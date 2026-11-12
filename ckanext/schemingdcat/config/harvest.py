# Custom rules for harvesters.base._update_custom_format()
CUSTOM_FORMAT_RULES = [
    {
        'format_strings': ['esri', 'arcgis'],
        'url_string': 'viewer.html?url=',
        'format': 'HTML',
        'mimetype': 'https://www.iana.org/assignments/media-types/text/html'
    },
    {
        'format_strings': ['html', 'html5'],
        'url_string': None,
        'format': 'HTML',
        'mimetype': 'https://www.iana.org/assignments/media-types/text/html'
    },
    {
        'format_strings': None,
        'url_string': 'getrecordbyid',
        'format': 'XML',
        'mimetype': 'https://www.iana.org/assignments/media-types/application/xml'
    }
    # Add more rules here as needed
]

DATADICTIONARY_DEFAULT_SCHEMA = [
    'id',
    'type',
    'label',
    'notes',
    'type_override'
    ]

# CKAN tags fields to be searched in the harvester
AUX_TAG_FIELDS = [
    'tag_string',
    'keywords'
]

URL_FIELD_NAMES = {
        'dataset': 
            ['dcat_type', 'theme_es', 'language', 'topic', 'maintainer_url', 'tag_uri', 'contact_uri', 'contact_url', 'publisher_identifier', 'publisher_uri', 'publisher_url', 'publisher_type', 'maintainer_uri', 'maintainer_url', 'author_uri', 'author_url', 'conforms_to', 'theme', 'reference_system', 'spatial_uri', 'representation_type', 'license_id', 'access_rights', 'graphic_overview', 'frequency', 'hvd_category'],
        'resource':
            ['url', 'availability', 'mimetype', 'status', 'resource_relation', 'license', 'rights', 'conforms_to', 'reference_system']
    }
EMAIL_FIELD_NAMES = ['publisher_email', 'maintainer_email', 'author_email', ]

# Fields to be explicit excluded from the harvester list parser because they are not lists
XLS_HARVESTER_FIELDS_NOT_LIST = ['access_rights']