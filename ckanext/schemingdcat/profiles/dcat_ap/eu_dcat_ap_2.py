import json
from decimal import Decimal, DecimalException
import logging

from rdflib import URIRef, BNode, Literal

from ckanext.dcat.utils import resource_uri, catalog_uri
from ckanext.dcat.profiles.base import URIRefOrLiteral, CleanedURIRef

from ckanext.schemingdcat.config import (
    DCAT_SERVICE_TYPES
)
from ckanext.schemingdcat.profiles.base import (
    # Codelists
    MD_INSPIRE_REGISTER,
    MD_FORMAT,
    MD_EU_LANGUAGES,
)
from ckanext.schemingdcat.profiles.eu_dcat_ap_base import BaseEuDCATAPProfile
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
    FOAF,
    # Default values
    metadata_field_names,
    eu_dcat_ap_default_values,
    )

log = logging.getLogger(__name__)

class EuDCATAP2Profile(BaseEuDCATAPProfile):
    """
    A custom RDF profile based on the DCAT-AP 2 for data portals in Europe

    Default values for some fields:
    
    ckanext-dcat/ckanext/dcat/.profiles.default_config.py

    More information and specification:

    https://joinup.ec.europa.eu/asset/dcat_application_profile

    """


    def parse_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        dataset_dict = self._parse_dataset_base(dataset_dict, dataset_ref)

        # DCAT AP v2 properties also applied to higher versions
        dataset_dict = self._parse_dataset_v2(dataset_dict, dataset_ref)

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        self._graph_from_dataset_base(dataset_dict, dataset_ref)

        # DCAT AP v2 properties also applied to higher versions
        self._graph_from_dataset_v2(dataset_dict, dataset_ref)

        # DCAT AP v2 specific properties
        self._graph_from_dataset_v2_only(dataset_dict, dataset_ref)

    def graph_from_catalog(self, catalog_dict, catalog_ref):

        self._graph_from_catalog_base(catalog_dict, catalog_ref)

        # DCAT AP 2 catalog properties also applied to higher versions
        self._graph_from_catalog_v2(catalog_dict, catalog_ref)

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
        # Temporal
        start, end = self._time_interval(dataset_ref, DCT.temporal, dcat_ap_version=2)
        if start:
            self._insert_or_update_temporal(dataset_dict, "temporal_start", start)
        if end:
            self._insert_or_update_temporal(dataset_dict, "temporal_end", end)

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

    def _graph_from_dataset_v2(self, dataset_dict, dataset_ref):
        """
        CKAN -> DCAT properties carried forward to higher DCAT-AP versions
        """

        # Catalog URI
        catalog_ref = catalog_uri()

        # Lists
        for key, predicate, fallbacks, type, datatype, _class in (
            (
                "is_referenced_by",
                DCT.isReferencedBy,
                None,
                URIRefOrLiteral,
                None,
                RDFS.Resource,
            ),
            (
                "applicable_legislation",
                DCATAP.applicableLegislation,
                None,
                URIRefOrLiteral,
                None,
                ELI.LegalResource,
            ),
            ("hvd_category", DCATAP.hvdCategory, None, URIRefOrLiteral, None, None),
        ):
            self._add_triple_from_dict(
                dataset_dict,
                dataset_ref,
                predicate,
                key,
                list_value=True,
                fallbacks=fallbacks,
                _type=type,
                _datatype=datatype,
                _class=_class,
            )

        # Temporal
        # The profile for DCAT-AP 1 stored triples using schema:startDate,
        # remove them to avoid duplication
        for temporal in self.g.objects(dataset_ref, DCT.temporal):
            if SCHEMA.startDate in [t for t in self.g.predicates(temporal, None)]:
                self.g.remove((temporal, None, None))
                self.g.remove((dataset_ref, DCT.temporal, temporal))

        start = self._get_dataset_value(dataset_dict, "temporal_start")
        end = self._get_dataset_value(dataset_dict, "temporal_end")
        if start or end:
            temporal_extent = BNode()

            self.g.add((temporal_extent, RDF.type, DCT.PeriodOfTime))
            if start:
                self._add_date_triple(temporal_extent, DCAT.startDate, self._ensure_datetime(start))
            if end:
                self._add_date_triple(temporal_extent, DCAT.endDate, self._ensure_datetime(end))
            self.g.add((dataset_ref, DCT.temporal, temporal_extent))

        # spatial
        spatial_bbox = self._get_dataset_value(dataset_dict, "spatial_bbox")
        spatial_cent = self._get_dataset_value(dataset_dict, "spatial_centroid")

        if spatial_bbox or spatial_cent:
            spatial_ref = self._get_or_create_spatial_ref(dataset_dict, dataset_ref)

            if spatial_bbox:
                self._add_spatial_value_to_graph(spatial_ref, DCAT.bbox, spatial_bbox)

            if spatial_cent:
                self._add_spatial_value_to_graph(
                    spatial_ref, DCAT.centroid, spatial_cent
                )

        # Spatial resolution in meters (0..1)
        spatial_resolution_in_meters = self._read_list_value(
            self._get_dataset_value(dataset_dict, "spatial_resolution_in_meters")
        )
        if spatial_resolution_in_meters:
            for value in spatial_resolution_in_meters:
                spatial_resolution = self._clean_spatial_resolution(value, 'decimal')
                try:
                    self.g.add(
                        (
                            dataset_ref,
                            DCAT.spatialResolutionInMeters,
                            Literal(Decimal(spatial_resolution), datatype=XSD.decimal),
                        )
                    )
                except (ValueError, TypeError, DecimalException):
                    self.g.add(
                        (dataset_ref, DCAT.spatialResolutionInMeters, Literal(spatial_resolution))
                    )

        # Clean up applicable_legislation that are not URIs
        for legislation in self.g.objects(dataset_ref, DCATAP.applicableLegislation):
            if not isinstance(legislation, URIRef):
                self.g.remove((dataset_ref, DCATAP.applicableLegislation, legislation))

        # DCAT 2: byteSize decimal
        for subject, predicate, object in self.g.triples((None, DCAT.byteSize, None)):
            if object and object.datatype != XSD.decimal or not object.datatype:
                self.g.remove((subject, predicate, object))

                self.g.add(
                    (
                        subject,
                        predicate,
                        Literal(int(object), datatype=XSD.decimal),
                    )
                )

        # Resources
        for resource_dict in dataset_dict.get("resources", []):

            distribution_ref = CleanedURIRef(resource_uri(resource_dict))

            #  Simple values
            items = [
                (
                    "compress_format",
                    DCAT.compressFormat,
                    None,
                    URIRefOrLiteral,
                    DCT.MediaType,
                ),
                (
                    "package_format",
                    DCAT.packageFormat,
                    None,
                    URIRefOrLiteral,
                    DCT.MediaType,
                ),
            ]

            self._add_triples_from_dict(resource_dict, distribution_ref, items)

            # Add availability from distribution
            distribution_availability = self._get_dataset_value(resource_dict, "availability") or eu_dcat_ap_default_values["availability"]
            if distribution_availability:
                self.g.add((distribution_ref, DCATAP.availability, URIRef(distribution_availability)))

            # Temporal resolution
            temporal_resolution = resource_dict.get("temporal_resolution")
            if temporal_resolution and self._is_valid_temporal_resolution(temporal_resolution):
                self.g.add((
                    distribution_ref, 
                    DCAT.temporalResolution, 
                    Literal(temporal_resolution, datatype=XSD.duration)
                ))

            # Spatial resolution in meters (0..1)
            spatial_resolution_in_meters = resource_dict.get("spatial_resolution_in_meters")
            if spatial_resolution_in_meters:
                spatial_resolution = self._clean_spatial_resolution(spatial_resolution_in_meters, 'decimal')
                try:
                    self.g.add(
                        (
                            distribution_ref,
                            DCAT.spatialResolutionInMeters,
                            Literal(Decimal(spatial_resolution), datatype=XSD.decimal),
                        )
                    )
                except (ValueError, TypeError, DecimalException):
                    self.g.add(
                        (distribution_ref, DCAT.spatialResolutionInMeters, Literal(spatial_resolution))
                    )

            #  Lists
            items = [
                (
                    "applicable_legislation",
                    DCATAP.applicableLegislation,
                    None,
                    URIRefOrLiteral,
                    ELI.LegalResource,
                ),
            ]
            self._add_list_triples_from_dict(resource_dict, distribution_ref, items)
            
            # Clean up applicable_legislation that are not URIs
            for legislation in self.g.objects(distribution_ref, DCATAP.applicableLegislation):
                if not isinstance(legislation, URIRef):
                    self.g.remove((distribution_ref, DCATAP.applicableLegislation, legislation))
            
            # DCAT Data Service. ckanext-schemingdcat: DCAT-AP Enhancements
            access_service_list = resource_dict.get("access_services", [])
            if isinstance(access_service_list, str):
                try:
                    access_service_list = json.loads(access_service_list)
                except ValueError:
                    access_service_list = []

            for access_service_dict in access_service_list:
                if not self._is_valid_access_service(access_service_dict):
                    continue
            
                # Get appropriate access service URI
                access_service_node = self._get_access_service_uri(access_service_dict, distribution_ref)
            
                self.g.add((distribution_ref, DCAT.accessService, access_service_node))
                self.g.add((access_service_node, RDF.type, DCAT.DataService))

                # Verificar si el nodo de servicio está basado en la URI del catálogo
                catalog_base_uri = str(catalog_uri())
                
                # Add title and description for dcat:DataServices
                self._add_service_multilingual_properties(access_service_node, access_service_dict, catalog_base_uri)

                #  Simple values
                items = [
                    ("license", DCT.license, None, URIRefOrLiteral),
                    ("access_rights", DCT.accessRights, None, URIRefOrLiteral),
                    (
                        "endpoint_description",
                        DCAT.endpointDescription,
                        None,
                        URIRefOrLiteral,
                        RDFS.Resource,
                    ),
                    ("description", DCT.description, None, Literal),
                ]

                self._add_triples_from_dict(
                    access_service_dict, access_service_node, items
                )

                #  Lists
                items = [
                    (
                        "endpoint_url",
                        DCAT.endpointURL,
                        None,
                        URIRefOrLiteral,
                        RDFS.Resource,
                    ),
                    ("serves_dataset", DCAT.servesDataset, None, URIRefOrLiteral),
                ]
                self._add_list_triples_from_dict(
                    access_service_dict, access_service_node, items
                )

                # Lists from resource
                items = [
                    (
                        "applicable_legislation",
                        DCATAP.applicableLegislation,
                        None,
                        URIRefOrLiteral,
                        ELI.LegalResource,
                    ),
                ]
                self._add_list_triples_from_dict(
                    resource_dict, access_service_node, items
                )

                # FOAF Page
                self.g.add((access_service_node, FOAF.page, distribution_ref))
                
                # HVD DataService Mandatory properties
                data_service_hvd_properties = [
                    ('hvd_category', DCATAP.hvdCategory, lambda x: x),
                    (None, DCT.license, self.g.value, dataset_ref),
                    (None, DCT.accessRights, self.g.value, dataset_ref),
                ]
                
                # Process mappings
                for src_field, predicate, getter, *args in data_service_hvd_properties:
                    value = (
                        self._get_dataset_value(dataset_dict, src_field) 
                        if src_field 
                        else getter(*args, predicate)
                    )
                    if value:
                        self._add_uri_from_value(access_service_node, predicate, value)
                
                # Add all DCAT.theme from dataset_ref to access_service_node
                for theme in self.g.objects(dataset_ref, DCAT.theme):
                    self.g.add((access_service_node, DCAT.theme, theme))
                    
                # Add DCAT.contactPoint from dataset_ref to access_service_node
                contact_point = self.g.value(dataset_ref, DCAT.contactPoint)
                if contact_point:
                    self.g.add((access_service_node, DCAT.contactPoint, contact_point))

                # Add DCAT.publisher from dataset_ref to access_service_node   
                self._add_catalog_publisher_to_service(access_service_node)

                # Append dcat:DataService to dcat:Catalog
                self.g.add((URIRef(catalog_ref), DCAT.service, access_service_node))   

                # Clean up applicable_legislation that are not URIs
                for legislation in self.g.objects(access_service_node, DCATAP.applicableLegislation):
                    if not isinstance(legislation, URIRef):
                        self.g.remove((access_service_node, DCATAP.applicableLegislation, legislation))

            if access_service_list:
                resource_dict["access_services"] = json.dumps(access_service_list)

    def _graph_from_dataset_v2_only(self, dataset_dict, dataset_ref):
        """
        CKAN -> DCAT v2 specific properties (not applied to higher versions)
        """

        # Other identifiers (these are handled differently in the
        # DCAT-AP v3 profile)
        self._add_triple_from_dict(
            dataset_dict,
            dataset_ref,
            ADMS.identifier,
            "alternate_identifier",
            list_value=True,
            _type=URIRefOrLiteral,
            _class=ADMS.Identifier,
        )

    def _graph_from_catalog_v2(self, catalog_dict, catalog_ref):
        # Add DataServices to catalog
        for access_service in self.g.objects(catalog_ref, DCAT.DataService):
            self.g.add((catalog_ref, DCAT.service, access_service))
    