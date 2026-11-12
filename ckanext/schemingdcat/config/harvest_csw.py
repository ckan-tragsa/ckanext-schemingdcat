import os

# Define the base directory of the repository dynamically
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))

# XLSTransformer configuration
XLST_MAPPINGS_DIR = os.path.join(BASE_DIR, 'ckanext/schemingdcat/lib/csw_mapper/xslt/mappings')
# GeoDCAT-AP official XSLT
DEFAULT_XSLT_FILE = 'https://raw.githubusercontent.com/SEMICeu/iso-19139-to-dcat-ap/refs/heads/geodcat-ap-2.0.0/iso-19139-to-dcat-ap.xsl'

# CSW processor configuration
CSW_DEFAULT_LIMIT = None
CQL_QUERY_DEFAULT = 'csw:AnyText'
CQL_SEARCH_TERM_DEFAULT = None
OUTPUT_SCHEMA = 'http://www.isotc211.org/2005/gmd'

# Define normalized protocol constants
DOWNLOAD_PROTOCOL = "WWW:DOWNLOAD"
OGC_WMTS_PROTOCOL = "OGC:WMTS"
OGC_WFS_PROTOCOL = "OGC:WFS"
OGC_WMS_PROTOCOL = "OGC:WMS"
LINKED_DATA_PROTOCOL = "LINKED:DATA"
APP_PROTOCOL = "WWW:DOWNLOAD-APP"
ESRI_REST_PROTOCOL = "ESRI:REST"
MAP_PROTOCOL = 'MAP:PREVIEW'

# DCAT-AP HVD
INSPIRE_HVD_CATEGORY = "http://data.europa.eu/bna/c_ac64a52d"
INSPIRE_HVD_APPLICABLE_LEGISLATION = "http://data.europa.eu/eli/reg_impl/2023/138/oj"

# Definir una correspondencia completa entre los identificadores de protocolo y los protocolos normalizados
PROTOCOL_MAPPING = {
    # OGC Services
    'ogc:wms': 'WMS',
    'ogc:wms-': 'WMS',
    'ogc:wfs': 'WFS',
    'ogc:wfs-': 'WFS',
    'ogc:wmts': 'WMTS',
    'ogc:wmts-': 'WMTS',
    'ogc:wcs': 'WCS',
    'ogc:wcs-': 'WCS',
    'ogc:csw': 'CSW',
    'ogc:sos': 'SOS',
    'ogc:wps': 'WPS',
    'ogc:wcts': 'WCTS',
    'ogc:wns': 'WNS',
    'ogc:gml': 'GML',
    'ogc:kml': 'KML',
    'ogc:wmc': 'WMC',
    
    # Specific versions (maintain for compatibility)
    'ogc:wms-1.1.1-http-get-map': 'WMS',
    'ogc:wms-1.3.0-http-get-map': 'WMS',
    'ogc:wms-1.1.1-http-get-capabilities': 'WMS',
    'ogc:wms-1.3.0-http-get-capabilities': 'WMS',
    'ogc:wfs-1.0.0-http-get-capabilities': 'WFS',
    'ogc:wfs-g': 'WFS',
    'ogc:wmts-1.0.0-http-get-capabilities': 'WMTS',
    'ogc:wcs-1.1.0-http-get-capabilities': 'WCS',
    'ogc:sos-1.0.0-http-get-observation': 'SOS',
    'ogc:sos-1.0.0-http-post-observation': 'SOS',
    
    # Descriptive names
    'web map service': 'WMS',
    'web feature service': 'WFS',
    'web coverage service': 'WCS',
    'web map tile service': 'WMTS',
    
    # ESRI Services
    'esri:aims-http-configuration': 'HTTP',
    'esri:aims-http-get-feature': 'HTTP',
    'esri:aims-http-get-image': 'HTTP',
    'esri:rest': 'ESRI_REST',
    'arcgis:rest': 'ESRI_REST',
    'arcgis/rest/services': 'ESRI_REST',
    
    # Other services
    'glg:kml-2.0-http-get-map': 'KML',
    'tms': 'TMS',
    
    # Download formats
    'www:download-1.0-http-download': 'HTTP',
    'www:download-1.0-ftp-download': 'FTP',
    'www:download': 'HTTP',
    
    # Web URLs
    'www:link-1.0-http-link': 'HTML',
    'www:link-1.0-http-related': 'HTML',
    'www:link-1.0-http-partners': 'HTML',
    'www:link-1.0-http-samples': 'HTML',
    'www:link-1.0-http-ical': 'ICAL',
    'www:link-1.0-http-rss': 'HTTP',
    'www:link-1.0-http-opendap': 'HTTP',
    'www:link': 'HTML',
    
    # File formats/MIME
    'html': 'HTML',
    'htm': 'HTML',
    'text/html': 'HTML',
    'application/html': 'HTML',
    'aspx': 'HTML',
    'php': 'HTML',
    'jsp': 'HTML',
    
    'xml': 'XML',
    'application/xml': 'XML',
    'text/xml': 'XML',
    
    'json': 'JSON',
    'application/json': 'JSON',
    'application/geojson': 'GEOJSON',
    'geojson': 'GEOJSON',
    
    'gml': 'GML',
    'application/gml+xml': 'GML',
    
    'kml': 'KML',
    'application/vnd.google-earth.kml+xml': 'KML',
    
    'pdf': 'PDF',
    'application/pdf': 'PDF',
    
    'zip': 'ZIP',
    'application/zip': 'ZIP',
    
    'csv': 'CSV',
    'text/csv': 'CSV',
    
    'xls': 'XLS',
    'xlsx': 'XLSX',
    'application/vnd.ms-excel': 'XLS',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    
    'shp': 'SHP',
    'shapefile': 'SHP',
    
    'octet-stream': 'BINARY',
    'application/octet-stream': 'BINARY',
    'binary': 'BINARY',
    
    # Valor por defecto (cuando no hay coincidencia)
    'default': 'HTML'
}

