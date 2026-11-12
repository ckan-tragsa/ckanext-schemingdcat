import re

# Cache
linkeddata_links = None
geometadata_links = None
endpoints = None
catalog_publisher_info = {}
## dict of local schemas dicts
schemas = {}
form_tabs = {}
form_tabs_grouping = None
form_groups = {}
## Custom facets
dataset_custom_facets = {}
## Social info
social_links = {}

# loose definition of BCP47-like strings
BCP_47_LANGUAGE = u'^[a-z]{2,8}(-[0-9a-zA-Z]{1,8})*$'

slugify_pat = re.compile('[^a-zA-Z0-9]')

# Clean ckan names
URL_REGEX = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

# Compile the regular expression
INVALID_CHARS = re.compile(r"[^a-zñ0-9_.-]")
TAGS_NORMALIZE_PATTERN = re.compile(r'[^a-záéíóúüñ0-9\-_\.]')

# Define a dictionary to map accented characters to their unaccented equivalents except ñ
ACCENT_MAP = str.maketrans({
    "á": "a", "à": "a", "ä": "a", "â": "a", "ã": "a",
    "é": "e", "è": "e", "ë": "e", "ê": "e",
    "í": "i", "ì": "i", "ï": "i", "î": "i",
    "ó": "o", "ò": "o", "ö": "o", "ô": "o", "õ": "o",
    "ú": "u", "ù": "u", "ü": "u", "û": "u",
    "ñ": "ñ",
})

# Common date formats for parsing. https://docs.python.org/es/3/library/datetime.html#strftime-and-strptime-format-codes
COMMON_DATE_FORMATS = [
    '%Y-%m-%d',
    '%d-%m-%Y',
    '%m-%d-%Y',
    '%Y/%m/%d',
    '%d/%m/%Y',
    '%m/%d/%Y',
    '%Y-%m-%d %H:%M:%S',  # Date with time
    '%d-%m-%Y %H:%M:%S',  # Date with time
    '%m-%d-%Y %H:%M:%S',  # Date with time
    '%Y/%m/%d %H:%M:%S',  # Date with time
    '%d/%m/%Y %H:%M:%S',  # Date with time
    '%m/%d/%Y %H:%M:%S',  # Date with time
    '%Y-%m-%dT%H:%M:%S',  # ISO 8601 format
    '%Y-%m-%dT%H:%M:%SZ',  # ISO 8601 format with Zulu time indicator
]