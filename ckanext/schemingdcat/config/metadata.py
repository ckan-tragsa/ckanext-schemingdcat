import typing

# Default DCAT metadata configuration
OGC2CKAN_HARVESTER_MD_CONFIG = {
    'access_rights': 'http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/noLimitations',
    'conformance': [
        'http://inspire.ec.europa.eu/documents/inspire-metadata-regulation','http://inspire.ec.europa.eu/documents/commission-regulation-eu-no-13122014-10-december-2014-amending-regulation-eu-no-10892010-0'
    ],
    'author_name': 'ckanext-schemingdcat',
    'author_email': 'admin@{ckan_site_url}',
    'author_url': '{ckan_site_url}/organization/test',
    'author_uri': '{ckan_site_url}/organization/test',
    'contact_name': 'ckanext-schemingdcat',
    'contact_email': 'admin@{ckan_site_url}',
    'contact_url': '{ckan_site_url}/organization/test',
    'contact_uri': '{ckan_site_url}/organization/test',
    'dcat_type': {
        'series': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/series',
        'dataset': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
        'spatial_data_service': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/service',
        'default': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
        'collection': 'http://purl.org/dc/dcmitype/Collection',
        'event': 'http://purl.org/dc/dcmitype/Event',
        'image': 'http://purl.org/dc/dcmitype/Image',
        'still_image': 'http://purl.org/dc/dcmitype/StillImage',
        'moving_image': 'http://purl.org/dc/dcmitype/MovingImage',
        'physical_object': 'http://purl.org/dc/dcmitype/PhysicalObject',
        'interactive_resource': 'http://purl.org/dc/dcmitype/InteractiveResource',
        'service': 'http://purl.org/dc/dcmitype/Service',
        'sound': 'http://purl.org/dc/dcmitype/Sound',
        'software': 'http://purl.org/dc/dcmitype/Software',
        'text': 'http://purl.org/dc/dcmitype/Text',
    },
    'encoding': 'UTF-8',
    'frequency' : 'http://publications.europa.eu/resource/authority/frequency/UNKNOWN',
    'inspireid_theme': 'HB',
    'language': 'http://publications.europa.eu/resource/authority/language/ENG',
    'license': 'http://creativecommons.org/licenses/by/4.0/',
    'license_id': 'CC-BY-4.0',
    'license_url': 'https://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'lineage_process_steps': 'ckanext-schemingdcat lineage process steps.',
    'maintainer_name': 'ckanext-schemingdcat',
    'maintainer_email': 'admin@{ckan_site_url}',
    'maintainer_url': '{ckan_site_url}/organization/test',
    'maintainer_uri': '{ckan_site_url}/organization/test',
    'metadata_profile': [
        'http://semiceu.github.io/GeoDCAT-AP/releases/2.0.0','http://inspire.ec.europa.eu/document-tags/metadata'
    ],
    'provenance': 'ckanext-schemingdcat provenance statement.',
    'publisher_name': 'ckanext-schemingdcat',
    'publisher_email': 'admin@{ckan_site_url}',
    'publisher_url': '{ckan_site_url}/organization/test',
    'publisher_identifier': '{ckan_site_url}/organization/test',
    'publisher_uri': '{ckan_site_url}/organization/test',
    'publisher_type': 'http://purl.org/adms/publishertype/NonProfitOrganisation',
    'reference_system': 'http://www.opengis.net/def/crs/EPSG/0/4258',
    'representation_type': {
        'wfs': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/vector',
        'wcs': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/grid',
        'default': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/vector',
        'grid': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/grid',
        'vector': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/vector',
        'textTable': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/textTable',
        'tin': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/tin',
        'stereoModel': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/stereoModel',
        'video': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/video',
    },
    'resources': {
        'availability': 'http://publications.europa.eu/resource/authority/planned-availability/AVAILABLE',
        'name': {
            'es': 'Distribución {format}',
            'en': 'Distribution {format}'
        },
    },
    'rights': 'http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/noLimitations',
    'spatial': None,
    'spatial_uri': 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España',
    'status': 'http://purl.org/adms/status/UnderDevelopment',
    'temporal_start': None,
    'temporal_end': None,
    'theme': 'http://inspire.ec.europa.eu/theme/hb',
    'theme_es': 'http://datos.gob.es/kos/sector-publico/sector/medio-ambiente',
    'theme_eu': 'http://publications.europa.eu/resource/authority/data-theme/ENVI',
    'topic': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/biota',
    'valid': None
}