# Patterns to detect formatting in URLs and names
FORMAT_STANDARDIZATION = {
    'format_patterns': {
        # OGC Services
        'wms': 'WMS',
        'service=wms': 'WMS',
        'ogc:wms': 'WMS',
        'getcapabilities': 'HTML',  # Typically XML metadata but presented as HTML
        
        'wfs': 'WFS',
        'service=wfs': 'WFS',
        'ogc:wfs': 'WFS',
        
        'wmts': 'WMTS',
        'service=wmts': 'WMTS',
        
        'wcs': 'WCS',
        'service=wcs': 'WCS',
        
        'csw': 'CSW',
        'service=csw': 'CSW',
        
        # ESRI Services
        'arcgis/rest': 'ESRI_REST',
        'mapserver': 'MAPSERVER',
        'geoserver': 'GEOSERVER',
        
        # GIS viewers and webs
        'visor': 'HTML',
        'viewer': 'HTML',
        'portal': 'HTML',
        'enlace': 'HTML',
        'link': 'HTML',
        'html': 'HTML',
        'htm': 'HTML',
        'aspx': 'HTML',
        'php': 'HTML',
        'web': 'HTML',
        
        # Files
        '.zip': 'ZIP',
        '.shp': 'SHP',
        '.gml': 'GML',
        '.kml': 'KML',
        '.kmz': 'KMZ',
        '.pdf': 'PDF',
        '.csv': 'CSV',
        '.json': 'JSON',
        '.geojson': 'GEOJSON',
        '.xml': 'XML',
        '.xls': 'XLS',
        '.xlsx': 'XLSX',
        '.doc': 'DOC',
        '.docx': 'DOCX',
        '.tif': 'TIFF',
        '.tiff': 'TIFF',
        '.png': 'PNG',
        '.jpg': 'JPEG',
        '.jpeg': 'JPEG',
        
        # Default
        'default': 'HTML',
    },
    
    # Format to mimetypes
    'mimetype_mapping': {
        # OGC Services
        'WMS': 'application/vnd.ogc.wms_xml',
        'WFS': 'application/gml+xml',
        'WMTS': 'application/vnd.ogc.wmts+xml',
        'WCS': 'application/xml',
        'CSW': 'application/xml',
        'SOS': 'application/xml',
        'WPS': 'application/xml',
        
        # Common formats
        'HTML': 'text/html',
        'XML': 'application/xml',
        'JSON': 'application/json',
        'GEOJSON': 'application/geo+json',
        'GML': 'application/gml+xml',
        'KML': 'application/vnd.google-earth.kml+xml',
        'KMZ': 'application/vnd.google-earth.kmz',
        'PDF': 'application/pdf',
        'ZIP': 'application/zip',
        'SHP': 'application/octet-stream',  # Not official mimetype
        'CSV': 'text/csv',
        'XLS': 'application/vnd.ms-excel',
        'XLSX': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'DOC': 'application/msword',
        'DOCX': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'TIFF': 'image/tiff',
        'PNG': 'image/png',
        'JPEG': 'image/jpeg',
        'BINARY': 'application/octet-stream',
        'ESRI_REST': 'application/json',
        
        # Default
        'default': 'text/html'
    }
}

