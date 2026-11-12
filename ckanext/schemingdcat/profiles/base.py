import re
from decimal import Decimal, DecimalException
import logging
import json
from urllib.parse import quote
from typing import Tuple, List, Union, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dateutil.parser import parse as parse_date

from rdflib import term, URIRef, Literal, Graph, BNode

from ckantoolkit import config, get_action, aslist
from ckan.lib.helpers import is_url

from ckanext.dcat.validators import is_year, is_year_month, is_date
from ckanext.dcat.utils import catalog_uri, resource_uri
from ckanext.dcat.profiles.base import RDFProfile, URIRefOrLiteral, CleanedURIRef, DEFAULT_SPATIAL_FORMATS, GEOJSON_IMT, InvalidGeoJSONException, wkt
from ckanext.schemingdcat.config import (
    translate_validator_tags,
    ISO19115_LANGUAGE,
    BASE_VOCABS,
    FREQUENCY_MAPPING
)

from ckanext.schemingdcat.config import (
    DCAT_SERVICE_TYPES
)
from ckanext.schemingdcat.helpers import get_langs, schemingdcat_get_catalog_publisher_info
from ckanext.schemingdcat.codelists import load_inspire_csv_codelists
from ckanext.schemingdcat.profiles.dcat_config import (
    # Vocabs
    RDF,
    RDFS,
    SKOS,
    ELI,
    EUROVOC,
    DCAT,
    DC,
    DCT,
    DCAT,
    DCATAP,
    GEODCATAP,
    DCATUS,
    ADMS,
    VCARD,
    FOAF,
    SCHEMA,
    TIME,
    LOCN,
    GSP,
    OWL,
    SPDX,
    CNT,
    ORG,
    ODRS,
    XSD,
    # Default values
    eu_dcat_ap_default_values,
    )

# INSPIRE Codelists
codelists = load_inspire_csv_codelists()
MD_INSPIRE_REGISTER = codelists["MD_INSPIRE_REGISTER"]
MD_FORMAT = codelists["MD_FORMAT"]
MD_ES_THEMES = codelists["MD_ES_THEMES"]
MD_EU_THEMES = codelists["MD_EU_THEMES"]
MD_EU_LANGUAGES = codelists["MD_EU_LANGUAGES"]
MD_ES_FORMATS = codelists["MD_ES_FORMATS"]
DCAT_AP_STATUS = codelists["DCAT_AP_STATUS"]
DCAT_AP_ACCESS_RIGHTS = codelists["DCAT_AP_ACCESS_RIGHTS"]

namespaces = {
    "cnt": CNT,
    "dc": DC,
    "dct": DCT,
    "dcat": DCAT,
    "dcatap": DCATAP,
    "geodcatap": GEODCATAP,
    "eli": ELI,
    "dcatus": DCATUS,
    "adms": ADMS,
    "vcard": VCARD,
    "foaf": FOAF,
    "schema": SCHEMA,
    "time": TIME,
    "skos": SKOS,
    "locn": LOCN,
    "gsp": GSP,
    "owl": OWL,
    "org": ORG,
    "spdx": SPDX,
    "odrs": ODRS,
}

default_lang = config.get("ckan.locale_default", "en")
catalog_base_ref =  config.get('ckan.site_url', None)

log = logging.getLogger(__name__)


