import json
import logging

from rdflib import URIRef, Literal, BNode
import ckantoolkit as toolkit

from ckanext.dcat.utils import resource_uri, catalog_uri
from ckanext.dcat.profiles.base import URIRefOrLiteral, CleanedURIRef

from ckanext.schemingdcat.profiles.base import (
    # Codelists
    MD_ES_FORMATS,
    # Namespaces
    namespaces,
)
from ckanext.schemingdcat.config import (
    FREQUENCY_MAPPING
)
from ckanext.schemingdcat.helpers import schemingdcat_get_catalog_publisher_info, schemingdcat_get_ckan_site_url
from ckanext.schemingdcat.profiles.dcat_ap.eu_dcat_ap import EuDCATAPProfile
from ckanext.schemingdcat.profiles.dcat_config import (
    # Vocabs
    RDF,
    DCAT,
    DCATAP,
    DC,
    DCT,
    XSD,
    SCHEMA,
    RDFS,
    ADMS,
    CNT,
    FOAF,
    TIME,
    # Default values
    default_translated_fields,
    es_dcat_default_values, 
    default_translated_fields_es_dcat,
    )

config = toolkit.config

DISTRIBUTION_LICENSE_FALLBACK_CONFIG = "ckanext.dcat.resource.inherit.license"
catalog_base_ref =  config.get('ckan.site_url', None).rstrip('/')

log = logging.getLogger(__name__)