# Add a dictionary for specific services
SERVICE_INDICATORS = {
    'WMS': ['wms', 'service=wms', 'request=getcapabilities', 'request=getmap', 'layers='],
    'WFS': ['wfs', 'service=wfs', 'request=getfeature', 'typename='],
    'WMTS': ['wmts', 'service=wmts'],
    'CSW': ['csw', 'service=csw'],
    'SOS': ['sos', 'service=sos'],
    'ESRI_REST': ['arcgis/rest', 'mapserver', 'imageserver', 'featureserver', 'f=json'],
}
SERVICE_FORMAT = 'SERVICE'
API_FORMAT = 'API'
LINKED_DATA_SERVICE = "Linked Data Service"

FORMAT_MAPPING = {
    DOWNLOAD_PROTOCOL: ('FORMAT_FROM_PROTOCOL', 'FORMAT_FROM_PROTOCOL'),
    LINKED_DATA_PROTOCOL: ('FORMAT_FROM_PROTOCOL_IF_NOT_DATA', API_FORMAT),
    ESRI_REST_PROTOCOL: (SERVICE_FORMAT, API_FORMAT),
    APP_PROTOCOL: (SERVICE_FORMAT, API_FORMAT),
    MAP_PROTOCOL: (SERVICE_FORMAT, API_FORMAT),
    OGC_WMS_PROTOCOL: ('WMS', API_FORMAT),
    OGC_WFS_PROTOCOL: ('WFS', API_FORMAT),
    OGC_WMTS_PROTOCOL: ('WMTS', API_FORMAT),
    'OGC:WCS': ('WCS', API_FORMAT),
    'OGC:CSW': ('CSW', API_FORMAT),
    'OGC:SOS': ('SOS', API_FORMAT),
    'OGC:WCTS': ('WCTS', API_FORMAT),
    'WNS': ('WNS', API_FORMAT),
    'WPS': ('WPS', API_FORMAT),
    'TMS': ('TMS', API_FORMAT),
    'FTP': ('FTP', 'FTP'),
    'HTTP': ('HTTP', 'HTTP'),
    'ICAL': ('ICAL', 'ICAL'),
    # Add other mappings as needed
}

RESOURCE_TYPES = {
    'wms': ('/wms', 'service=wms', 'geoserver/wms', 'mapserver/wmsserver', 'com.esri.wms.Esrimap', 'service/wms'),
    'wfs': ('/wfs', 'service=wfs', 'geoserver/wfs', 'mapserver/wfsserver', 'com.esri.wfs.Esrimap'),
    'wcs': ('/wcs', 'service=wcs', 'geoserver/wcs', 'imageserver/wcsserver', 'mapserver/wcsserver'),
    'sos': ('/sos', 'service=sos'),
    'csw': ('/csw', 'service=csw'),
    'wmts': ('/wmts', 'service=wmts'),
    'kml': ('.kml', 'kml'),
    'kmz': ('.kmz',),
    'tms': ('/tms',),
    'esri_rest': ('arcgis/rest/services',),
}
    