class SchemingDCATRDFProfile(RDFProfile):
    """
    A custom ckanext-dcat Base RDF Profile for the ckanext-schemingdcat extension. https://github.com/ckan/ckanext-dcat/blob/master/ckanext/dcat/profiles/base.py

    Notes:
        **RDFProfile**: Base class with helper methods for implementing RDF parsing profiles

        This class should not be used directly, but rather extended to create
        custom profiles

    """
    
    # ckanext-schemingdcat profiles: INSPIRE/DCAT Themes.
    def _themes(self, dataset_ref):
        """
        Returns all DCAT themes on a particular dataset
        """
        # Precompile regular expressions for faster matching
        data_es_pattern = re.compile(r"https?://datos\.gob\.es/")
        inspire_eu_pattern = re.compile(r"https?://inspire\.ec\.europa\.eu/theme")
        themes = set()

        for theme in self._object_value_list(dataset_ref, DCAT.theme):
            theme = theme.replace("https://", "http://")

            if data_es_pattern.match(theme):
                themes.add(theme)
                if theme:
                    theme_es_dcat_ap = self._search_value_codelist(MD_ES_THEMES, theme, "id","dcat_ap") or None
                    themes.add(theme_es_dcat_ap)
                
            elif inspire_eu_pattern.match(theme):
                themes.add(theme)
                if theme:
                    theme_eu_dcat_ap = self._search_value_codelist(MD_EU_THEMES, theme, "id","dcat_ap") or None
                    themes.add(theme_eu_dcat_ap)

        return themes
    
    
    # Improve publisher/contact details
    def _publisher(self, subject, predicate):
        """
        Returns a dict with details about a dct:publisher entity, a foaf:Agent

        Both subject and predicate must be rdflib URIRef or BNode objects

        Examples:

        <dct:publisher>
            <foaf:Organization rdf:about="http://orgs.vocab.org/some-org">
                <foaf:name>Publishing Organization for dataset 1</foaf:name>
                <foaf:mbox>contact@some.org</foaf:mbox>
                <foaf:homepage>http://some.org</foaf:homepage>
                <dct:type rdf:resource="http://purl.org/adms/publishertype/NonProfitOrganisation"/>
                <dct:identifier>EA349s92</dct:identifier>
            </foaf:Organization>
        </dct:publisher>

        {
            'uri': 'http://orgs.vocab.org/some-org',
            'name': 'Publishing Organization for dataset 1',
            'email': 'contact@some.org',
            'url': 'http://some.org',
            'type': 'http://purl.org/adms/publishertype/NonProfitOrganisation',
            'identifier': 'EA349s92'
        }

        <dct:publisher rdf:resource="http://publications.europa.eu/resource/authority/corporate-body/EURCOU" />

        {
            'uri': 'http://publications.europa.eu/resource/authority/corporate-body/EURCOU'
        }

        Returns keys for uri, name, email, url and type with the values set to
        an empty string if they could not be found
        """

        publisher = {}

        for agent in self.g.objects(subject, predicate):

            publisher["uri"] = str(agent) if isinstance(agent, term.URIRef) else ""

            publisher["name"] = self._object_value(agent, FOAF.name)

            publisher["email"] = self._object_value(agent, FOAF.mbox)

            publisher["url"] = self._object_value(agent, FOAF.homepage)

            publisher["type"] = self._object_value(agent, DCT.type)

            publisher["identifier"] = self._object_value(agent, DCT.identifier)

        return publisher

    def _contact_details(self, subject, predicate):
        """
        Returns a list of dicts with details about vcard expressions

        Both subject and predicate must be rdflib URIRef or BNode objects

        Examples:

        <dcat:contactPoint>
            <vcard:Organization rdf:nodeID="Nc320885686e84382a0a2ea602ebde399">
                <vcard:fn>Contact Point for dataset 1</vcard:fn>
                <vcard:hasEmail <mailto:contact@some.org>
                <vcard:hasURL>http://some.org<vcard:hasURL>
                <vcard:role>pointOfContact<vcard:role>
            </vcard:Organization>
        </dcat:contactPoint>

        [
            {
            'uri': 'http://orgs.vocab.org/some-org',
            'name': 'Contact Point for dataset 1',
            'email': 'contact@some.org',
            'url': 'http://some.org',
            'role': 'pointOfContact',
            }
        ]

        Returns keys for uri, name, email and url with the values set to
        an empty string if they could not be found
        """

        contacts = []

        for agent in self.g.objects(subject, predicate):

            contact = {}                
            contact["uri"] = str(agent) if isinstance(agent, URIRef) else ""

            contact["name"] = self._get_vcard_property_value(
                agent, VCARD.hasFN, VCARD.fn
            )

            contact["email"] = self._without_mailto(
                self._get_vcard_property_value(agent, VCARD.hasEmail)
            )

            contact["identifier"] = self._get_vcard_property_value(agent, VCARD.hasUID)

            contact["url"] = self._get_vcard_property_value(
                agent, VCARD.hasURL
            )

            contact["role"] = self._get_vcard_property_value(
                agent, VCARD.role
            )

            contacts.append(contact)

        return contacts
        
    # ckanext-schemingdcat: Multilang management
    ## Since  ckanext-dcat v2.1.0 unnecessary due to its multilingual support ##
    
    #TODO: Delete deprecated method
    def _get_localized_dataset_value(self, multilang_dict, default=None):
        """Returns a localized dataset multilang_dict.

        Args:
            multilang_dict: A string or dictionary representing the multilang_dict to localize.
            default: A default value to return if the multilang_dict cannot be localized.

        Returns:
            A dictionary representing the localized multilang_dict, or the default value if the multilang_dict cannot be localized.

        Raises:
            None.
        """
        if isinstance(multilang_dict, dict):
            return multilang_dict

        if isinstance(multilang_dict, str):
            try:
                multilang_dict = json.loads(multilang_dict)
            except ValueError:
                return default
    
    # ckanext-schemingdcat: Catalog class enhancements
    def _get_catalog_field(self, field_name, default_values_dict=eu_dcat_ap_default_values, fallback=None, return_none=False, order="desc"):
        """
        Returns the value of a field from the most recently modified dataset.

        Args:
            field_name (str): The name of the field to retrieve from datasets list
            default_values_dict (dict): A dictionary of default values to use if the field is not found. Defaults to eu_dcat_ap_default_values.
            fallback (str): The name of the fallback field to retrieve if `field_name` is not found. Defaults to None.
            return_none (bool): Whether to return None if the field is not found. Defaults to False.
            order (str): The order in which to sort the results. Defaults to "desc".

        Returns:
            The value of the field, or the default value if it could not be found and `return_none` is False.

        Notes:
            This function caches the result of the CKAN API call to improve performance. The cache is stored in the `_catalog_search_result` attribute of the object. If the attribute exists, the function will return the value of the requested field from the cached result instead of making a new API call. If the attribute does not exist, the function will make a new API call and store the result in the attribute for future use.
        """
        if not hasattr(self, "_catalog_search_result"):
            context = {
                "ignore_auth": True
            }
            self._catalog_search_result = get_action("package_search")(context, {
                "sort": f"metadata_modified {order}",
                "rows": 1,
            })
        try:
            if self._catalog_search_result and self._catalog_search_result.get("results"):
                return self._catalog_search_result["results"][0][field_name]
        except KeyError:
            pass
        if fallback:
            try:
                if self._catalog_search_result and self._catalog_search_result.get("results"):
                    return self._catalog_search_result["results"][0][fallback]
            except KeyError:
                pass
        if return_none:
            return None
        return default_values_dict[field_name]

    def _get_catalog_dcat_theme(self):
        """
        Returns the value of the `theme_es` field from the most recently created dataset,
        or the value of the `theme_eu` field if `theme_es` is not present.

        Returns None if neither `theme_es` nor `theme_eu` are present in the dataset.

        Returns:
            A string with the value of the `theme_es` or `theme_eu` field, or None if not found.
        """
        context = {
            "ignore_auth": True
        }
        result = get_action("package_search")(context, {
            "sort": "metadata_created desc",
            "rows": 1,
        })
        if result and result.get("results"):
            if "theme_es" in result["results"][0]:
                return result["results"][0]["theme_es"][0]
            elif "theme_eu" in result["results"][0]:
                return result["results"][0]["theme_eu"][0]
        return None

    def _get_catalog_language(self, default_values=eu_dcat_ap_default_values):
        """
        Returns the value of the `language` field from the most recently modified dataset.

        Args:
            default_values (dict): A dictionary of default values to use if the `publisher_uri` field cannot be found.

        Returns:
            A string with the value of the `language` field, or None if it could not be found.
        """
        context = {
            "ignore_auth": True
        }
        result = get_action("package_search")(context, {
            "sort": "metadata_modified desc",
            "rows": 1,
        })
        try:
            if result and result.get("results"):
                return result["results"][0]["language"]
            
        except KeyError:
            return default_values["language"]

    def _get_catalog_languages_paginated(
        self, 
        default_values=eu_dcat_ap_default_values,
        batch_size=100, 
        default_values_property='catalog_languages',
        output_format='uri'  # Options: 'iso2', 'iso3', 'uri'
    ):
        """
        Returns a set of language codes in the specified format.
    
        Args:
            default_values (dict): Dictionary of default values
            batch_size (int): Number of records to process per batch
            default_values_property (str): Property name for default languages
            output_format (str): Desired output format:
                - 'iso2': 2-letter codes (e.g., 'es', 'en')
                - 'iso3': 3-letter codes (e.g., 'spa', 'eng')
                - 'uri': Language URIs (e.g., 'http://publications.europa.eu/resource/authority/language/ENG')
    
        Returns:
            set: Set of language codes in requested format
    
        Example:
            >>> # Get 2-letter codes
            >>> languages = _get_catalog_languages_paginated(output_format='iso2')
            >>> print(languages)
            {'es', 'en'}
            
            >>> # Get URI format
            >>> languages = _get_catalog_languages_paginated(output_format='uri')
            >>> print(languages)
            {'http://publications.europa.eu/resource/authority/language/ENG'}
        """
        try:
            context = {"ignore_auth": True}
            languages = set()
            start = 0
    
            while True:
                result = get_action("package_search")(context, {
                    "start": start,
                    "rows": batch_size,
                    "fl": "language"
                })
    
                if not result or not result.get("results"):
                    break
    
                for dataset in result["results"]:
                    lang = dataset.get("language")
                    
                    lang_codes = set()
                    if isinstance(lang, list):
                        lang_codes.update(lang)
                    elif isinstance(lang, str):
                        lang_codes.add(lang)
                    elif isinstance(lang, dict):
                        lang_codes.update(lang.keys())
    
                    # Process each code
                    for code in lang_codes:
                        formatted_code = self._format_language_code(code, output_format)
                        if formatted_code:
                            languages.add(formatted_code)
    
                start += batch_size
                if start >= result["count"]:
                    break
    
            # Add default if needed
            if not languages and default_values.get(default_values_property):
                default_lang = self._format_language_code(
                    default_values[default_values_property], 
                    output_format
                )
                if default_lang:
                    languages.add(default_lang)    
            return languages
    
        except Exception as e:
            return set()
    
    def _format_language_code(self, code, output_format='iso2'):
        """
        Formats language code to desired output format.
        """
        if not code:
            return None

        # For URI input, just return it if output_format is also 'uri'
        if is_url(code) and output_format == 'uri' and 'publications.europa.eu' in code:
            return code

        # First get the raw language code
        raw_code = None
        
        # Handle URIs
        if is_url(code):
            if 'publications.europa.eu' in code:
                raw_code = code.split('/')[-1].upper()
        else:
            raw_code = code.upper()

        if not raw_code:
            return None

        # Convert to desired format
        if output_format == 'iso2':
            if len(raw_code) == 2:
                result = raw_code.lower()
            else:
                result = ISO19115_LANGUAGE.get(raw_code.lower())
            return result
            
        elif output_format == 'iso3':
            if len(raw_code) == 3:
                result = raw_code.lower()
            else:
                # Convert from ISO2 to ISO3
                for iso3, iso2 in ISO19115_LANGUAGE.items():
                    if iso2.upper() == raw_code.upper():
                        result = iso3.lower()
                        break
            return result
                
        elif output_format == 'uri':
            iso3_code = None
            if len(raw_code) == 3:
                iso3_code = raw_code
            else:
                # Convert from ISO2 to ISO3
                for iso3, iso2 in ISO19115_LANGUAGE.items():
                    if iso2.upper() == raw_code.upper():
                        iso3_code = iso3.upper()
                        break
            
            if iso3_code:
                result = f"{BASE_VOCABS['eu_publications']}language/{iso3_code}"
                return result

        return None

    def _normalize_language_code(self, code):
        """
        Normalizes language codes from various formats to ISO 639-1.
        
        Args:
            code (str): Language code or URI
            
        Returns:
            str: Normalized ISO 639-1 code or None if invalid
        """
        if not code:
            return None

        # Handle URIs
        if is_url(code):
            # Extract code from URI
            code = code.split('/')[-1].lower()

        # Convert to 3-letter code if needed
        code = code.lower()
        if len(code) == 2:
            # Find 3-letter code for 2-letter input
            for three_letter, two_letter in ISO19115_LANGUAGE.items():
                if two_letter == code:
                    return code
        
        # Map 3-letter code to 2-letter
        return ISO19115_LANGUAGE.get(code)

    # ckanext-schemingdcat: Codelist management
    def _search_values_codelist_add_to_graph(self, metadata_codelist, labels, dataset_dict, dataset_ref, 
                                           dataset_tag_base, g, dcat_property, lang=None, raw=True):
        """
        Adds values from a metadata codelist to a graph based on provided labels.
        raw=True by default, adds labels directly without processing or validation (DCAT-AP)

        Args:
            metadata_codelist (list): A list of dictionaries containing metadata codelist entries.
            labels (list or str): A list of labels or a single label to search for in the codelist.
            dataset_dict (dict): The dataset dictionary containing dataset metadata.
            dataset_ref (URIRef): The reference URI of the dataset.
            dataset_tag_base (str): The base URL for dataset tags.
            g (Graph): The RDF graph to which the values will be added.
            dcat_property (URIRef): The DCAT property to be used for adding values to the graph.
            lang (str, optional): The language of the labels. Defaults to None.
            raw (bool, optional): If True, adds labels without processing. Defaults to False.

        """
        # Ensure labels is a list
        if not isinstance(labels, list):
            labels = [labels]
        
        if raw:
            for label in labels:
                g.add((dataset_ref, dcat_property, URIRefOrLiteral(label)))
            return
            
        # Only needed for non-raw processing
        inspire_dict = {row["label"].lower(): row.get("id", row.get("value")) 
                       for row in metadata_codelist}
        
        # Get 'topic' from dataset_dict only for non-raw
        topics = self._get_dataset_value(dataset_dict, "topic")
        if not topics:
            topics = []
        elif not isinstance(topics, list):
            topics = [topics]
        
        for label in labels:
            if label not in topics:
                if label.lower() in inspire_dict:
                    tag_val = inspire_dict[label.lower()]
                else:
                    tag_val = f"{dataset_tag_base}/dataset/?tags={label}"
                    
                if lang:
                    g.add((dataset_ref, dcat_property, Literal(tag_val, lang=lang)))
                else:
                    g.add((dataset_ref, dcat_property, URIRefOrLiteral(tag_val)))

    def dict_to_list(self, value):
        """Converts a dictionary to a list of its values.

        Args:
            value: The value to convert.

        Returns:
            If the value is a dictionary, returns a list of its values. Otherwise, returns the value unchanged.
        """
        if isinstance(value, dict):
            value = list(value.values())
        return value

    def _search_value_codelist(self, metadata_codelist, label, input_field_name, output_field_name, return_value=True):
        """Searches for a value in a metadata codelist.

        Args:
            metadata_codelist (list): A list of dictionaries containing the metadata codelist.
            label (str): The label to search for in the codelist.
            input_field_name (str): The name of the input field in the codelist.
            output_field_name (str): The name of the output field in the codelist.
            return_value (bool): Whether to return the label value if not found (True) or None if not found (False). Default is True.

        Returns:
            str or None: The value found in the codelist, or None if not found and return_value is False.
        """
        
        if not label:
            return None
        
        inspire_dict = {
            row[input_field_name].lower(): row[output_field_name] 
            for row in metadata_codelist
        }
        tag_val = inspire_dict.get(label.lower())
        
        if not return_value:
            return tag_val
        
        return label if tag_val is None else tag_val

    def _add_date_triple(self, subject, predicate, value, _type=Literal):
        """
        Adds a new triple with a date object
    
        If the value is one of xsd:gYear, xsd:gYearMonth or xsd:date. If not
        the value will be parsed using dateutil, and if the date obtained is correct,
        added to the graph as an xsd:dateTime value.
    
        If there are parsing errors, the literal string value is added.
        """
        if not value:
            return
    
        # Handle special case for problematic 1900-01-01 with strange timezone
        if isinstance(value, str) and value.startswith('1900-01-01'):
            # Special case - convert to simple date format without time component
            simple_date = value.split('T')[0]  # Just take the date part
            self.g.add((subject, predicate, _type(simple_date, datatype=XSD.date)))
            return
    
        if is_year(value):
            self.g.add((subject, predicate, _type(value, datatype=XSD.gYear)))
            return
        elif is_year_month(value):
            self.g.add((subject, predicate, _type(value, datatype=XSD.gYearMonth)))
            return
        elif is_date(value):
            self.g.add((subject, predicate, _type(value, datatype=XSD.date)))
            return
    
        # For any other format, try to parse and format correctly
        try:
            default_datetime = datetime(1, 1, 1, 0, 0, 0)
            _date = parse_date(value, default=default_datetime)
            
            # Special handling for dates before 1900
            if _date.year < 1900 or (_date.year == 1900 and _date.month == 1 and _date.day == 1):
                # Format as just the date part (YYYY-MM-DD) without time component
                date_str = _date.strftime("%Y-%m-%d")
                self.g.add((subject, predicate, _type(date_str, datatype=XSD.date)))
                return
                
            # For modern dates (>=1900), ensure proper timezone formatting
            if _date.tzinfo is not None:
                # Convert to UTC
                try:
                    _date = _date.astimezone(timezone.utc)
                    # Format with Z for UTC timezone (ISO 8601)
                    date_str = _date.strftime("%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, OverflowError):
                    # If timezone conversion fails, use simple date format
                    date_str = _date.strftime("%Y-%m-%d")
                    self.g.add((subject, predicate, _type(date_str, datatype=XSD.date)))
                    return
            else:
                # Use ISO format without timezone for naive datetimes
                date_str = _date.strftime("%Y-%m-%dT%H:%M:%S")
                
            self.g.add((subject, predicate, _type(date_str, datatype=XSD.dateTime)))
                
        except (ValueError, TypeError, OverflowError) as e:
            # If parsing fails, try to extract just the date part for dates before 1900
            try:
                if isinstance(value, str) and ('1900-' in value or value < '1900-'):
                    date_part = value.split('T')[0]
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_part):
                        self.g.add((subject, predicate, _type(date_part, datatype=XSD.date)))
                        return
            except Exception:
                pass
                
            # If all else fails, log and add as literal string
            log.warning(f"Failed to parse date '{value}': {str(e)}")
            self.g.add((subject, predicate, _type(value)))
    
    ## https://github.com/mjanez/ckanext-dcat/issues/4
    def _add_spatial_value_to_graph(self, spatial_ref, predicate, value):
        """
        Adds spatial triples to the graph. Assumes that value is a GeoJSON string
        or object.
        """
        spatial_formats = aslist(
            config.get(
                "ckanext.dcat.output_spatial_format", DEFAULT_SPATIAL_FORMATS
            )
        )
    
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                return

        # Check if the predicate already exists for the spatial_ref. Location props have only one (0..1).
        if (spatial_ref, predicate, None) in self.g:
            return
    
        if "wkt" in spatial_formats:
            # WKT, because GeoDCAT-AP says so
            try:
                log.debug(type(value))
                self.g.add(
                    (
                        spatial_ref,
                        predicate,
                        Literal(
                            wkt.dumps(value, decimals=4),
                            datatype=GSP.wktLiteral,
                        ),
                    )
                )
            except (TypeError, ValueError, InvalidGeoJSONException):
                pass
    
        if "geojson" in spatial_formats:
            # GeoJSON
            self.g.add((spatial_ref, predicate, Literal(json.dumps(value), datatype=GEOJSON_IMT)))
            
    # ckanext-dcat enhancements
    def _add_multilingual_literal(self, g, subject, predicate, value, required_lang=None):
        """
        Add multilingual literal to graph with required language support
        Args:
            g: RDF graph
            subject: RDF subject
            predicate: RDF predicate
            value: String or dict with language codes as keys
            required_lang: Required language code (optional)
        """
        if not value:
            return

        if isinstance(value, dict):
            # Check required language first
            if required_lang and required_lang in value:
                g.add((subject, predicate, Literal(value[required_lang], lang=required_lang)))
            
            # Add default language if different from required
            if self._default_lang in value and (not required_lang or required_lang != self._default_lang):
                g.add((subject, predicate, Literal(value[self._default_lang], lang=self._default_lang)))
            
            # Add other languages
            for lang, text in value.items():
                if lang not in [required_lang, self._default_lang]:
                    g.add((subject, predicate, Literal(text, lang=lang)))
        else:
            # Single string value - use required language if specified, otherwise default
            use_lang = required_lang if required_lang else self._default_lang
            g.add((subject, predicate, Literal(value, lang=use_lang)))
        
    def _multilingual_fields(self, entity="dataset"):
        """
        Retrieve multilingual fields from the dataset schema.
    
        This function checks the dataset schema for fields that have validators
        indicating they are multilingual. It looks for validators that start with
        any of the tags specified in `translate_validator_tags`.
    
        Args:
            entity (str, optional): The entity type to check for multilingual fields.
                                    Defaults to "dataset".
    
        Returns:
            list: A list of fields that are considered multilingual.
        """    
        if not self._dataset_schema:
            return []
    
        out = []
        for field in self._dataset_schema[f"{entity}_fields"]:
            if field.get("validators") and any(
                v for v in field["validators"].split() if any(tag for tag in translate_validator_tags if v.startswith(tag))
            ):
                out.append(field["field_name"])
        return out
    
    def _publisher_fallback_details(self, dataset_dict):
        """
        Use contact details for publisher if not already set.
    
        This method checks if the publisher details (name, email, url, identifier, uri)
        are present in the dataset_dict or dataset_dict["extras"]. If they are not present,
        it uses the corresponding contact details to fill in the publisher details.
    
        Args:
            dataset_dict (dict): The dataset dictionary containing metadata fields.
    
        Returns:
            None
        """
        contact_keys = ["name", "email", "url", "identifier", "uri"]
        for key in contact_keys:
            contact_key = f"contact_{key}"
            publisher_key = f"publisher_{key}"
            if not any(extra['key'] == publisher_key for extra in dataset_dict["extras"]) and publisher_key not in dataset_dict:
                if contact_key in dataset_dict:
                    dataset_dict["extras"].append(
                        {
                            "key": publisher_key,
                            "value": dataset_dict[contact_key]
                        }
                    )
                    dataset_dict[publisher_key] = dataset_dict[contact_key]

    def _add_valid_url_to_graph(self, graph, subject, predicate, url, fallback_url=None):
        """
        Add a valid URL to the graph. Only adds if URL is valid or fallback exists.
        
        Args:
            graph (rdflib.Graph): The RDF graph
            subject (rdflib.term.URIRef): The subject of the triple
            predicate (rdflib.term.URIRef): The predicate of the triple
            url (str): The URL to validate and add
            fallback_url (str): The fallback URL to use if the URL is not valid
        """
        
        def normalize_url(url_str):
            if not url_str:
                return None
    
            url_str = url_str.strip()
    
            # Fix missing slash after protocol if needed
            if re.match(r'^https?:/?[^/]', url_str):
                url_str = re.sub(r'^(https?:/?)', r'\1/', url_str)
    
            # Add protocol if missing but looks like a URL
            if not url_str.startswith(('http://', 'https://')) and re.match(r'^[^/]+\.[^/]+/', url_str):
                url_str = 'https://' + url_str
    
            # Remove excessive slashes after the protocol
            url_str = re.sub(r'(?<!:)/{2,}', '/', url_str)
            
            return url_str
        
        if isinstance(url, str):
            normal_url = normalize_url(url)
            encoded_url = quote(normal_url, safe=':/?&=')
            if is_url(encoded_url):
                graph.add((subject, predicate, URIRef(encoded_url)))
                return True
                
        if fallback_url and isinstance(fallback_url, str):
            normal_url = normalize_url(fallback_url)
            encoded_fallback = quote(normal_url, safe=':/?&=')
            if is_url(encoded_fallback):
                graph.add((subject, predicate, URIRef(encoded_fallback)))
                return True
                
        return False

    def _is_direct_download_url(self, url):
        """
        Check if the URL is a direct download link.
    
        Args:
            url (str): The URL to check.
    
        Returns:
            bool: True if the URL is a direct download link, False otherwise.
        """
        # Check if the URL ends with '/download' or with an extension like '.ext'
        if url.endswith('/download'):
            return True
        
        # Check if the URL ends with a common file extension
        if '.' in url.split('/')[-1]:
            return True
        
        # Additional checks for common download patterns
        common_download_patterns = ['/files/', '/downloads/', '/get/', '/dl/']
        for pattern in common_download_patterns:
            if pattern in url:
                return True
        
        return False
    
    def _ensure_datetime(self, value_or_dict: Union[dict, str, datetime], date_field: str = None, as_string: bool = True) -> Optional[Union[str, datetime]]:
        """
        Ensure datetime with timezone and convert to ISO string.
        This method checks if the given date field in the resource dictionary is a valid datetime.
        If the date field is a string, it attempts to parse it into a datetime object. If the datetime
        object is naive (lacking timezone information), it assigns the UTC timezone. Finally, it stores
        the datetime as an ISO 8601 string with timezone information if `as_string` is True, otherwise
        it stores the datetime object.
    
        Args:
            value_or_dict (str or dict): The dictionary containing the resource data.
            date_field (str): The key in the dictionary for the date field to be ensured.
            as_string (bool): Whether to store the datetime as an ISO string. Defaults to True.
    
        Returns:
            str or datetime or None: Formatted date string, datetime object or None if invalid
        """
        # Get value from dict if provided
        date_value = value_or_dict.get(date_field) if isinstance(value_or_dict, dict) else value_or_dict
        
        if not date_value:
            return None
            
        # Special case for 1900-01-01 with problematic timezone
        if isinstance(date_value, str) and date_value.startswith('1900-01-01'):
            # If we're dealing with a string that's a 1900-01-01 date
            # Just return the date part without time component
            if as_string:
                return '1900-01-01'
            return datetime(1900, 1, 1)
            
        # Convert to datetime if string
        if not isinstance(date_value, datetime):
            try:
                # For simple date formats (YYYY-MM-DD), ensure we don't add time component
                if isinstance(date_value, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', date_value):
                    # Parse as date
                    date_obj = datetime.strptime(date_value, '%Y-%m-%d')
                    if date_obj.year <= 1900:
                        # For historical dates, return just the date string
                        return date_value if as_string else date_obj
                
                # Normal parsing for more complex date formats
                date_value = parse_date(date_value)
            except (ValueError, TypeError):
                log.warning(f"Could not parse date {date_value}")
                # Last resort - if it's a string with a date format, try to extract just the date part
                if isinstance(date_value, str):
                    match = re.search(r'(\d{4}-\d{2}-\d{2})', date_value)
                    if match:
                        date_part = match.group(1)
                        if as_string:
                            return date_part
                        try:
                            return datetime.strptime(date_part, '%Y-%m-%d')
                        except (ValueError, TypeError):
                            pass
                return None
        
        # Special handling for dates in 1900 or earlier
        if date_value.year <= 1900:
            if as_string:
                # Return just the date part for historical dates
                return date_value.strftime('%Y-%m-%d')
            return date_value
                
        # Add timezone if naive
        if date_value.tzinfo is None:
            tz_name = config.get('ckan.display_timezone', 'UTC')
            try:
                tz = ZoneInfo(tz_name)
            except ZoneInfoNotFoundError:
                log.warning(f"Invalid timezone {tz_name}, using UTC")
                tz = timezone.utc
            date_value = date_value.replace(tzinfo=tz)
        
        if as_string:
            # For modern dates with timezone, use proper ISO format with Z for UTC
            if date_value.tzinfo == timezone.utc:
                return date_value.strftime('%Y-%m-%dT%H:%M:%SZ')
            # Otherwise use ISO format with proper timezone offset
            return date_value.isoformat()
        
        return date_value
    
    def _clean_spatial_resolution(self, value: Union[str, int, float], as_type: str = 'decimal') -> Union[str, Decimal, float]:
        """Clean spatial resolution string to extract numeric value."""
        if not value:
            return value
            
        # Fast path for numeric input
        if isinstance(value, (int, float)):
            return abs(Decimal(value)) if as_type == 'decimal' else abs(float(value))
        
        # Process string input    
        value = str(value)
        
        # Handle ratio format (1:50000)
        if ':' in value:
            value = value.split(':')[1].strip()
        
        # Remove dots (Spanish thousands) and convert
        value = value.replace('.', '')
        
        try:
            if as_type == 'decimal':
                return abs(Decimal(value))
            return abs(float(value))
        except (ValueError, DecimalException):
            return value

    def _clean_string(self, value: str, upper: bool = False) -> str:
        """
        Clean string value, optionally convert to uppercase.

        Args:
            value (str): The string value to be cleaned.
            upper (bool): If True, convert the cleaned string to uppercase. Defaults to False.

        Returns:
            Optional[str]: The cleaned string, optionally converted to uppercase, or None if the input is not a string.
       """
        if not isinstance(value, str) or not value:
            return None
        cleaned = value.strip()
        return cleaned.upper() if upper else cleaned

    def _is_valid_access_service(self, access_service_dict: dict) -> bool:
        """Validate required properties for DataService.
        Args:
            access_service_dict (dict): Dictionary containing the access service properties.
        Returns:
            bool: True if all required properties are present, False otherwise.
        Required properties:
            - title (DCT.title)
            - endpoint_url (DCAT.endpointURL)
            - serves_dataset (DCAT.servesDataset)
        """
        required = [
            ('title', DCT.title),
            ('endpoint_url', DCAT.endpointURL),
            ('serves_dataset', DCAT.servesDataset)
        ]
        
        return all(
            access_service_dict.get(field) 
            for field, _ in required
        )

    def _normalize_format(self, fmt: str) -> str:
        """
        Normalize format string to uppercase, handling None values
        """
        if not fmt:
            return ''
        return fmt.strip().upper()

    def _clean_publisher(self, dataset_ref):
        """Remove all publisher triples before adding catalog publisher"""
        # Get all existing publishers
        for publisher in self.g.objects(dataset_ref, DCT.publisher):
            # Remove publisher triple and all related triples
            self.g.remove((dataset_ref, DCT.publisher, publisher))
            self.g.remove((publisher, None, None))

    def _add_catalog_publisher_to_service(self, access_service_node):
        """Add catalog publisher to data service if not present"""
        try:
            # Check if node exists
            if not access_service_node:
                return
                
            # Check if publisher already exists
            if self.g.value(access_service_node, DCT.publisher):
                return
                
            # Get publisher info safely
            catalog_publisher_info = schemingdcat_get_catalog_publisher_info() or {}
            publisher_uri = catalog_publisher_info.get("identifier")
            
            # Only add if we have a valid URI
            if publisher_uri and isinstance(publisher_uri, str):
                self.g.add((
                    access_service_node,
                    DCT.publisher,
                    CleanedURIRef(publisher_uri)
                ))
        except Exception as e:
            log.warning(f"Error adding catalog publisher to service: {str(e)}")

    def _is_valid_temporal_resolution(self, value: str) -> bool:
        """
        Validate ISO-8601 duration format.
        
        Format: P[nY][nM][nD][T[nH][nM][nS]]
        Examples:
            PT1H          - 1 hour
            P1Y           - 1 year
            P3M           - 3 months
            P1DT12H      - 1 day, 12 hours
            PT30M        - 30 minutes
        """
        if not value or not isinstance(value, str):
            return False
            
        # Simplified pattern that allows single units
        pattern = r'^P(?:\d+Y)?(?:\d+M)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+S)?)?$|^PT(?:\d+H)?(?:\d+M)?(?:\d+S)?$'
        
        return bool(re.match(pattern, value))


    def _get_graph_required_languages(
            self, 
            graph: Graph, 
            properties: List[URIRef] = None,
            required_languages: List[str] = None
        ) -> List[str]:
        """
        Check which languages are present for all specified properties across the graph.
        Returns the list of languages that are consistently present.
        
        Args:
            graph (Graph): RDF Graph to analyze
            properties (List[URIRef]): Properties to check (e.g., [DCT.title, DCT.description])
            required_languages (List[str]): List of language codes to consider.
                                        If None, retrieves all languages in the graph.
        
        Returns:
            List[str]: List of language codes that are present for all specified properties
        
        Example:
            >>> # Get languages that exist for all titles and descriptions
            >>> languages = self._get_graph_required_languages(
            ...     graph, 
            ...     [DCT.title, DCT.description],
            ...     ['es', 'en', 'ca']
            ... )
            >>> # If 'es' is present for all but 'en' is missing for some,
            >>> # the result would be ['es']
        """
        if not properties:
            return []
        
        # Get all languages present in the graph if required_languages not specified
        if not required_languages:
            all_langs = set()
            for _, _, o in graph:
                if isinstance(o, Literal) and o.language:
                    all_langs.add(o.language)
            required_languages = list(all_langs)
        
        # If there are no languages to check, return empty list
        if not required_languages:
            return []
        
        # Track which languages are missing for each property+subject combination
        missing_languages = {lang: False for lang in required_languages}
        
        # For each subject and property combination, check if all required languages exist
        subject_property_pairs = set((s, p) for s, p, _ in graph if p in properties)
        
        # Skip check if there are no subject-property pairs to analyze
        if not subject_property_pairs:
            return []
        
        for s, p in subject_property_pairs:
            # Get the languages present for this subject+property
            existing_langs = set(
                o.language 
                for _, _, o in graph.triples((s, p, None)) 
                if isinstance(o, Literal) and o.language
            )
            
            # Mark languages that are missing
            for lang in required_languages:
                if lang not in existing_langs:
                    missing_languages[lang] = True
        
        # Return only languages that are present for all properties (not marked as missing)
        consistent_languages = [lang for lang, is_missing in missing_languages.items() if not is_missing]
        
        return consistent_languages

    def _graph_remove_non_target_language_literals(
            self, 
            graph: Graph, 
            properties: List[URIRef] = None,
            langs: List[str] = None
        ) -> None:
        """
        Remove literals with languages not in the target list, keeping only specified languages.
        
        Args:
            graph (Graph): RDF Graph to process
            properties (List[URIRef]): Properties to check. If None, checks all properties.
            langs (List[str]): List of language codes to keep. If None, uses [self._default_lang].
        
        Example:
            >>> # Keep only Spanish and English literals for title and description
            >>> self._graph_remove_non_target_language_literals(
            ...     graph, 
            ...     [DCT.title, DCT.description],
            ...     ['es', 'en']
            ... )
        """
        if not langs:
            langs = [self._default_lang]
        
        # Ensure we have properties to check
        if not properties:
            return
        
        # Find all triples with language tags not in the target list
        triples_to_remove = []
        
        for s, p, o in graph:
            # Check if this is a property we're interested in
            if p not in properties:
                continue
                
            # Check if this is a literal with a language tag
            if isinstance(o, Literal) and o.language and o.language not in langs:
                triples_to_remove.append((s, p, o))
        
        # Remove the identified triples
        for triple in triples_to_remove:
            graph.remove(triple)
        
        # Check each subject-predicate pair to ensure at least one value remains
        for s, p in set((s, p) for s, p, _ in graph if p in properties):
            # Get remaining literals for this subject-predicate pair
            remaining = list(graph.objects(s, p))
            
            # If no literals remain, restore the highest priority language if available
            if not remaining:
                log.warning(f"All literals removed for {s} {p}, nothing to restore.")
                continue

    def _graph_remove_empty_language_literals(self, graph: Graph) -> None:
        """
        Removes empty language literals using generator expression.
        
        Args:
            graph (Graph): RDF Graph.
        """
        empty_triples = (
            triple for triple in graph 
            if isinstance(triple[2], Literal) 
            and triple[2].language 
            and not triple[2].value.strip()
        )
        
        list(map(graph.remove, empty_triples))

    def _add_provenance_statement_to_graph(self, data_dict, key, subject, predicate, _class=None):
        """
        Adds a provenance statement property to the graph.
        If it is a Literal value, it is added as a node (with a class if provided)
        with a DCT.description property, eg:

            <your-dataset> dct:provenance [
            rdf:type dct:ProvenanceStatement ;
            dct:description "Texto del dataset_dict['provenance']"@en
            ] .

        """
        value = self._get_dict_value(data_dict, key)
        if not value:
            return

        if isinstance(value, dict):
            _objects = []
            for lang_code, text_val in value.items():
                if text_val and text_val.strip():
                    _objects.append(Literal(text_val.strip(), lang=lang_code))
        else:
            # Para cadenas simples, se anexa sólo si no está vacío
            if value and value.strip():
                # Por defecto sin idioma, o podrías usar el CFG default_lang
                _objects = [Literal(value.strip(), lang="en")]
            else:
                _objects = []
    
        # Si no hay contenido válido, no creamos nodo
        if not _objects:
            return
    
        statement_ref = BNode()
        self.g.add((subject, predicate, statement_ref))
        if _class:
            self.g.add((statement_ref, RDF.type, _class))
    
        # Añade cada descripción
        for _literal in _objects:
            self.g.add((statement_ref, DCT.description, _literal))

    def _ensure_language_triple(self, subject_ref, default_lang_uri):
        """
        Ensures a DCT.language triple exists for the subject_ref, adding default if missing.

        Checks if DCT.language exists for the given subject reference. If it doesn't exist,
        adds the default language URI. If it exists but doesn't match the default, adds 
        the default language as an additional value.

        Args:
            subject_ref (rdflib.term.URIRef): The subject reference (dataset or distribution)
            default_lang_uri (str): The default language URI to add if missing

        Returns:
            None: Modifies the graph in place
        """
        existing_langs = list(self.g.objects(subject_ref, DCT.language))
        default_uri = URIRef(default_lang_uri)
        if not existing_langs:
            # No language -> add default language
            self.g.add((subject_ref, DCT.language, default_uri))
        elif default_uri not in existing_langs:
            # there are languages, but not the one we want -> add it
            self.g.add((subject_ref, DCT.language, default_uri))
            
    def _process_dct_identifier(self, identifier, mandatory=False):
        """
        Process dct:identifier to ensure it's a valid literal.
        
        Args:
            identifier (str): The identifier to process
            mandatory (bool): If True, always return last part of URI as string
                            If False, return None if no valid identifier found
            
        Returns:
            str or None: Processed identifier or None if invalid and not mandatory
        """
        try:
            if not identifier:
                return None if not mandatory else identifier
                
            # If it's a URI, extract the last part
            if identifier.startswith(('http://', 'https://')):
                # Remove trailing slashes and get last part
                parts = identifier.rstrip('/').split('/')
                if len(parts) > 1:
                    return str(parts[-1])  # Force string type
                return identifier if mandatory else None
                
            # If it's not a URI, return as-is
            return str(identifier)  # Force string type
            
        except Exception as e:
            log.warning(f"Error processing publisher identifier: {str(e)}")
            return identifier if mandatory else None
        
    def _create_uri_ref(self, identifier, role="contact", base_ref=None):
        """
        Create a reference URI for entities like contacts or other vcard roles.
        
        This function creates a URI reference using a provided identifier and role.
        If the identifier is valid, it constructs a URI in the format:
        {base_ref}/kos/role/{processed_identifier}/{role}
        
        Args:
            identifier (str): The identifier to use in the URI. Can be a full URI 
                or a simple string.
            role (str, optional): The role to append to the URI path. Used to 
                categorize different types of entities. Defaults to "contact".
            base_ref (str, optional): The base URI to use. If not provided, uses
                cached value or falls back to ckan.site_url config.
                
        Returns:
            URIRef or BNode: A cleaned URI reference if successful, or a blank node
                if the creation fails.
                
        Notes:
            - Uses caching for base_ref to improve performance
            - Handles various edge cases like empty/invalid identifiers
            - Always returns either a valid URIRef or a BNode
            - Processes identifiers to extract meaningful parts from URIs
            
        Examples:
            >>> _create_uri_ref("123", "publisher")
            URIRef('http://example.com/kos/role/123/publisher')
            
            >>> _create_uri_ref("http://data.ex.com/org/123", "contact")
            URIRef('http://example.com/kos/role/123/contact')
            
            >>> _create_uri_ref(None)
            BNode('Nxxx')
        """
        try:
            if not base_ref:
                base_ref = catalog_base_ref or config.get('ckan.site_url')
            
            if identifier:
                # Process the identifier with mandatory=True to always get a string
                processed_id = self._process_dct_identifier(identifier, mandatory=True)
                if processed_id:
                    # Clean and normalize components
                    base = base_ref.rstrip('/')
                    role = role.strip().lower() if role else 'contact'
                    processed_id = processed_id.strip()
                    
                    # Construct URI
                    uri = f"{base}/kos/role/{processed_id}/{role}"
                    return CleanedURIRef(uri)
                
            return BNode()
            
        except Exception as e:
            return BNode()
        
    def _add_frequency_value(self, dataset_ref, frequency_uri):
        """
        Adds frequency metadata to dataset using TIME ontology with multilingual labels.
        
        This method generates RDF triples that describe the dataset's update frequency
        using the TIME ontology. It maps frequency URIs from the EU Publications Office
        to appropriate TIME duration descriptions with labels in multiple languages.
        
        Args:
            dataset_ref (URIRef): The URI reference for the dataset.
            frequency_uri (str): The frequency URI from the EU Publications Office
                authority list (e.g., "http://publications.europa.eu/resource/authority/frequency/ANNUAL").
        
        Returns:
            None: Updates the RDF graph in-place.
        
        Note:
            The FREQUENCY_MAPPING dictionary must contain entries with the format:
            (time_property, time_value, language_labels_dict, show_value_in_label)
            
            Example mapping:
            "http://publications.europa.eu/resource/authority/frequency/ANNUAL": 
                ("years", "1", {"es": "año", "en": "year"}, True)
        """
        # Early return if no mapping exists
        mapped_value = FREQUENCY_MAPPING.get(frequency_uri)
        if not mapped_value:
            log.debug(f"No frequency mapping found for {frequency_uri}")
            return
        
        # Extract values based on mapping structure
        if len(mapped_value) == 4:
            time_prop, time_val, time_labels, show_value = mapped_value
        else:
            # Legacy format support
            time_prop, time_val, time_labels = mapped_value
            show_value = time_val != "0"
        
        # Create stable, predictable URIs for the frequency components
        frequency_node = BNode()
        duration_node = BNode()
        
        # Add the frequency structure to the graph
        g = self.g
        g.add((dataset_ref, DCT.accrualPeriodicity, frequency_node))
        g.add((frequency_node, RDF.type, DCT.Frequency))
        g.add((frequency_node, RDF.value, duration_node))
        
        # Add the duration description with proper datatype
        g.add((duration_node, RDF.type, TIME.DurationDescription))
        g.add((duration_node, getattr(TIME, time_prop), Literal(time_val, datatype=XSD.decimal)))
        
        # Process multilingual labels for both frequency_node and duration_node
        if isinstance(time_labels, dict):
            # Add labels to duration_node
            self._add_multilingual_frequency_labels(
                duration_node, time_val, time_labels, show_value
            )

        elif time_labels:  # Fallback for string labels (legacy support)
            label = f"{time_val} {time_labels}" if show_value and time_val != "0" else time_labels
            g.add((duration_node, RDFS.label, Literal(label, lang="es")))
            g.add((frequency_node, RDFS.label, Literal(label, lang="es")))

    def _add_multilingual_frequency_labels(self, node, value, labels_dict, show_value):
        """
        Helper method to add multilingual labels to a frequency node.
        
        Args:
            node (URIRef): The node to add labels to
            value (str): The time value
            labels_dict (dict): Dictionary of language codes to label texts
            show_value (bool): Whether to show the value in the label
        """
        g = self.g
        for lang, label in labels_dict.items():
            if not label:
                continue
                
            if show_value and value != "0":
                # Format: "1 year", "30 minutes", etc.
                g.add((node, RDFS.label, Literal(f"{value} {label}", lang=lang)))
            else:
                # Format: "year", "never", "irregular", etc.
                g.add((node, RDFS.label, Literal(label, lang=lang)))

    def _add_uri_from_value(self, subject, predicate, value):
        """
        Helper to add URIRef triples from values that might be strings or lists
        
        Args:
            subject: The subject of the triple
            predicate: The predicate of the triple
            value: The value to convert to URIRef(s) - can be string, list or JSON string
            
        Returns:
            bool: True if at least one triple was added, False otherwise
        """
        if not value:
            return False
            
        # Handle JSON string representations of lists
        if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
            try:
                # Try to parse as JSON array
                values = json.loads(value.replace("'", '"'))
                # Add each item as a separate triple
                for item in values:
                    if item and isinstance(item, str):
                        self.g.add((subject, predicate, URIRef(item.strip())))
                return True
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, continue with original value
                pass
                
        # Handle Python list objects
        if isinstance(value, list):
            for item in value:
                if item and isinstance(item, str):
                    self.g.add((subject, predicate, URIRef(item.strip())))
            return True
            
        # Handle scalar value
        if value and isinstance(value, str):
            self.g.add((subject, predicate, URIRef(value)))
            return True
            
        return False

    def _detect_service_type(self, access_service_dict):
        """
        Detecta el tipo de servicio basado en la URL del punto final y otros datos.
        
        Args:
            access_service_dict: Diccionario con información del servicio de acceso
            
        Returns:
            str: Tipo de servicio (e.g. 'WMS', 'WFS', etc.) o 'DEFAULT' si no se detecta
        """
        # Obtener endpoint URLs
        endpoint_urls = access_service_dict.get('endpoint_url', [])
        if isinstance(endpoint_urls, str):
            endpoint_urls = [endpoint_urls]
        
        # Revisar la URI del servicio - podría contener información del tipo
        service_uri = access_service_dict.get('uri', '').lower()
        
        # Obtener título del servicio si existe
        service_title = access_service_dict.get('title', '').lower()
        
        # Comprobar cada tipo de servicio para encontrar coincidencias
        for service_type, service_info in DCAT_SERVICE_TYPES.items():
            if service_type == "DEFAULT":
                continue  # Saltamos el DEFAULT para procesarlo al final
                
            # Comprobar indicadores en URLs
            for url in endpoint_urls:
                url_lower = url.lower()
                for indicator in service_info.get('url_indicators', []):
                    if indicator.lower() in url_lower:
                        return service_type
            
            # Comprobar indicadores en el título
            for indicator in service_info.get('name_indicators', []):
                if indicator.lower() in service_title:
                    return service_type
                    
            # Comprobar indicadores en la URI
            for indicator in service_info.get('protocol_indicators', []):
                if indicator.lower() in service_uri:
                    return service_type
        
        # Si llegamos aquí, no pudimos determinar el tipo de servicio
        return "DEFAULT"
    
    def _add_service_multilingual_properties(self, access_service_node, access_service_dict, catalog_base_uri):
        """
        Adds multilingual properties to an access service node.
        
        Args: 
            access_service_node: The RDF node of the access service.
            access_service_dict: Dictionary containing the service data.
            catalog_base_uri: Catalog base URI for comparisons.
        """
        # Verificar si el nodo de servicio está basado en la URI del catálogo.
        access_service_uri = str(access_service_node)
        
        # Solo se deben modificar las propiedades si no se trata de una derivación de la URI del catálogo.
        if not access_service_uri.startswith(catalog_base_uri):
            service_type = self._detect_service_type(access_service_dict)
            default_values = DCAT_SERVICE_TYPES.get(service_type, DCAT_SERVICE_TYPES["DEFAULT"])
            
            properties_to_process = [
                (DCT.title, "multilingual_title", "default_title"),
                (DCT.description, "multilingual_description", "default_description")
            ]
            
            for predicate, multilingual_key, default_key in properties_to_process:
                for existing_value in list(self.g.objects(access_service_node, predicate)):
                    self.g.remove((access_service_node, predicate, existing_value))

                multilingual_values = default_values.get(multilingual_key, {})

                for lang_code, value in multilingual_values.items():
                    self.g.add((access_service_node, predicate, Literal(value, lang=lang_code)))

                if not multilingual_values and default_values.get(default_key):
                    self.g.add((access_service_node, predicate, Literal(default_values.get(default_key))))
        else:
            items = [
                ("title", DCT.title, None, Literal),
                ("description", DCT.description, None, Literal),
            ]
            
            self._add_triples_from_dict(access_service_dict, access_service_node, items)