import logging
import json
from decimal import Decimal, DecimalException

from rdflib import URIRef, BNode, Literal

from ckantoolkit import config

from ckanext.dcat.utils import resource_uri
from ckanext.dcat.profiles.base import URIRefOrLiteral, CleanedURIRef

from ckanext.schemingdcat.profiles.base import (
    # Codelists
    MD_INSPIRE_REGISTER,
    MD_FORMAT,
    MD_EU_LANGUAGES,
)
from ckanext.schemingdcat.profiles.dcat_ap.eu_dcat_ap_2 import EuDCATAP2Profile
from ckanext.schemingdcat.helpers import schemingdcat_get_catalog_publisher_info
from ckanext.schemingdcat.profiles.dcat_config import (
    # Vocabs
    RDF,
    DCAT,
    DCATAP,
    DCT,
    XSD,
    SCHEMA,
    RDFS,
    ADMS,
    CNT,
    ELI,
    EUROVOC,
    FOAF,
    VCARD,
    SKOS,
    # Default values
    eu_dcat_ap_default_values,
    es_dcat_ap_default_values,
    )

log = logging.getLogger(__name__)


#TODO: Implement Spanish DCAT-AP-ES (Based on DCAT-AP 2.1.1) profile
class EsDCATAP2Profile(EuDCATAP2Profile):
    """
    A custom RDF profile based on the DCAT-AP 2.1.1 for data portals in Spain

    Default values for some fields:
    
    ckanext-dcat/ckanext/dcat/.profiles.default_config.py

    More information and specification:

    https://datos.gob.es/es/doc-tags/dcat-ap

    """


    def parse_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        dataset_dict = self._parse_dataset_base(dataset_dict, dataset_ref)

        # DCAT AP v2 properties also applied to higher versions
        dataset_dict = self._parse_dataset_v2(dataset_dict, dataset_ref)

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):
        """
        Generates the RDF network for a dataset with optimized language handling (DCAT-AP-ES req).
        
        This optimized version only applies the default language tags to the literals associated with the current 
        to the literals associated with the current dataset_ref, avoiding processing the entire
        the entire network each time.
        """
        # Call base method for common properties
        self._graph_from_dataset_base(dataset_dict, dataset_ref)
    
        # DCAT AP v2 properties also applied to higher versions
        self._graph_from_dataset_v2(dataset_dict, dataset_ref)
    
        # DCAT AP v2 specific properties
        self._graph_from_dataset_v2_only(dataset_dict, dataset_ref)
    
        # DCAT AP-ES v2 properties also applied to higher versions
        self._graph_from_dataset_es_dcat_ap_v2(dataset_dict, dataset_ref)

    def graph_from_catalog(self, catalog_dict, catalog_ref):

        # Call catalog base method for common properties
        self._graph_from_catalog_base(catalog_dict, catalog_ref)

        # DCAT AP 2 catalog properties also applied to higher versions
        self._graph_from_catalog_v2(catalog_dict, catalog_ref)

        # DCAT AP ES v2 catalog properties also applied to higher versions
        self._graph_from_catalog_es_dcat_ap_v2(catalog_dict, catalog_ref)
        
    def _parse_dataset_v2(self, dataset_dict, dataset_ref):
        """
        DCAT -> CKAN properties carried forward to higher DCAT-AP versions
        """

        # Call base super method for common properties
        super().parse_dataset(dataset_dict, dataset_ref)

        # Basic fields
        for key, predicate in (
            ('encoding', CNT.characterEncoding),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = value

        # Standard values
        value = self._object_value(dataset_ref, DCAT.temporalResolution)
        if value:
            dataset_dict["extras"].append(
                {"key": "temporal_resolution", "value": value}
            )

        # Lists
        for key, predicate in (
            ("is_referenced_by", DCT.isReferencedBy),
            ("applicable_legislation", DCATAP.applicableLegislation),
            ("hvd_category", DCATAP.hvdCategory),
        ):
            values = self._object_value_list(dataset_ref, predicate)
            if values:
                dataset_dict["extras"].append({"key": key, "value": json.dumps(values)})

        # Spatial
        spatial = self._spatial(dataset_ref, DCT.spatial)
        for key in ("bbox", "centroid"):
            self._add_spatial_to_dict(dataset_dict, key, spatial)

        # Spatial resolution in meters
        spatial_resolution = self._object_value_float_list(
            dataset_ref, DCAT.spatialResolutionInMeters
        )
        if spatial_resolution:
            # For some reason we incorrectly allowed lists in this property at
            # some point, keep support for it but default to single value
            value = (
                spatial_resolution[0]
                if len(spatial_resolution) == 1
                else json.dumps(spatial_resolution)
            )
            dataset_dict["extras"].append(
                {
                    "key": "spatial_resolution_in_meters",
                    "value": value,
                }
            )

        # Resources
        for distribution in self._distributions(dataset_ref):
            distribution_ref = str(distribution)
            for resource_dict in dataset_dict.get("resources", []):
                # Match distribution in graph and distribution in resource dict
                if resource_dict and distribution_ref == resource_dict.get(
                    "distribution_ref"
                ):
                    #  Simple values
                    for key, predicate in (
                        ("availability", DCATAP.availability),
                        ("compress_format", DCAT.compressFormat),
                        ("package_format", DCAT.packageFormat),
                        ("temporal_resolution", DCAT.temporalResolution),
                    ):
                        value = self._object_value(distribution, predicate)
                        if value:
                            resource_dict[key] = value

                    # Spatial resolution in meters
                    spatial_resolution = self._object_value_float_list(
                        distribution, DCAT.spatialResolutionInMeters
                    )
                    if spatial_resolution:
                        value = (
                            spatial_resolution[0]
                            if len(spatial_resolution) == 1
                            else json.dumps(spatial_resolution)
                        )
                        resource_dict["spatial_resolution_in_meters"] = value

                    #  Lists
                    for key, predicate in (
                        ("applicable_legislation", DCATAP.applicableLegislation),
                    ):
                        values = self._object_value_list(distribution, predicate)
                        if values:
                            resource_dict[key] = json.dumps(values)

                    # Access services
                    access_service_list = []

                    for access_service in self.g.objects(
                        distribution, DCAT.accessService
                    ):
                        access_service_dict = {}

                        #  Simple values
                        for key, predicate in (
                            ("availability", DCATAP.availability),
                            ("title", DCT.title),
                            ("endpoint_description", DCAT.endpointDescription),
                            ("license", DCT.license),
                            ("access_rights", DCT.accessRights),
                            ("description", DCT.description),
                        ):
                            value = self._object_value(access_service, predicate)
                            if value:
                                access_service_dict[key] = value
                        #  List
                        for key, predicate in (
                            ("endpoint_url", DCAT.endpointURL),
                            ("serves_dataset", DCAT.servesDataset),
                        ):
                            values = self._object_value_list(access_service, predicate)
                            if values:
                                access_service_dict[key] = values

                        # Access service URI (explicitly show the missing ones)
                        access_service_dict["uri"] = (
                            str(access_service)
                            if isinstance(access_service, URIRef)
                            else ""
                        )

                        # Remember the (internal) access service reference for
                        # referencing in further profiles, e.g. for adding more
                        # properties
                        access_service_dict["access_service_ref"] = str(access_service)

                        access_service_list.append(access_service_dict)

                    if access_service_list:
                        resource_dict["access_services"] = json.dumps(
                            access_service_list
                        )

        return dataset_dict

    def _graph_from_dataset_es_dcat_ap_v2(self, dataset_dict, dataset_ref):
        """
        CKAN -> DCAT properties carried forward to higher DCAT-AP versions
        """

        # Dates to Datetime      
        self._add_triple_from_dict(
            dataset_dict,
            dataset_ref,
            DCT.issued,
            "issued",
            _datatype=XSD.date,
        )

        # Ensure ES language exists in dct:language props
        self._ensure_language_triple(dataset_ref, es_dcat_ap_default_values["language"])

        # Resources
        for resource_dict in dataset_dict.get("resources", []):
            distribution_ref = CleanedURIRef(resource_uri(resource_dict))

    def _graph_from_dataset_v2_only(self, dataset_dict, dataset_ref):
        """
        CKAN -> DCAT v2 specific properties (not applied to higher versions)
        """

        # Other identifiers (these are handled differently in the
        # DCAT-AP v3 profile)
        alternate_identifier = self._get_dict_value(dataset_dict, "alternate_identifier")
        if alternate_identifier:
            items = self._read_list_value(alternate_identifier)
            for item in items:
                identifier = BNode()
                self.g.add((dataset_ref, ADMS.identifier, identifier))
                self.g.add((identifier, RDF.type, ADMS.Identifier))
                self.g.add((identifier, SKOS.notation, Literal(item)))

        # DCAT-AP-ES Mandatory. The publisher is a DIR3 identifier: https://datos.gob.es/es/recurso/sector-publico/org/Organismo
        catalog_publisher_info = schemingdcat_get_catalog_publisher_info()
        
        publisher_details = {
            "name": catalog_publisher_info.get("name"),
            "email": catalog_publisher_info.get("email"),
            "url": catalog_publisher_info.get("url"),
            "type": catalog_publisher_info.get("type"),
            "identifier": catalog_publisher_info.get("identifier"),
        }

        publisher_ref = CleanedURIRef(publisher_details["identifier"]
        )

        # remove publisher to avoid duplication
        self._clean_publisher(dataset_ref)

        # Add Catalog publisher to Dataset
        if publisher_ref:
            self.g.add((publisher_ref, RDF.type, FOAF.Agent))
            self.g.add((dataset_ref, DCT.publisher, publisher_ref))
            
            # Process identifier
            if "identifier" in publisher_details and publisher_details["identifier"]:
                publisher_details["identifier"] = self._process_dct_identifier(publisher_details["identifier"], mandatory=True)
            
            items = [
                ("name", FOAF.name, None, Literal),
                ("email", FOAF.mbox, None, Literal),
                ("url", FOAF.homepage, None, URIRef),
                ("type", DCT.type, None, URIRefOrLiteral),
                ("identifier", DCT.identifier, None, Literal),
            ]

            self._add_triples_from_dict(publisher_details, publisher_ref, items)

        # Clean up applicable_legislation that are not URIs
        for legislation in self.g.objects(dataset_ref, DCATAP.applicableLegislation):
            if not isinstance(legislation, URIRef):
                self.g.remove((dataset_ref, DCATAP.applicableLegislation, legislation))

        # Resources
        for resource_dict in dataset_dict.get("resources", []):

            distribution_ref = CleanedURIRef(resource_uri(resource_dict))

            # Clean up applicable_legislation that are not URIs
            for legislation in self.g.objects(distribution_ref, DCATAP.applicableLegislation):
                if not isinstance(legislation, URIRef):
                    self.g.remove((distribution_ref, DCATAP.applicableLegislation, legislation))

    def _graph_from_catalog_es_dcat_ap_v2(self, catalog_dict, catalog_ref):
        # Catalog languages
        catalog_language_codes = self._get_catalog_languages_paginated(default_values_property='catalog_languages', default_values=es_dcat_ap_default_values, output_format='uri')
        for catalog_lang in catalog_language_codes:
            self.g.add((catalog_ref, DCT.language, URIRef(catalog_lang)))
        
        # Title & Description multilang
        catalog_fields = {
            'title': (config.get("ckan.site_title"), DCT.title),
            'description': (config.get("ckan.site_description"), DCT.description)
        }
        
        try:
            for field, (value, predicate) in catalog_fields.items():
                self._add_multilingual_literal(self.g, catalog_ref, predicate, value, es_dcat_ap_default_values['language_code'])
        except Exception as e:
            log.error(f'Error adding catalog {field}: {str(e)}')