FILE_TYPES = {
    'kml': ('kml',),
    'kmz': ('kmz',),
    'gml': ('gml',),
    'tif': ('tif', 'tiff'),
    'shp': ('shp',),
    'zip': ('zip',),
    'geojson': ('geojson', 'json'),
    'pdf': ('pdf',),
    'docx': ('docx', 'doc'),
    'pptx': ('pptx', 'ppt'),
    'xlsx': ('xlsx', 'xls'),
    'csv': ('csv',),
    'json': ('json',),
    'html': ('html', 'htm'),
    'xml': ('xml',),
    'geopackage': ('gpkg',),
    'sqlite': ('sqlite', 'db'),
    'exe': ('exe',),
    'bat': ('bat',),
    'sh': ('sh',),
    'zip': ('zip', 'rar', '7z', 'tar', 'gz', 'bz2'),
    'jpg': ('jpg', 'jpeg'),
    'png': ('png',),
    'gif': ('gif',),
    'tiff': ('tiff', 'tif'),
    'bmp': ('bmp',),
    'svg': ('svg',),
    'cad': ('dwg', 'dxf'),
    'kmz': ('kmz',),
    'gml': ('gml',),
    'txt': ('txt',),
    'rtf': ('rtf',),
    'odt': ('odt',),
    'ods': ('ods',),
    'odp': ('odp',),
    'ppt': ('ppt',),
    'xls': ('xls',),
    'doc': ('doc',),
    'pptm': ('pptm',),
    'xlsm': ('xlsm',),
    'dotx': ('dotx',),
    'potx': ('potx',),
    # Add other mappings as needed
}

# Mapping of languages to ISO 639-1 codes
ISO19115_LANGUAGE = {
    'spa': 'es',
    'cat': 'ca',
    'eus': 'eu',
    'glg': 'gl',
    'eng': 'en',
    'deu': 'de',
    'ger': 'de',
    'fra': 'fr',
    'fre': 'fr',
    'ita': 'it',
    'nld': 'nl',
    'dut': 'nl',
    'por': 'pt',
    'fin': 'fi',
    'swe': 'sv',
    'ces': 'cs',
    'cze': 'cs',
    'est': 'et',
    'hrv': 'hr',
    'hun': 'hu',
    'lav': 'lv',
    'lit': 'lt',
    'ltz': 'lb',
    'mlt': 'mt',
    'pol': 'pl',
    'slk': 'sk',
    'slo': 'sk',
    'slv': 'sl',
    'rom': 'ro',
    'rum': 'ro'
}

# Mapping of ISO 19115 hierarchy levels to dcat_type (GeoDCAT-AP)
ISO19115_HIERARCHY = {
    'dataset': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
    'series': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/series',
    'service': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/service',
    'default': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
}

# Mapping of ISO 19115 spatial representation types to INSPIRE Metadata codelist
ISO19115_REPRESENTATION_TYPE = {
    'wfs': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/vector',
    'wcs': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/grid',
    'grid': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/grid',
    'vector': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/vector',
    'textTable': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/textTable',
    'tin': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/tin',
    'stereoModel': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/stereoModel',
    'video': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/video',
    'default': None,
}

# Mapping of ISO 19115 topic categories to INSPIRE Metadata codelist
ISO19115_TOPIC_CATEGORY = {
    'biota': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/biota',
    'boundaries': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/boundaries',
    'climatologyMeteorologyAtmosphere': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/climatologyMeteorologyAtmosphere',
    'economy': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/economy',
    'elevation': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/elevation',
    'environment': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/environment',
    'farming': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/farming',
    'geoscientificInformation': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/geoscientificInformation',
    'health': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/health',
    'imageryBaseMapsEarthCover': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/imageryBaseMapsEarthCover',
    'inlandWaters': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/inlandWaters',
    'intelligenceMilitary': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/intelligenceMilitary',
    'location': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/location',
    'oceans': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/oceans',
    'planningCadastre': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/planningCadastre',
    'society': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/society',
    'structure': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/structure',
    'transportation': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/transportation',
    'utilitiesCommunication': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/utilitiesCommunication',
    'default': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/environment'  # Default category if none specified
}