#TODO: Implement Spanish DCAT (NTI-RISP) profile
class EsNTIRISPProfile(EuDCATAPProfile):
    """
    A custom RDF profile based on the NTI-RISP for data portals in Spain

    Default values for some fields:
    
    ckanext-dcat/ckanext/dcat/.profiles.default_config.py

    More information and specification:

    https://datos.gob.es/es/documentacion/normativa-de-ambito-nacional
    https://datos.gob.es/es/documentacion/guia-de-aplicacion-de-la-norma-tecnica-de-interoperabilidad-de-reutilizacion-de

    """

    def parse_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        dataset_dict = self._parse_dataset_base(dataset_dict, dataset_ref)

        # NTI-RISP properties also applied to higher versions
        dataset_dict = self._parse_dataset_nti_risp(dataset_dict, dataset_ref)

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        self._graph_from_dataset_base(dataset_dict, dataset_ref)

        # NTI-RISP properties also applied to higher versions
        self._graph_from_dataset_nti_risp(dataset_dict, dataset_ref)

        # NTI-RISP specific properties
        self._graph_from_dataset_nti_risp_only(dataset_dict, dataset_ref)

    def graph_from_catalog(self, catalog_dict, catalog_ref):

        self._graph_from_catalog_base(catalog_dict, catalog_ref)
        
        # NTI-RISP catalog properties
        self._graph_from_catalog_nti_risp(catalog_dict, catalog_ref)

    def _parse_dataset_nti_risp(self, dataset_dict, dataset_ref):
        """
        Parses a CKAN dataset dictionary and generates an RDF graph.

        Args:
            dataset_dict (dict): The dictionary containing the dataset metadata.
            dataset_ref (URIRef): The URI of the dataset in the RDF graph.

        Returns:
            dict: The updated dataset dictionary with the RDF metadata.
        """
        # Call base super method for common properties
        super().parse_dataset(dataset_dict, dataset_ref)

        # Lists
        for key, predicate in (
            ('theme_es', DCAT.theme),
            ('temporal_resolution', DCAT.temporalResolution),
            ('is_referenced_by', DCT.isReferencedBy),
        ):
            values = self._object_value_list(dataset_ref, predicate)
            if values:
                dataset_dict['extras'].append({'key': key,
                                               'value': json.dumps(values)})
        # Temporal
        start, end = self._time_interval(dataset_ref, DCT.temporal, dcat_ap_version=2)
        if start:
            self._insert_or_update_temporal(dataset_dict, 'temporal_start', start)
        if end:
            self._insert_or_update_temporal(dataset_dict, 'temporal_end', end)

        # Spatial
        spatial = self._spatial(dataset_ref, DCT.spatial)
        for key in ('bbox', 'centroid'):
            self._add_spatial_to_dict(dataset_dict, key, spatial)

        # Resources
        for distribution in self._distributions(dataset_ref):
            distribution_ref = str(distribution)
            for resource_dict in dataset_dict.get('resources', []):
                # Match distribution in graph and distribution in resource dict
                if resource_dict and distribution_ref == resource_dict.get('distribution_ref'):
                    #  Simple values
                    for key, predicate in (
                            ('availability', DCATAP.availability),
                            ('compress_format', DCAT.compressFormat),
                            ('package_format', DCAT.packageFormat),
                            ):
                        value = self._object_value(distribution, predicate)
                        if value:
                            resource_dict[key] = value

                    # Access services
                        access_service_list = []

                        for access_service in self.g.objects(distribution, DCAT.accessService):
                            access_service_dict = {}

                            #  Simple values
                            for key, predicate in (
                                    ('availability', DCATAP.availability),
                                    ('title', DCT.title),
                                    ('endpoint_description', DCAT.endpointDescription),
                                    ('access_rights', DCT.accessRights),
                                    ('description', DCT.description),
                                    ):
                                value = self._object_value(access_service, predicate)
                                if value:
                                    access_service_dict[key] = value
                            #  List
                            for key, predicate in (
                                    ('endpoint_url', DCAT.endpointURL),
                                    ('serves_dataset', DCAT.servesDataset),
                                    ('resource_relation', DCT.relation),
                                    ):
                                values = self._object_value_list(access_service, predicate)
                                if values:
                                    access_service_dict[key] = values

                            # Access service URI (explicitly show the missing ones)
                            access_service_dict['uri'] = (str(access_service)
                                    if isinstance(access_service, URIRef)
                                    else '')

                            # Remember the (internal) access service reference for referencing in
                            # further profiles, e.g. for adding more properties
                            access_service_dict['access_service_ref'] = str(access_service)

                            access_service_list.append(access_service_dict)

                        if access_service_list:
                            resource_dict['access_services'] = json.dumps(access_service_list)

        return dataset_dict

    def _graph_from_dataset_nti_risp(self, dataset_dict, dataset_ref):
        """
        CKAN -> DCAT properties carried forward to higher NTI-RISP versions
        """
        
        # Namespaces
        self._bind_namespaces()

        for prefix, namespace in namespaces.items():
            self.g.bind(prefix, namespace)

        self.g.add((dataset_ref, RDF.type, DCAT.Dataset))

        # Translated fields
        items = [(
            default_translated_fields[key]['field_name'],
            default_translated_fields[key]['rdf_predicate'],
            default_translated_fields[key]['fallbacks'],
            default_translated_fields[key]['_type'],
            default_translated_fields[key]['required_lang']
            )
            for key in default_translated_fields_es_dcat
        ]
        self._add_triples_from_dict(dataset_dict, dataset_ref, items)


        # Basic elements (Title, description, Dates)
        basic_elements = [
            ('url', DCAT.landingPage, None, URIRef),
        ]
        
        dates = [
            ('created', DCT.created, ['metadata_created'], Literal),
            ('valid', DCT.valid, None, Literal),
        ]
        
        self._add_date_triples_from_dict(dataset_dict, dataset_ref, dates)
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, basic_elements)

        # Remove identifier without URI if exists
        for dataset_identifier in self.g.objects(dataset_ref, DCT.identifier):
            if not isinstance(dataset_identifier, URIRef):
                self.g.remove((dataset_ref, DCT.identifier, dataset_identifier))
        
        # Remove language with URI if exists
        for language_uri in self.g.objects(dataset_ref, DCT.language):
            self.g.remove((dataset_ref, DCT.language, language_uri))
            
        # Remove other themes (DCAT-AP/NTI-RISP)
        for non_theme_es in self.g.objects(dataset_ref, DCAT.theme):
            self.g.remove((dataset_ref, DCAT.theme, non_theme_es))

        # NTI-RISP Mandatory. The publisher is a DIR3 identifier: https://datos.gob.es/es/recurso/sector-publico/org/Organismo
        catalog_publisher_info = schemingdcat_get_catalog_publisher_info()
        
        publisher_ref = CleanedURIRef(catalog_publisher_info.get("identifier"))

        # remove publisher to avoid duplication
        self._clean_publisher(dataset_ref)

        # Add Catalog publisher to Dataset
        if publisher_ref:
            self.g.add((publisher_ref, RDF.type, FOAF.Agent))
            self.g.add((dataset_ref, DCT.publisher, publisher_ref))
            
        # Add dataset URI as identifier
        if dataset_ref:
            self.g.add((dataset_ref, DCT.identifier, Literal(dataset_ref)))

        # NTI-RISP Core elements
        items = {
            'notes': (DCT.description, es_dcat_default_values['notes']),
            'conforms_to_es': (DCT.conformsTo, es_dcat_default_values['conformance_es']),
            'license_url': (DCT.license, es_dcat_default_values['license_url']),
            'language_code': (DC.language, es_dcat_default_values['language_code'] or config.get('ckan.locale_default')),
            'spatial_uri': (DCT.spatial, es_dcat_default_values['spatial_uri']),
            'publisher_identifier_es': (DCT.publisher,  publisher_ref or es_dcat_default_values['publisher_identifier']),
        }

        self._add_dataset_triples_from_dict(dataset_dict, dataset_ref, items)      

        # Lists
        dataset_dict['tags'] = [tag['name'].replace(" ", "").lower() for tag in dataset_dict.get('tags', [])]

        # Lists NTI-RISP Core
        items_list = [
            ('reference', DCT.references, None, URIRefOrLiteral),
            ('tags', DCAT.keyword, None, Literal),
            ('theme_es', DCAT.theme, es_dcat_default_values['theme_es'], URIRefOrLiteral),
        ]

        #Lists DCAT-AP Extension
        items_dcatap_list = [
            ('conforms_to', DCT.conformsTo, None, URIRef),
            ('metadata_profile', DCT.conformsTo, None, URIRef),
        ]

        items_list.extend(items_dcatap_list)
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items_list)
         
        #FIXME Frequency - Frecuencia ('frequency', DCT.accrualPeriodicity, None, URIRefOrLiteral): https://github.com/ctt-gob-es/datos.gob.es/blob/30c4a0d97356e0caf948aff2bb74790f4885c67f/ckan/ckanext-dge-harvest/ckanext/dge_harvest/profiles.py#L2508
        # Remove dct:accrualPeriodicity if exists
        for old_freq in self.g.objects(dataset_ref, DCT.accrualPeriodicity):
            self.g.remove((dataset_ref, DCT.accrualPeriodicity, old_freq))
        freq_uri = dataset_dict.get('frequency')
        if freq_uri:
            self._add_frequency_value(dataset_ref, freq_uri)

        # Temporal - Cobertura temporal
        for temporal_obj in self.g.objects(dataset_ref, DCT["temporal"]):
            # Remove temporal with URI if exists
            self.g.remove((dataset_ref, DCT["temporal"], temporal_obj))
            
            # If it is a blank node, delete all of its properties
            if isinstance(temporal_obj, BNode):
                for p, o in self.g.predicate_objects(temporal_obj):
                    self.g.remove((temporal_obj, p, o))
        self._temporal_graph(dataset_dict, dataset_ref)
    
        # Use fallback license if set in config
        resource_license_fallback = None
        if toolkit.asbool(config.get(DISTRIBUTION_LICENSE_FALLBACK_CONFIG, False)):
            if "license_id" in dataset_dict and isinstance(
                URIRefOrLiteral(dataset_dict["license_id"]), URIRef
            ):
                resource_license_fallback = dataset_dict["license_id"]
            elif "license_url" in dataset_dict and isinstance(
                URIRefOrLiteral(dataset_dict["license_url"]), URIRef
            ):
                resource_license_fallback = dataset_dict["license_url"]
        
        # Resources
        for resource_dict in dataset_dict.get('resources', []):

            distribution_ref = CleanedURIRef(resource_uri(resource_dict))

            self.g.add((dataset_ref, DCAT.distribution, distribution_ref))

            self.g.add((distribution_ref, RDF.type, DCAT.Distribution))

            # Remove any accessURL if exists
            for access_url in self.g.objects(distribution_ref, DCAT["accessURL"]):
                self.g.remove((distribution_ref, DCAT["accessURL"], access_url))

            # Add distribution URI as identifier
            if distribution_ref:
                self.g.add((distribution_ref, DCT.identifier, Literal(distribution_ref)))

            # NTI-RISP Core elements
            items = {
                'url': (DCAT.accessURL, None),
                'name': (DCT.title, None),
                'description': (DCT.description, es_dcat_default_values['description']),
                'language_code': (DC.language, es_dcat_default_values['language_code'] or config.get('ckan.locale_default')),
                'license': (DCT.license, es_dcat_default_values['license']),
                'size': (DCT.byteSize, None),
            }

            if resource_license_fallback and not (distribution_ref, DCT.license, None) in self.g:
                self.g.add(
                    (
                        distribution_ref,
                        DCT.license,
                        URIRefOrLiteral(resource_license_fallback),
                    )
                )

            self._add_dataset_triples_from_dict(resource_dict, distribution_ref, items)   

            # Lists
            items_lists = [
                ('resource_relation', DCT.relation, None, URIRef),
            ]

            self._add_list_triples_from_dict(resource_dict, distribution_ref, items_lists)

            # Format/Mimetype - Formato de la distribución
            for format_obj in self.g.objects(distribution_ref, DCT["format"]):
                # Remove format with URI if exists
                self.g.remove((distribution_ref, DCT["format"], format_obj))
                
                # If it is a blank node, delete all of its properties
                if isinstance(format_obj, BNode):
                    for p, o in self.g.predicate_objects(format_obj):
                        self.g.remove((format_obj, p, o))
            # Add correct format
            self._distribution_format(resource_dict, distribution_ref)

            # Remove language with URI if exists
            for language_uri in self.g.objects(distribution_ref, DCT.language):
                self.g.remove((distribution_ref, DCT.language, language_uri))

            # Remove dcat:mediaType if exists
            for media_type in self.g.objects(distribution_ref, DCAT.mediaType):
                self.g.remove((distribution_ref, DCAT.mediaType, media_type))

    def _graph_from_dataset_nti_risp_only(self, dataset_dict, dataset_ref):
        """
        CKAN -> DCAT v2 specific properties (not applied to higher versions)
        """
        pass

    def _graph_from_catalog_nti_risp(self, catalog_dict, catalog_ref):
        """
        NTI-RISP Catalog properties
        """
        for prefix, namespace in namespaces.items():
            self.g.bind(prefix, namespace)

        self.g.add((catalog_ref, RDF.type, DCAT.Catalog))
        
        # Basic fields
        license, access_rights, spatial_uri, language_code = [
            self._get_catalog_field(field_name='license_url', fallback='license_id', default_values_dict=es_dcat_default_values),
            self._get_catalog_field(field_name='access_rights', default_values_dict=es_dcat_default_values),
            self._get_catalog_field(field_name='spatial_uri', default_values_dict=es_dcat_default_values),
            es_dcat_default_values['language_code'] or config.get('ckan.locale_default')
            ]

        # Remove homepage without root_path
        for homepage in self.g.objects(catalog_ref, FOAF.homepage):
            self.g.remove((catalog_ref, FOAF.homepage, homepage))

        # Remove language with URI if exists
        for language_uri in self.g.objects(catalog_ref, DCT.language):
            self.g.remove((catalog_ref, DCT.language, language_uri))

        # Remove other themes (DCAT-AP/INSPIRE)
        for non_theme_es in self.g.objects(catalog_ref, DCAT.themeTaxonomy):
            self.g.remove((catalog_ref, DCAT.themeTaxonomy, non_theme_es))

        # Mandatory elements by NTI-RISP (datos.gob.es)
        items_core = [
            ("identifier", DCT.identifier, catalog_uri(), URIRef),
            ('encoding', CNT.characterEncoding, 'UTF-8', Literal),
            ('language_code', DC.language, language_code, Literal),
            ('spatial_uri', DCT.spatial, spatial_uri, URIRefOrLiteral),
            ('theme_taxonomy', DCAT.themeTaxonomy, es_dcat_default_values['theme_taxonomy'], URIRef),
            ('homepage', FOAF.homepage, schemingdcat_get_ckan_site_url(), URIRef),
        ]
        
        # DCAT-AP extension
        items_dcatap = [
            ('license', DCT.license, license, URIRef),
            ('conforms_to', DCT.conformsTo, es_dcat_default_values['conformance_es'], URIRef),
            ('access_rights', DCT.accessRights, access_rights, URIRefOrLiteral),
        ]
         
        items_core.extend(items_dcatap)
         
        for item in items_core:
            key, predicate, fallback, _type = item
            value = catalog_dict.get(key, fallback) if catalog_dict else fallback
            if value:
                self.g.add((catalog_ref, predicate, _type(value)))

        # Title & Description multilang
        catalog_fields = {
            'title': (config.get("ckan.site_title"), DCT.title),
            'description': (config.get("ckan.site_description"), DCT.description)
        }
        
        try:
            for field, (value, predicate) in catalog_fields.items():
                self._add_multilingual_literal(self.g, catalog_ref, predicate, value, es_dcat_default_values['language_code'])
        except Exception as e:
            log.error(f'Error adding catalog {field}: {str(e)}')

        #TODO: Tamaño del catálogo - dct:extent
        # <dct:extent> 
        #     <dct:SizeOrDuration> 
        #         <rdf:value rdf:datatype="http://www.w3.org/2001/XMLSchema#nonNegativeInteger">850</rdf:value> 
        #         <rdfs:label xml:lang="es">850 documentos o recursos de información</rdfs:label> 
        #     </dct:SizeOrDuration> 
        # </dct:extent> 

        # Dates
        modified = self._get_catalog_field(field_name='metadata_modified', default_values_dict=es_dcat_default_values)
        issued = self._get_catalog_field(field_name='metadata_created', default_values_dict=es_dcat_default_values, order='asc')
        if modified or issued or license:
            if modified:
                self._add_date_triple(catalog_ref, DCT.modified, self._ensure_datetime(modified))
            if issued:
                self._add_date_triple(catalog_ref, DCT.issued, self._ensure_datetime(issued))

        #TODO: Catalog languages, only when NTI-RISP accepted not include all fields in all of catalog languages.
        catalog_language_codes = self._get_catalog_languages_paginated(default_values_property='catalog_language_codes', default_values=es_dcat_default_values, output_format='iso2')
        consistent_catalog_language_codes = self._get_graph_required_languages(
            self.g, 
            [DCT.title, DCT.description],
            catalog_language_codes
        )
        
        # Make sure Spanish language is included (without duplicating)
        default_lang = es_dcat_default_values['language_code']
        if default_lang not in consistent_catalog_language_codes:
            consistent_catalog_language_codes.append(default_lang)
        
        #log.debug('consistent_catalog_language_codes: %s', consistent_catalog_language_codes)
        for catalog_lang in consistent_catalog_language_codes:
            self.g.add((catalog_ref, DC.language, Literal(catalog_lang)))

    def _add_dataset_triples_from_dict(self, dataset_dict, dataset_ref, items):
        """Adds triples to the RDF graph for the given dataset.

        Args:
            dataset_dict (dict): A dictionary containing the dataset metadata.
            dataset_ref (rdflib.URIRef): The URI reference for the dataset.
            items (dict): A dictionary containing the keys and values for the metadata items.

        Returns:
            None

        """
        
        for key, (predicate, default_value) in items.items():
            value = dataset_dict.get(key, default_value)
            if value is not None:
                self.g.add((dataset_ref, predicate, URIRefOrLiteral(value)))

    def _bind_namespaces(self):
        self.g.namespace_manager.bind('schema', namespaces['schema'], replace=True)
        self.g.namespace_manager.bind('time', namespaces['time'], replace=True)

    def _temporal_graph(self, dataset_dict, dataset_ref):
        """Adds the dct:temporal triple to the RDF graph for the given dataset.

        Args:
            dataset_dict (dict): A dictionary containing the dataset metadata.
            dataset_ref (rdflib.URIRef): The URI reference for the dataset.

        Returns:
            None

        """
        # Temporal
        start = self._get_dataset_value(dataset_dict, 'temporal_start')
        end = self._get_dataset_value(dataset_dict, 'temporal_end')
    
        if start or end:
            # Remove language with URI if exists
            for old_temporal in self.g.objects(dataset_ref, DCT.temporal):
                self.g.remove((dataset_ref, DCT.temporal, old_temporal))
            
            uid = 1
            temporal_extent = URIRef(
                "%s/%s-%s" % (dataset_ref, 'PeriodOfTime', uid))
            self.g.add((temporal_extent, RDF.type, DCT.PeriodOfTime))
            if start:
                self._add_date_triple(
                    temporal_extent, SCHEMA.startDate, self._ensure_datetime(start))
            if end:
                self._add_date_triple(
                    temporal_extent, SCHEMA.endDate, self._ensure_datetime(end))
            self.g.add((dataset_ref, DCT.temporal, temporal_extent))

    def _distribution_format(self, resource_dict, distribution_ref):
        """
        Generates an RDF triple for the format of a resource.

        Args:
            mime_type (str): The MIME type of the format.
            label (str): The label of the format.

        Returns:
            str: The RDF triple for the format.
        """        
        resource_format = resource_dict.get('format', es_dcat_default_values['format_es'])

        format_es = self._search_value_codelist(MD_ES_FORMATS, resource_format, 'label','label', False) or es_dcat_default_values['format_es']
        mime_type = self._search_value_codelist(MD_ES_FORMATS, format_es, 'label','id') or es_dcat_default_values['mimetype_es']

        if format_es:
            imt = BNode()
            self.g.add((imt, RDF.type, DCT.IMT))
            self.g.add((distribution_ref, DCT['format'], imt))
            self.g.add((imt, RDFS.label, Literal(format_es)))

        if mime_type:
            self.g.add((imt, RDF.value, Literal(mime_type)))