OGC2CKAN_MD_FORMATS = {
    'api': ('API', 'http://www.iana.org/assignments/media-types/application/vnd.api+json', None, 'Application Programming Interface'),
    'api feature': ('OGCFeat', 'http://www.opengis.net/def/interface/ogcapi-features', 'http://www.opengeospatial.org/standards/features', 'OGC API - Features'),
    'wms': ('WMS', 'http://www.opengis.net/def/serviceType/ogc/wms', 'http://www.opengeospatial.org/standards/wms', 'Web Map Service'),
    'zip': ('ZIP', 'http://www.iana.org/assignments/media-types/application/zip', 'http://www.iso.org/standard/60101.html', 'ZIP File'),
    'rar': ('RAR', 'http://www.iana.org/assignments/media-types/application/vnd.rar', 'http://www.rarlab.com/technote.htm', 'RAR File'),
    'wfs': ('WFS', 'http://www.opengis.net/def/serviceType/ogc/wfs', 'http://www.opengeospatial.org/standards/wfs', 'Web Feature Service'),
    'wcs': ('WCS', 'http://www.opengis.net/def/serviceType/ogc/wcs', 'http://www.opengeospatial.org/standards/wcs', 'Web Coverage Service'),
    'tms': ('TMS', 'http://wiki.osgeo.org/wiki/Tile_Map_Service_Specification', 'http://www.opengeospatial.org/standards/tms', 'Tile Map Service'),
    'wmts': ('WMTS', 'http://www.opengis.net/def/serviceType/ogc/wmts', 'http://www.opengeospatial.org/standards/wmts', 'Web Map Tile Service'),
    'kml': ('KML', 'http://www.iana.org/assignments/media-types/application/vnd.google-earth.kml+xml', 'http://www.opengeospatial.org/standards/kml', 'Keyhole Markup Language'),
    'kmz': ('KMZ', 'http://www.iana.org/assignments/media-types/application/vnd.google-earth.kmz+xml', 'http://www.opengeospatial.org/standards/kml', 'Compressed Keyhole Markup Language'),
    'gml': ('GML', 'http://www.iana.org/assignments/media-types/application/gml+xml', 'http://www.opengeospatial.org/standards/gml', 'Geography Markup Language'),
    'geojson': ('GeoJSON', 'http://www.iana.org/assignments/media-types/application/geo+json', 'http://www.rfc-editor.org/rfc/rfc7946', 'GeoJSON'),
    'json': ('JSON', 'http://www.iana.org/assignments/media-types/application/json', 'http://www.ecma-international.org/publications/standards/Ecma-404.htm', 'JavaScript Object Notation'),
    'atom': ('ATOM', 'http://www.iana.org/assignments/media-types/application/atom+xml', 'http://validator.w3.org/feed/docs/atom.html', 'Atom Syndication Format'),
    'xml': ('XML', 'http://www.iana.org/assignments/media-types/application/xml', 'http://www.w3.org/TR/REC-xml/', 'Extensible Markup Language'),
    'arcgis_rest': ('ESRI Rest', None, None, 'ESRI Rest Service'),
    'shp': ('SHP', 'http://www.iana.org/assignments/media-types/application/vnd.shp', 'http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf', 'ESRI Shapefile'),
    'shapefile': ('SHP', 'http://www.iana.org/assignments/media-types/application/vnd.shp', 'http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf', 'ESRI Shapefile'),
    'esri': ('SHP', 'http://www.iana.org/assignments/media-types/application/vnd.shp', 'http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf', 'ESRI Shapefile'),
    'html': ('HTML', 'http://www.iana.org/assignments/media-types/text/html', 'http://www.w3.org/TR/2011/WD-html5-20110405/', 'HyperText Markup Language'),
    'html5': ('HTML', 'http://www.iana.org/assignments/media-types/text/html', 'http://www.w3.org/TR/2011/WD-html5-20110405/', 'HyperText Markup Language'),
    'visor': ('HTML', 'http://www.iana.org/assignments/media-types/text/html', 'http://www.w3.org/TR/2011/WD-html5-20110405/', 'Map Viewer'),
    'enlace': ('HTML', 'http://www.iana.org/assignments/media-types/text/html', 'http://www.w3.org/TR/2011/WD-html5-20110405/', 'Map Viewer'),
    'pdf': ('PDF', 'http://www.iana.org/assignments/media-types/application/pdf', 'http://www.iso.org/standard/75839.html', 'Portable Document Format'),
    'csv': ('CSV', 'http://www.iana.org/assignments/media-types/text/csv', 'http://www.rfc-editor.org/rfc/rfc4180', 'Comma-Separated Values'),
    'netcdf': ('NetCDF', 'http://www.iana.org/assignments/media-types/text/csv', 'http://www.opengeospatial.org/standards/netcdf', 'Network Common Data Form'),
    'csw': ('CSW', 'http://www.opengis.net/def/serviceType/ogc/csw', 'http://www.opengeospatial.org/standards/cat', 'Catalog Service for the Web'),
    'geodcatap': ('RDF', 'http://www.iana.org/assignments/media-types/application/rdf+xml', 'http://semiceu.github.io/GeoDCAT-AP/releases/2.0.0/', 'GeoDCAT-AP 2.0 Metadata')
    ,
    'inspire': ('XML', 'http://www.iana.org/assignments/media-types/application/xml', ['http://inspire.ec.europa.eu/documents/inspire-metadata-regulation','http://inspire.ec.europa.eu/documents/commission-regulation-eu-no-13122014-10-december-2014-amending-regulation-eu-no-10892010-0', 'http://www.isotc211.org/2005/gmd/'], 'INSPIRE ISO 19139 Metadata')
}

