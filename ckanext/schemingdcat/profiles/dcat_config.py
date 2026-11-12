"""
This file contains default values for the SpanishDCATProfile and EuropeanDCATAPProfile profiles.
Default values are used to fill in missing metadata in resources.
Default values can be overridden in resource-specific metadata.

    metadata_field_names: dict
        A dictionary containing the metadata field names for each profile.

    es_dcat_default_values: dict
        A dictionary containing the default values for the SpanishDCATProfile.

    eu_dcat_ap_default_values: dict
        A dictionary containing the default values for the EuropeanDCATAPProfile.
        
    es_dcat_ap_default_values: dict
        A dictionary containing the default values for the EsDCATAP2Profile.
        
    default_translated_fields: dict
        A dictionary containing the default translated fields for the ckanext-schemingdcat extension.
"""
from pathlib import Path

from ckanext.dcat.profiles.base import (
    RDF,
    RDFS,
    SKOS,
    XSD,
    DCT,
    ADMS,
    GEOJSON_IMT,
    ORG,
    Namespace,
    Literal   
)

EUROVOC = Namespace("http://publications.europa.eu/ontology/euvoc#")
ELI = Namespace("http://data.europa.eu/eli/ontology#")
DC = Namespace("http://purl.org/dc/elements/1.1/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCATAP = Namespace("http://data.europa.eu/r5r/")
GEODCATAP = Namespace("http://data.europa.eu/930/")
DCATUS = Namespace("http://resources.data.gov/ontology/dcat-us#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace("http://schema.org/")
TIME = Namespace("http://www.w3.org/2006/time#")  # correct with trailing #
LOCN = Namespace("http://www.w3.org/ns/locn#")
GSP = Namespace("http://www.opengis.net/ont/geosparql#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SPDX = Namespace("http://spdx.org/rdf/terms#")
CNT = Namespace("http://www.w3.org/2011/content#")
ODRS = Namespace("http://schema.theodi.org/odrs#")

CODELISTS_DIR = Path(__file__).resolve().parent.parent / "codelists"
EU_VOCABS_DIR = CODELISTS_DIR / "dcat"
INSPIRE_CODELISTS_DIR = CODELISTS_DIR / "inspire"
IANA_MEDIA_TYPES_BASE_URI = 'http://www.iana.org/assignments/media-types'
EU_VOCAB_AUTHORITY_TABLES_BASE_URI = 'http://publications.europa.eu/resource/authority'

# DCAT default elements by profile
metadata_field_names = {
    'eu_dcat_ap': {
        'theme': 'theme_eu',
    },
    'es_dcat': {
        'theme': 'theme_es',
    }
    ,
    'es_dcat_ap': {
        'theme': 'theme_es',
    },
}

# EU Vocabs
EU_VOCABULARIES = [
    {
        "title": "Access Right",
        "name": "access-right",
        "url": "http://publications.europa.eu/resource/authority/access-right",
        "description": "Access rights, CSV fields: URI, Label"
    },
    {
        "title": "File Types",
        "name": "file-types",
        "url": "http://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http://publications.europa.eu/resource/distribution/file-type/rdf/skos_ap_act/filetypes-skos-ap-act.rdf&fileName=filetypes-skos-ap-act.rdf",
        "description": "File Types, CSV fields: URI, Label, Non-Proprietary format (true/false)"
    },
    {
        "title": "IANA Media Types",
        "name": "media-types",
        "url": "http://www.iana.org/assignments/media-types/media-types.xml",
        "description": "File Types, CSV fields: URI, Label"
    },
    {
        "title": "Licenses",
        "name": "licenses",
        "url": "http://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http://publications.europa.eu/resource/distribution/licence/rdf/skos_ap_act/licences-skos-ap-act.rdf&fileName=licences-skos-ap-act.rdf",
        "description": "Licenses, CSV fields: URI, Label, EUVocab URI"
    },
    {
        "title": "Distribution status",
        "name": "status",
        "url": "http://publications.europa.eu/resource/authority/distribution-status",
        "description": "Distribution status, CSV fields: URI, EUVocab URI"
    },
    # Add more URLs and their respective configurations here as needed
]

# Spanish Profile: Mandatory elements by NTI-RISP.
es_dcat_default_values = {
    'availability': 'http://publications.europa.eu/resource/authority/planned-availability/AVAILABLE',
    'access_rights': 'http://publications.europa.eu/resource/authority/access-right/PUBLIC',
    'conformance_es': 'http://www.boe.es/eli/es/res/2013/02/19/(4)',
    'description': 'Recurso sin descripción.',
    'description_es': 'Recurso sin descripción.',
    'format_es': 'HTML',
    'language_code': 'es',
    'language': 'http://publications.europa.eu/resource/authority/language/SPA',
    'catalog_language_codes': ['es'],
    'catalog_languages': ['http://publications.europa.eu/resource/authority/language/ENG', 'http://publications.europa.eu/resource/authority/language/SPA'],
    'license': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'license_url': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'mimetype_es': 'text/html',
    'notes': 'Conjunto de datos sin descripción.',
    'notes_es': 'Conjunto de datos sin descripción.',
    'notes_en': 'Dataset without description.',
    'publisher_identifier': 'http://datos.gob.es/recurso/sector-publico/org/Organismo/EA0007777',
    'publisher_type': 'http://purl.org/adms/publishertype/NonProfitOrganisation',
    'status': 'http://publications.europa.eu/resource/authority/distribution-status/COMPLETED',
    'theme_es': 'http://datos.gob.es/kos/sector-publico/sector/sector-publico',
    'theme_eu': 'http://publications.europa.eu/resource/authority/data-theme/GOVE',
    'theme_taxonomy': 'http://datos.gob.es/kos/sector-publico/sector',
    'rights_uri_label': 'Derechos relativos a la reutilización del Catálogo de Datos Abiertos',
    'rights_attribution_text': 'Atribución de la autoría al organismo.',
    'spatial_uri': 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España',
}


# Spanish Profile: Mandatory elements by DCAT-AP-ES (Based on DCAT-AP 2.1.1).
es_dcat_ap_default_values = {
    'availability': 'http://publications.europa.eu/resource/authority/planned-availability/AVAILABLE',
    'access_rights': 'http://publications.europa.eu/resource/authority/access-right/PUBLIC',
    'conformance_es': 'http://www.boe.es/eli/es/res/2013/02/19/(4)',
    'description': 'Recurso sin descripción.',
    'description_es': 'Recurso sin descripción.',
    'format_es': 'HTML',
    'language_code': 'es',
    'language': 'http://publications.europa.eu/resource/authority/language/SPA',
    'catalog_language_codes': ['en', 'es'],
    'catalog_languages': ['http://publications.europa.eu/resource/authority/language/ENG', 'http://publications.europa.eu/resource/authority/language/SPA'],
    'license': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'license_url': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'mimetype_es': 'text/html',
    'notes': 'Conjunto de datos sin descripción.',
    'notes_es': 'Conjunto de datos sin descripción.',
    'notes_en': 'Dataset without description.',
    'publisher_identifier': 'http://datos.gob.es/recurso/sector-publico/org/Organismo/EA0007777',
    'publisher_type': 'http://purl.org/adms/publishertype/NonProfitOrganisation',
    'status': 'http://publications.europa.eu/resource/authority/distribution-status/COMPLETED',
    'theme_es': 'http://datos.gob.es/kos/sector-publico/sector/sector-publico',
    'theme_eu': 'http://publications.europa.eu/resource/authority/data-theme/GOVE',
    'theme_taxonomy': 'http://datos.gob.es/kos/sector-publico/sector',
    'rights_uri_label': 'Derechos relativos a la reutilización del Catálogo de Datos Abiertos',
    'rights_attribution_text': 'Atribución de la autoría al organismo.',
    'spatial_uri': 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España',
}

# EU DCAT-AP: Mandatory catalog elements by DCAT-AP.
eu_dcat_ap_default_values = {
    'availability': 'http://publications.europa.eu/resource/authority/planned-availability/AVAILABLE',
    'access_rights': 'http://publications.europa.eu/resource/authority/access-right/PUBLIC',
    'access_rights_restricted': 'http://publications.europa.eu/resource/authority/access-right/RESTRICTED',
    'author_role': 'http://id.loc.gov/vocabulary/relators/aut',
    'conformance': 'http://data.europa.eu/r5r/',
    'contact_role': 'http://id.loc.gov/vocabulary/relators/mdc',
    'checksum_algorithm': 'http://spdx.org/rdf/terms#checksumAlgorithm_sha1',
    'description': 'Resource without description.',
    'description_en': 'Resource without description.',
    'description_es': 'Recurso sin descripción.',
    'language': 'http://publications.europa.eu/resource/authority/language/ENG',
    'catalog_languages': ['http://publications.europa.eu/resource/authority/language/ENG', 'http://publications.europa.eu/resource/authority/language/SPA'],
    'license': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'license_url': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'maintainer_role': 'http://id.loc.gov/vocabulary/relators/rpy',
    'notes': 'Dataset without description.',
    'notes_es': 'Conjunto de datos sin descripción.',
    'notes_en': 'Dataset without description.',
    'publisher_identifier': 'http://datos.gob.es/recurso/sector-publico/org/Organismo/EA0007777',
    'publisher_type': 'http://purl.org/adms/publishertype/NonProfitOrganisation',
    'publisher_role': 'http://id.loc.gov/vocabulary/relators/pbl',
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

# EU GeoDCAT-AP Profile: Mandatory catalog elements by GeoDCAT-AP.
eu_geodcat_ap_default_values = {
    'availability': 'http://publications.europa.eu/resource/authority/planned-availability/AVAILABLE',
    'access_rights': 'http://publications.europa.eu/resource/authority/access-right/PUBLIC',
    'author_role': 'http://inspire.ec.europa.eu/metadata-codelist/ResponsiblePartyRole/author',
    'conformance': 'http://data.europa.eu/930/',
    'contact_role': 'http://inspire.ec.europa.eu/metadata-codelist/ResponsiblePartyRole/pointOfContact',
    'description': 'Resource without description.',
    'description_en': 'Resource without description.',
    'description_es': 'Recurso sin descripción.',
    'language': 'http://publications.europa.eu/resource/authority/language/ENG',
    'catalog_languages': ['http://publications.europa.eu/resource/authority/language/ENG', 'http://publications.europa.eu/resource/authority/language/SPA'],
    'license': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'license_url': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
    'maintainer_role': 'http://inspire.ec.europa.eu/metadata-codelist/ResponsiblePartyRole/custodian',
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

# Default field_names to translated fields mapping (ckanext.schemingdcat:schemas)
default_translated_fields = {
    'title': 
        {
            'field_name': 'title_translated',
            'rdf_predicate': DCT.title,
            'fallbacks': ['title'],
            '_type': Literal,
            '_class': None,
            'required_lang': None
        },
    'notes': 
        {
            'field_name': 'notes_translated',
            'rdf_predicate': DCT.description,
            'fallbacks': ['notes'],
            '_type': Literal,
            '_class': None,
            'required_lang': None
        },
    'description': 
        {
            'field_name': 'description_translated',
            'rdf_predicate': DCT.description,
            'fallbacks': ['description'],
            '_type': Literal,
            '_class': None,
            'required_lang': None
        },
    'provenance': 
        {
            'field_name': 'provenance',
            'rdf_predicate': RDFS.label,
            'fallbacks': None,
            '_type': Literal,
            '_class': DCT.ProvenanceStatement,
            'required_lang': None
        },
    'version_notes': 
        {
            'field_name': 'version_notes',
            'rdf_predicate': ADMS.versionNotes,
            'fallbacks': None,
            '_type': Literal,
            '_class': None,
            'required_lang': None
        },
}

default_translated_fields_es_dcat = {
    'title': 
        {
            'field_name': 'title_translated',
            'rdf_predicate': DCT.title,
            'fallbacks': ['title'],
            '_type': Literal,
            '_class': None,
            'required_lang': 'es',
        },
    'notes': 
        {
            'field_name': 'notes_translated',
            'rdf_predicate': DCT.description,
            'fallbacks': ['notes'],
            '_type': Literal,
            '_class': None,
            'required_lang': 'es',
        },
    'description': 
        {
            'field_name': 'description_translated',
            'rdf_predicate': DCT.description,
            'fallbacks': ['description'],
            '_type': Literal,
            '_class': None,
            'required_lang': 'es',
        }
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# Licenses fallbacks
dcat_ap_default_licenses = {
    'http://www.opendefinition.org/licenses/cc-by': {
        'license_url': 'http://www.opendefinition.org/licenses/cc-by',
        'license_id': 'cc-by',
        'fallback_license_url': 'http://publications.europa.eu/resource/authority/licence/CC_BY',
        'fallback_license_id': 'CC_BY'
    },
     'http://creativecommons.org/licenses/by/4.0/': {
        'license_url': 'http://creativecommons.org/licenses/by/4.0/',
        'license_id': 'cc-by',
        'fallback_license_url': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
        'fallback_license_id': 'CC_BY_4_0'
    },
     'https://creativecommons.org/licenses/by/4.0/': {
        'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'license_id': 'CC-BY-4.0',
        'fallback_license_url': 'http://publications.europa.eu/resource/authority/licence/CC_BY_4_0',
        'fallback_license_id': 'CC_BY_4_0'
    }   
}

# Mapping RDF entity types to properties that must have language tags
DCAT_ENTITY_PROPERTIES_CONFIG = {
    "Catalog": {
        "type": DCAT.Catalog,
        "properties": [
            DCT.title,
            DCT.description
        ]
    },
    "Dataset": {
        "type": DCAT.Dataset,
        "properties": [
            DCT.title,
            DCT.description,
            DCAT.keyword,
            ADMS.versionNotes,
            DCT.subject
        ]
    },
    "Distribution": {
        "type": DCAT.Distribution,
        "properties": [
            DCT.title,
            DCT.description
        ]
    },
    "DataService": {
        "type": DCAT.DataService,
        "properties": [
            DCT.title,
            DCT.description,
            DCAT.keyword
        ]
    },
    "Agent": {
        "type": FOAF.Agent,
        "properties": [
            FOAF.name
        ]
    },
    "VCard": {
        "type": VCARD.Kind,
        "properties": [
            VCARD.fn,
            VCARD.organization_name
        ]
    },
    "ProvenanceStatement": {
        "type": DCT.ProvenanceStatement,
        "properties": [
            DCT.description
        ]
    },
    "Relationship": {
        "type": DCAT.Relationship,
        "properties": []
    },
    "PeriodOfTime": {
        "type": DCT.PeriodOfTime,
        "properties": []
    },
    "Location": {
        "type": DCT.Location,
        "properties": []
    },
    "Checksum": {
        "type": SPDX.Checksum,
        "properties": []
    }
    # Add more entities as needed
}

# Specific profiles with their property sets
DCAT_PROFILE_CONFIGS = {
    "es_dcat": {
        "entities": [
            "Catalog",
            "Dataset",
            "Distribution",
            "Agent", 
            "VCard", 
            "ProvenanceStatement",
        ],
        "default_language": "es"
    },
    "es_dcat_ap_2": {
        "entities": [
            "Catalog",
            "Dataset", 
            "Distribution", 
            "DataService", 
            "Agent", 
            "VCard", 
            "ProvenanceStatement",
            "Relationship",
            "PeriodOfTime",
            "Location",
            "Checksum"
        ],
        "default_language": "es"
    },
    "eu_dcat_ap_2": {
        "entities": [
            "Catalog",
            "Dataset", 
            "Distribution", 
            "DataService", 
            "Agent", 
            "VCard", 
            "ProvenanceStatement",
            "Relationship",
            "PeriodOfTime",
            "Location",
            "Checksum"
        ],
        "default_language": "en"
    },
    "eu_dcat_ap_3": {
        "entities": [
            "Catalog",
            "Dataset", 
            "Distribution", 
            "DataService", 
            "Agent", 
            "VCard", 
            "ProvenanceStatement",
            "Relationship",
            "PeriodOfTime",
            "Location",
            "Checksum"
        ],
        "default_language": "en"
    },
    "eu_geodcat_ap_2": {
        "entities": [
            "Catalog",
            "Dataset", 
            "Distribution", 
            "DataService", 
            "Agent", 
            "VCard", 
            "ProvenanceStatement",
            "Relationship",
            "PeriodOfTime",
            "Location",
            "Checksum"
        ],
        "default_language": "en"
    },
    "eu_geodcat_ap_3": {
        "entities": [
            "Catalog",
            "Dataset", 
            "Distribution", 
            "DataService", 
            "Agent", 
            "VCard", 
            "ProvenanceStatement",
            "Relationship",
            "PeriodOfTime",
            "Location",
            "Checksum"
        ],
        "default_language": "en"
    }
}
