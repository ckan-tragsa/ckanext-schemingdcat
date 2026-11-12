# config/__init__.py
from ckanext.schemingdcat.config.default import *
from ckanext.schemingdcat.config.harvest import *
from ckanext.schemingdcat.config.metadata import *
from ckanext.schemingdcat.config.tools import *

# Harvester config
from ckanext.schemingdcat.config.harvest_csw import *


# Config vars allowed
__all__ = [
    # From default.py
    'mimetype_base_uri'
    'field_mapping_extras_prefix'
    'field_mapping_extras_prefix_symbol'
    'epsg_uri_template',
    'geojson_tolerance',
    'translate_validator_tags',

    # From harvest.py
    'CUSTOM_FORMAT_RULES',
    'DATADICTIONARY_DEFAULT_SCHEMA',
    'AUX_TAG_FIELDS',
    'URL_FIELD_NAMES',
    'EMAIL_FIELD_NAMES',
    'XLS_HARVESTER_FIELDS_NOT_LIST',

    # From metadata.py
    'OGC2CKAN_HARVESTER_MD_CONFIG',
    'OGC2CKAN_MD_FORMATS',
    'OGC2CKAN_ISO_MD_ELEMENTS',
    ## CKAN fields
    'DATASET_DEFAULT_SCHEMA',
    'RESOURCE_DEFAULT_SCHEMA',
    'DATE_FIELDS',
    'DATASET_DEFAULT_FIELDS',
    'RESOURCE_DEFAULT_FIELDS',
    ## Vocabularies
    'SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME',
    'SCHEMINGDCAT_INSPIRE_THEMES_VOCAB',
    'SCHEMINGDCAT_DCAT_THEMES_VOCAB',
    'SCHEMINGDCAT_ISO19115_TOPICS_VOCAB',
    'INSPIRE_DCAT_TYPES',
    'DCAT_AP_HVD_CATEGORY_LEGISLATION',
    'DCAT_AP_DATASTORE_DATASERVICE',
    'CONTACT_PUBLISHER_FALLBACK',
    'BASE_VOCABS',
    'FREQUENCY_MAPPING',

    # From tools.py
    'linkeddata_links',
    'geometadata_links',
    'endpoints',
    'catalog_publisher_info',
    'schemas',
    'form_tabs',
    'form_tabs_grouping',
    'form_groups',
    'dataset_custom_facets',
    'social_links',
    'BCP_47_LANGUAGE',
    'slugify_pat',
    'URL_REGEX',
    'INVALID_CHARS',
    'TAGS_NORMALIZE_PATTERN',
    'ACCENT_MAP',
    'COMMON_DATE_FORMATS'
    
    # From harvest_csw.py
    'XLST_MAPPINGS_DIR',
    'DEFAULT_XSLT_FILE',
    'DOWNLOAD_PROTOCOL',
    'OGC_WMTS_PROTOCOL',
    'OGC_WFS_PROTOCOL',
    'OGC_WMS_PROTOCOL',
    'LINKED_DATA_PROTOCOL',
    'APP_PROTOCOL',
    'ESRI_REST_PROTOCOL',
    'MAP_PROTOCOL',
    'PROTOCOL_MAPPING',
    'SERVICE_FORMAT',
    'API_FORMAT',
    'LINKED_DATA_SERVICE',
    'FORMAT_MAPPING',
    'RESOURCE_TYPES',
    'FILE_TYPES',
    'FORMAT_STANDARDIZATION',
    'SERVICE_INDICATORS',
    'DCAT_SERVICE_TYPES',
    'ISO19115_LANGUAGE',
    'ISO19115_HIERARCHY',
    'ISO19115_INSPIRE_DEFAULT_VALUES',
    'ISO19115_REPRESENTATION_TYPE',
    'ISO19115_CHARACTER_ENCODING',
    'ISO19115_TOPIC_CATEGORY',
    ## CSW processor configuration
    'CSW_DEFAULT_LIMIT',
    'CQL_QUERY_DEFAULT',
    'CQL_SEARCH_TERM_DEFAULT',
    'OUTPUT_SCHEMA',
    'INSPIRE_HVD_CATEGORY',
    'INSPIRE_HVD_APPLICABLE_LEGISLATION',
]