# EU GeoDCAT-AP Profile: Mandatory catalog elements by GeoDCAT-AP.
ISO19115_INSPIRE_DEFAULT_VALUES = {
    'availability': 'http://publications.europa.eu/resource/authority/planned-availability/AVAILABLE',
    'access_rights': 'http://publications.europa.eu/resource/authority/access-right/PUBLIC',
    'author_role': 'http://inspire.ec.europa.eu/metadata-codelist/ResponsiblePartyRole/author',
    'conformance': 'http://data.europa.eu/930/',
    'contact_role': 'http://inspire.ec.europa.eu/metadata-codelist/ResponsiblePartyRole/pointOfContact',
    'description': 'Resource without description.',
    'description_en': 'Resource without description.',
    'description_es': 'Recurso sin descripción.',
    'language': 'http://publications.europa.eu/resource/authority/language/ENG',
    'license': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'license_url': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'maintainer_role': 'http://inspire.ec.europa.eu/metadata-codelist/ResponsiblePartyRole/custodian',
    'metadata_profile': [
        'http://semiceu.github.io/GeoDCAT-AP/releases/3.0.0','http://inspire.ec.europa.eu/document-tags/metadata'
    ],
    'notes': 'Dataset without description.',
    'notes_es': 'Conjunto de datos sin descripción.',
    'notes_en': 'Dataset without description.',
    'publisher_identifier': 'http://datos.gob.es/recurso/sector-publico/org/Organismo/EA0007777',
    'publisher_type': 'http://purl.org/adms/publishertype/NonProfitOrganisation',
    'publisher_role': 'http://inspire.ec.europa.eu/metadata-codelist/ResponsiblePartyRole/distributor',
    'reference_system_type': 'http://inspire.ec.europa.eu/glossary/SpatialReferenceSystem',
    'status': 'http://publications.europa.eu/resource/authority/distribution-status/COMPLETED',
    'theme_es': 'http://datos.gob.es/kos/sector-publico/sector/sector-publico',
    'theme_eu': 'http://publications.europa.eu/resource/authority/data-theme/GOVE',
    'theme_taxonomy': 'http://inspire.ec.europa.eu/theme',
    'theme_es_taxonomy': 'http://datos.gob.es/kos/sector-publico/sector',
    'theme_eu_taxonomy': 'http://publications.europa.eu/resource/authority/data-theme',
    'rights_uri_label': 'Rights related to the re-use of the Open Data Catalogue',
    'rights_attribution_text': 'Attribution of authorship to the organisation.',
    'spatial_uri': 'http://publications.europa.eu/resource/authority/country/ESP',
}

ISO19115_CHARACTER_ENCODING = {
    'ucs2': 'ISO-10646-UCS-2',
    'ucs4': 'ISO-10646-UCS-4',
    'utf7': 'UTF-7',
    'utf8': 'UTF-8',
    'utf16': 'UTF-16',
    '8859part1': 'ISO-8859-1',
    '8859part2': 'ISO-8859-2',
    '8859part3': 'ISO-8859-3',
    '8859part4': 'ISO-8859-4',
    '8859part5': 'ISO-8859-5',
    '8859part6': 'ISO-8859-6',
    '8859part7': 'ISO-8859-7',
    '8859part8': 'ISO-8859-8',
    '8859part9': 'ISO-8859-9',
    '8859part10': 'ISO-8859-10',
    '8859part11': 'ISO-8859-11',
    '8859part12': 'ISO-8859-12',
    '8859part13': 'ISO-8859-13',
    '8859part14': 'ISO-8859-14',
    '8859part15': 'ISO-8859-15',
    '8859part16': 'ISO-8859-16',
    'jis': 'JIS_Encoding',
    'shiftJIS': 'Shift_JIS',
    'eucJP': 'EUC-JP',
    'usAscii': 'US-ASCII',
    'ebcdic': 'IBM037',
    'eucKR': 'EUC-KR',
    'big5': 'Big5',
    'GB2312': 'GB2312',
    'default': 'UTF-8'  # Default encoding if none specified
}