OGC2CKAN_ISO_MD_ELEMENTS = {
    'lineage_source': 'gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:description/gco:CharacterString',
    'lineage_process_steps': 'gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:processStep'
}

# CKAN fields
DATASET_DEFAULT_SCHEMA = [
    'id',
    'type',
    'isopen',
    ]

RESOURCE_DEFAULT_SCHEMA = [
    'url',
    'name',
    ]

DATE_FIELDS = [
    {'field_name': 'created', 'fallback': 'issued', 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'issued', 'fallback': None, 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'modified', 'fallback': 'issued', 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'valid', 'fallback': None, 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'temporal_start', 'fallback': None, 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'temporal_end', 'fallback': None, 'default_value': None, 'override': True, 'dtype': str}
]

DATASET_DEFAULT_FIELDS = [
    {'field_name': 'id', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'name', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'title', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'notes', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'description', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'access_rights', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['access_rights'], 'override': False, 'dtype': str},
    {'field_name': 'license', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['license'], 'override': False, 'dtype': str},
    {'field_name': 'license_id', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['license_id'], 'override': False, 'dtype': str},
    {'field_name': 'topic', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['topic'], 'override': False, 'dtype': str},
    {'field_name': 'theme', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['theme'], 'override': False, 'dtype': str},
    {'field_name': 'theme_eu', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['theme_eu'], 'override': False, 'dtype': str},
    {'field_name': 'status', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['status'], 'override': False, 'dtype': str},
    {'field_name': 'hvd_category', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
]

RESOURCE_DEFAULT_FIELDS = [
    {'field_name': 'url', 'fallback': None, 'default_value': '', 'override': False, 'dtype': str},
    {'field_name': 'name', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'format', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'protocol', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'mimetype', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'description', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'license', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['license'], 'override': False, 'dtype': str},
    {'field_name': 'license_id', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['license_id'], 'override': False, 'dtype': str},
    {'field_name': 'rights', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['rights'], 'override': False, 'dtype': str},
    {'field_name': 'language', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['language'], 'override': False, 'dtype': str},
    {'field_name': 'conforms_to', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'size', 'fallback': None, 'default_value': 0, 'override': False, 'dtype': int},
]

# Vocabs
SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME: typing.Final[str] = 'dataset'
SCHEMINGDCAT_INSPIRE_THEMES_VOCAB: typing.Final[str] = 'theme'
SCHEMINGDCAT_DCAT_THEMES_VOCAB: typing.Final[list] = ['theme_es', 'theme_eu']
SCHEMINGDCAT_ISO19115_TOPICS_VOCAB: typing.Final[list] = 'topic'

INSPIRE_DCAT_TYPES = [
    'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
    'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/series',
    'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/service'
]

DCAT_AP_HVD_CATEGORY_LEGISLATION = 'http://data.europa.eu/eli/reg_impl/2023/138/oj'

DCAT_AP_DATASTORE_DATASERVICE = {
    'uri': '{ckan_site_url}/api/3',
    'title': 'Datastore API service',
    'description': 'This API provides live access to the Datastore portion of the Open Data Portal.',
    'endpoint_description': '{ckan_site_url}/openapi/datastore/',
    'endpoint_url': [
        '{ckan_site_url}/api/3'
    ],
    'serves_dataset': [
        '{ckan_site_url}/dataset/{dataset_id}'
    ]
}

CONTACT_PUBLISHER_FALLBACK = {
    'contact_name': 'ckanext.schemingdcat.dcat_ap.publisher.name',
    'contact_email': 'ckanext.schemingdcat.dcat_ap.publisher.email',
    'contact_url': 'ckanext.schemingdcat.dcat_ap.publisher.url',
    'contact_uri': 'ckanext.schemingdcat.dcat_ap.publisher.identifier',
    'contact_role': 'http://inspire.ec.europa.eu/metadata-codelist/ResponsiblePartyRole/pointOfContact'
}

BASE_VOCABS = {
    'eu_publications': 'http://publications.europa.eu/resource/authority/',
    'eu_inspire': 'http://inspire.ec.europa.eu/metadata-codelist',
    'eu_inspire_theme': 'http://inspire.ec.europa.eu/theme/',
    'publisher_type_purl': '"http://purl.org/adms/publishertype/',
    'iana_mimetype': 'http://www.iana.org/assignments/media-types/',
    'epsg_opengis': 'http://www.opengis.net/def/crs/EPSG/0/',
    'es_publisher_org': 'http://datos.gob.es/recurso/sector-publico/org/Organismo/',
}

FREQUENCY_MAPPING = {      
    # Minutes
    "http://publications.europa.eu/resource/authority/frequency/1MIN": ("minutes", "1", {"es": "minuto", "en": "minute"}, True),
    "http://publications.europa.eu/resource/authority/frequency/5MIN": ("minutes", "5", {"es": "minutos", "en": "minutes"}, True),
    "http://publications.europa.eu/resource/authority/frequency/10MIN": ("minutes", "10", {"es": "minutos", "en": "minutes"}, True),
    "http://publications.europa.eu/resource/authority/frequency/15MIN": ("minutes", "15", {"es": "minutos", "en": "minutes"}, True),
    "http://publications.europa.eu/resource/authority/frequency/30MIN": ("minutes", "30", {"es": "minutos", "en": "minutes"}, True),
    
    # Hours
    "http://publications.europa.eu/resource/authority/frequency/HOURLY": ("hours", "1", {"es": "hora", "en": "hour"}, True),
    "http://publications.europa.eu/resource/authority/frequency/BIHOURLY": ("hours", "2", {"es": "horas", "en": "hours"}, True),
    "http://publications.europa.eu/resource/authority/frequency/TRIHOURLY": ("hours", "3", {"es": "horas", "en": "hours"}, True),
    "http://publications.europa.eu/resource/authority/frequency/12HRS": ("hours", "12", {"es": "horas", "en": "hours"}, True),
    
    # Days
    "http://publications.europa.eu/resource/authority/frequency/MONTHLY_2": ("days", "15", {"es": "días", "en": "days"}, True),
    "http://publications.europa.eu/resource/authority/frequency/MONTHLY_3": ("days", "10", {"es": "días", "en": "days"}, True),
    "http://publications.europa.eu/resource/authority/frequency/WEEKLY": ("days", "7", {"es": "días", "en": "days"}, True),
    "http://publications.europa.eu/resource/authority/frequency/WEEKLY_2": ("days", "3", {"es": "días", "en": "days"}, True),
    "http://publications.europa.eu/resource/authority/frequency/WEEKLY_3": ("days", "2", {"es": "días", "en": "days"}, True),
    "http://publications.europa.eu/resource/authority/frequency/BIWEEKLY": ("days", "14", {"es": "días", "en": "days"}, True),
    "http://publications.europa.eu/resource/authority/frequency/DAILY": ("days", "1", {"es": "día", "en": "day"}, True),
    "http://publications.europa.eu/resource/authority/frequency/DAILY_2": ("hours", "12", {"es": "horas", "en": "hours"}, True),
    "http://publications.europa.eu/resource/authority/frequency/CONT": ("days", "1", {"es": "día", "en": "day"}, True),
    "http://publications.europa.eu/resource/authority/frequency/UPDATE_CONT": ("days", "1", {"es": "día", "en": "day"}, True),
    
    # Months
    "http://publications.europa.eu/resource/authority/frequency/MONTHLY": ("months", "1", {"es": "mes", "en": "month"}, True),
    "http://publications.europa.eu/resource/authority/frequency/BIMONTHLY": ("months", "2", {"es": "meses", "en": "months"}, True),
    "http://publications.europa.eu/resource/authority/frequency/ANNUAL_2": ("months", "6", {"es": "meses", "en": "months"}, True),
    "http://publications.europa.eu/resource/authority/frequency/ANNUAL_3": ("months", "4", {"es": "meses", "en": "months"}, True),
    "http://publications.europa.eu/resource/authority/frequency/QUARTERLY": ("months", "3", {"es": "meses", "en": "months"}, True),

    # Years
    "http://publications.europa.eu/resource/authority/frequency/ANNUAL": ("years", "1", {"es": "año", "en": "year"}, True),
    "http://publications.europa.eu/resource/authority/frequency/BIENNIAL": ("years", "2", {"es": "años", "en": "years"}, True),
    "http://publications.europa.eu/resource/authority/frequency/TRIENNIAL": ("years", "3", {"es": "años", "en": "years"}, True),
    "http://publications.europa.eu/resource/authority/frequency/QUADRENNIAL": ("years", "4", {"es": "años", "en": "years"}, True),
    "http://publications.europa.eu/resource/authority/frequency/QUINQUENNIAL": ("years", "5", {"es": "años", "en": "years"}, True),
    "http://publications.europa.eu/resource/authority/frequency/DECENNIAL": ("years", "10", {"es": "años", "en": "years"}, True),
    "http://publications.europa.eu/resource/authority/frequency/BIDECENNIAL": ("years", "20", {"es": "años", "en": "years"}, True),
    "http://publications.europa.eu/resource/authority/frequency/TRIDECENNIAL": ("years", "30", {"es": "años", "en": "years"}, True),
    
    # Special values without numerical value in the label
    "http://publications.europa.eu/resource/authority/frequency/NEVER": ("days", "0", {"es": "nunca", "en": "never"}, False),
    "http://publications.europa.eu/resource/authority/frequency/NOT_PLANNED": ("days", "0", {"es": "no planificado", "en": "not planned"}, False),   
    
    # Other - special values without numerical value
    "http://publications.europa.eu/resource/authority/frequency/IRREG": ("days", "0", {"es": "irregular", "en": "irregular"}, False),
    "http://publications.europa.eu/resource/authority/frequency/UNKNOWN": ("days", "0", {"es": "desconocido", "en": "unknown"}, False),
    "http://publications.europa.eu/resource/authority/frequency/OTHER": ("days", "0", {"es": "otro", "en": "other"}, False),
    "http://publications.europa.eu/resource/authority/frequency/OP_DATPRO": ("days", "0", {"es": "en proceso", "en": "in process"}, False),
    "http://publications.europa.eu/resource/authority/frequency/AS_NEEDED": ("days", "0", {"es": "según necesidad", "en": "as needed"}, False),
}