# Dictionary mapping service types to their standard URIs
DCAT_SERVICE_SERVICE_TYPE_URIS = {
    "WMS": "http://www.opengis.net/def/serviceType/ogc/wms",
    "WFS": "http://www.opengis.net/def/serviceType/ogc/wfs",
    "WCS": "http://www.opengis.net/def/serviceType/ogc/wcs",
    "CSW": "http://www.opengis.net/def/serviceType/ogc/csw",
    "WMTS": "http://www.opengis.net/def/serviceType/ogc/wmts",
    "SOS": "http://www.opengis.net/def/serviceType/ogc/sos",
    "API": "http://www.opengis.net/def/serviceType/ogc/api",
    "REST": "http://www.opengis.net/def/serviceType/ogc/rest",
    "ATOM": "http://www.opengis.net/def/serviceType/ogc/atom"
}

# Consolidated service type information
DCAT_SERVICE_TYPES = {
    "WMS": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/wms",
        "protocol_indicators": ["wms", "view", "ogc:wms", "web map service"],
        "url_indicators": ["wms", "service=wms", "request=getcapabilities", "request=getmap", "layers="],
        "name_indicators": ["wms", "web map service"],
        "default_title": "Web Map Service",
        "capabilities_param": "request=GetCapabilities&service=WMS",
        "mime_type": "application/vnd.ogc.wms_xml",
        "multilingual_title": {
            "en": "Web Map Service (WMS)",
            "es": "Servicio Web de Mapas (WMS)"
        },
        "multilingual_description": {
            "en": "OGC Web Map Service (WMS) provides a simple HTTP interface for requesting geo-registered map images from one or more distributed geospatial databases. For more specific information, please check the endpoint description.",
            "es": "El servicio Web Map Service (WMS) definido por el Open Geospatial Consortium (OGC) permite visualizar información geográfica como mapas. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "WFS": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/wfs",
        "protocol_indicators": ["wfs", "download", "ogc:wfs", "web feature service"],
        "url_indicators": ["wfs", "service=wfs", "request=getfeature", "typename="],
        "name_indicators": ["wfs", "web feature service"],
        "default_title": "Web Feature Service",
        "capabilities_param": "request=GetCapabilities&service=WFS",
        "mime_type": "application/gml+xml",
        "multilingual_title": {
            "en": "Web Feature Service (WFS)",
            "es": "Servicio Web de Entidades (WFS)"
        },
        "multilingual_description": {
            "en": "OGC Web Feature Service (WFS) provides an interface allowing requests for geographical features across the web using platform-independent calls. For more specific information, please check the endpoint description.",
            "es": "El servicio Web Feature Service (WFS) está definido por el Open Geospatial Consortium (OGC) con el objeto de proporcionar la información relativa a la entidad almacenada en una cobertura vectorial que reúnen las características formuladas en la consulta. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "WCS": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/wcs",
        "protocol_indicators": ["wcs", "coverage", "ogc:wcs", "web coverage service"],
        "url_indicators": ["wcs", "service=wcs"],
        "name_indicators": ["wcs", "web coverage service"],
        "default_title": "Web Coverage Service",
        "capabilities_param": "request=GetCapabilities&service=WCS",
        "mime_type": "application/xml",
        "multilingual_title": {
            "en": "Web Coverage Service (WCS)",
            "es": "Servicio Web de Coberturas (WCS)"
        },
        "multilingual_description": {
            "en": "OGC Web Coverage Service (WCS) provides access to coverage data in forms that are useful for client-side rendering, as input into scientific models, and for other clients. For more specific information, please check the endpoint description.",
            "es": "El servicio Web Coverage Service (WCS) definido por el Open Geospatial Consortium (OGC) permite el acceso e intercambio de datos geoespaciales como coberturas que representan valores o propiedades de ubicaciones geográficas. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "CSW": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/csw",
        "protocol_indicators": ["csw", "discovery", "ogc:csw", "catalog service"],
        "url_indicators": ["csw", "service=csw"],
        "name_indicators": ["csw", "catalog service"],
        "default_title": "Catalog Service for the Web",
        "capabilities_param": "request=GetCapabilities&service=CSW",
        "mime_type": "application/xml",
        "multilingual_title": {
            "en": "Catalog Service for the Web (CSW)",
            "es": "Servicio de Catálogo para la Web (CSW)"
        },
        "multilingual_description": {
            "en": "OGC Catalog Service for the Web (CSW) is a standard for exposing a catalog of geospatial records on the web. For more specific information, please check the endpoint description.",
            "es": "El servicio Catalog Service for the Web (CSW) definido por el Open Geospatial Consortium (OGC) permite la publicación y búsqueda de metadatos geoespaciales. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "WMTS": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/wmts",
        "protocol_indicators": ["wmts", "ogc:wmts", "web map tile service"],
        "url_indicators": ["wmts", "service=wmts"],
        "name_indicators": ["wmts", "web map tile"],
        "default_title": "Web Map Tile Service",
        "capabilities_param": "request=GetCapabilities&service=WMTS",
        "mime_type": "application/vnd.ogc.wmts+xml",
        "multilingual_title": {
            "en": "Web Map Tile Service (WMTS)",
            "es": "Servicio Web de Teselas de Mapas (WMTS)"
        },
        "multilingual_description": {
            "en": "OGC Web Map Tile Service (WMTS) provides access to cartographic map tiles of spatially referenced data. For more specific information, please check the endpoint description.",
            "es": "El servicio Web Map Tile Service (WMTS) definido por el Open Geospatial Consortium (OGC) proporciona acceso a teselas de mapas de datos con referencia espacial. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "SOS": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/sos",
        "protocol_indicators": ["sos", "sensor", "ogc:sos", "sensor observation service"],
        "url_indicators": ["sos", "service=sos"],
        "name_indicators": ["sos", "sensor observation"],
        "default_title": "Sensor Observation Service",
        "capabilities_param": "request=GetCapabilities&service=SOS",
        "mime_type": "application/xml",
        "multilingual_title": {
            "en": "Sensor Observation Service (SOS)",
            "es": "Servicio de Observación de Sensores (SOS)"
        },
        "multilingual_description": {
            "en": "OGC Sensor Observation Service (SOS) provides a standardized interface for managing and retrieving metadata and observations from heterogeneous sensor systems. For more specific information, please check the endpoint description.",
            "es": "El servicio Sensor Observation Service (SOS) definido por el Open Geospatial Consortium (OGC) proporciona una interfaz estandarizada para gestionar y recuperar metadatos y observaciones de sistemas de sensores heterogéneos. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "OGC-API": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/api",
        "protocol_indicators": ["api", "rest"],
        "url_indicators": ["api", "/api/"],
        "name_indicators": ["api"],
        "default_title": "OGC API",
        "capabilities_param": "",
        "mime_type": "application/json",
        "multilingual_title": {
            "en": "OGC API",
            "es": "API OGC"
        },
        "multilingual_description": {
            "en": "OGC API provides access to geospatial data through a modern REST API. For more specific information, please check the endpoint description.",
            "es": "La API OGC proporciona acceso a datos geoespaciales a través de una API REST moderna. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "REST": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/rest",
        "protocol_indicators": ["rest"],
        "url_indicators": ["rest", "/rest/"],
        "name_indicators": ["rest"],
        "default_title": "REST Service",
        "capabilities_param": "",
        "mime_type": "application/json",
        "multilingual_title": {
            "en": "REST Service",
            "es": "Servicio REST"
        },
        "multilingual_description": {
            "en": "REST service provides access to data through RESTful API endpoints. For more specific information, please check the endpoint description.",
            "es": "El servicio REST proporciona acceso a datos a través de puntos finales de API RESTful. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "ATOM": {
        "uri": "http://www.opengis.net/def/serviceType/ogc/atom",
        "protocol_indicators": ["atom"],
        "url_indicators": ["atom", "service=atom"],
        "name_indicators": ["atom"],
        "default_title": "ATOM Feed Service",
        "capabilities_param": "",
        "mime_type": "application/atom+xml",
        "multilingual_title": {
            "en": "ATOM Feed Service",
            "es": "Servicio de Fuente ATOM"
        },
        "multilingual_description": {
            "en": "ATOM Feed Service provides access to data through standardized ATOM feeds. For more specific information, please check the endpoint description.",
            "es": "El servicio de Fuente ATOM proporciona acceso a datos a través de fuentes ATOM estandarizadas. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "OPENSEARCH": {
        "uri": "",  # No hay URI estándar definida
        "protocol_indicators": ["opensearch"],
        "url_indicators": ["opensearchdescription"],
        "name_indicators": ["opensearch"],
        "default_title": "OpenSearch Service",
        "capabilities_param": "",
        "mime_type": "application/opensearchdescription+xml",
        "multilingual_title": {
            "en": "OpenSearch Service",
            "es": "Servicio OpenSearch"
        },
        "multilingual_description": {
            "en": "OpenSearch Service provides a search interface that can be used to search for data resources. For more specific information, please check the endpoint description.",
            "es": "El servicio OpenSearch proporciona una interfaz de búsqueda que puede utilizarse para buscar recursos de datos. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "ESRI_REST": {
        "uri": "",  # No hay URI estándar OGC para ESRI
        "protocol_indicators": ["esri", "arcgis"],
        "url_indicators": ["arcgis/rest", "mapserver", "imageserver", "featureserver", "f=json"],
        "name_indicators": ["arcgis", "esri"],
        "default_title": "ESRI REST Service",
        "capabilities_param": "f=json",
        "mime_type": "application/json",
        "multilingual_title": {
            "en": "ESRI REST Service",
            "es": "Servicio REST de ESRI"
        },
        "multilingual_description": {
            "en": "ESRI REST Service provides access to geospatial data through ESRI's REST API. For more specific information, please check the endpoint description.",
            "es": "El servicio REST de ESRI proporciona acceso a datos geoespaciales a través de la API REST de ESRI. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    # Servicios adicionales que pueden ser útiles
    "DOWNLOAD": {
        "uri": "",  
        "protocol_indicators": ["download", "download service"],
        "url_indicators": ["/download", "download=", "file="],
        "name_indicators": ["download", "descarga"],
        "default_title": "Download Service",
        "mime_type": "application/octet-stream",
        "multilingual_title": {
            "en": "Download Service",
            "es": "Servicio de Descarga"
        },
        "multilingual_description": {
            "en": "Download Service provides direct access to data file download. For more specific information, please check the endpoint description.",
            "es": "El Servicio de Descarga proporciona acceso directo a la descarga de archivos de datos. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "INSPIRE": {
        "uri": "",  
        "protocol_indicators": ["inspire"],
        "url_indicators": ["inspire"],
        "name_indicators": ["inspire"],
        "default_title": "INSPIRE Service",
        "mime_type": "application/xml",
        "multilingual_title": {
            "en": "INSPIRE Service",
            "es": "Servicio INSPIRE"
        },
        "multilingual_description": {
            "en": "INSPIRE Service provides access to data according to INSPIRE Directive specifications. For more specific information, please check the endpoint description.",
            "es": "El Servicio INSPIRE proporciona acceso a datos según las especificaciones de la Directiva INSPIRE. Más información específica del servicio en la descripción del punto final (dcat:endpointDescription)."
        }
    },
    "DEFAULT": {
        "uri": "",
        "protocol_indicators": [],
        "url_indicators": [],
        "name_indicators": [],
        "default_title": "Data Service",
        "mime_type": "application/octet-stream",
        "multilingual_title": {
            "en": "Data Service",
            "es": "Servicio de datos"
        },
        "multilingual_description": {
            "en": "Service providing access to the data resource. For more specific information, please check the endpoint description (dcat:endpointDescription).",
            "es": "Servicio que proporciona acceso al recurso de datos. Para información más específica, consulte la descripción del punto final (dcat:endpointDescription)."
        }
    }
}

OGC_SERVICES_LIST = ['WMS', 'WFS', 'WCS', 'CSW', 'SOS', 'WMTS']