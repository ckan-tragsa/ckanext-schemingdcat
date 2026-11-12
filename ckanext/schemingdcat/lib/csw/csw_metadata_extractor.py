import logging
import re
from datetime import datetime
from dateutil.parser import parse
from owslib.iso import MD_Metadata
from lxml import etree
from .csw_inspire import _generate_metadata_inspire
from shapely.geometry import Polygon
from shapely.geometry import mapping
import json

from ckantoolkit import config
from ckanext.schemingdcat.helpers import schemingdcat_get_ckan_site_url, schemingdcat_extract_base_url
from ckanext.schemingdcat.config import (
    ISO19115_LANGUAGE,
    BASE_VOCABS,
    PROTOCOL_MAPPING,
    ISO19115_HIERARCHY,
    ISO19115_INSPIRE_DEFAULT_VALUES,
    ISO19115_REPRESENTATION_TYPE,
    ISO19115_CHARACTER_ENCODING,
    ISO19115_TOPIC_CATEGORY,
    FORMAT_STANDARDIZATION,
    PROTOCOL_MAPPING,
    SERVICE_INDICATORS,
    DCAT_SERVICE_TYPES,
    OGC_SERVICES_LIST,
)

log = logging.getLogger(__name__)
valid_languages = list(ISO19115_LANGUAGE.keys())

# csw_metadata_extractor.py
class CSWMetadataExtractor:
    """
    Extracts metadata from CSW records using INSPIRE extractors as base
    and adding additional non-INSPIRE fields.
    """

    def __init__(self, debug=False):
        """
        Initialize CSWMetadataExtractor
        
        Args:
            debug (bool): Enable debug mode if True, disabled by default
        """
        self._debug = debug
        self._default_lang_code_2 = config.get("ckan.locale_default", "en")
        self._reverse_language_mapping = {v: k for k, v in ISO19115_LANGUAGE.items()}
        self._default_lang_code_3 = self._reverse_language_mapping.get(self._default_lang_code_2, 'eng')
        
        if self._debug:
            log.debug(f"CSWMetadataExtractor initialized with default language: {self._default_lang_code_2} (3-letter: {self._default_lang_code_3})")

    def extract_from_csw(self, metadata: MD_Metadata, xml_content: str) -> dict:
        """
        Extract metadata from both MD_Metadata object and raw XML.
        """
        try:
            # Add debug logging
            if self._debug:
                log.debug("Starting metadata extraction for record: %s", metadata.identifier)
            
            # Extract owslib metadata
            owslib_metadata = self._generate_metadata_with_owslib(metadata)
            #if self._debug:
            #    log.debug("OWSLib metadata extracted: %s", owslib_metadata)


            #TODO: Fix or improve basic owslib_metadata
            # # Extract base INSPIRE metadata
            # inspire_metadata = _generate_metadata_inspire(xml_content)
            #if self._debug:
            #    log.debug("INSPIRE metadata extracted: %s", inspire_metadata)
            
            # # Parse XML for additional fields
            # root = etree.fromstring(xml_content)
            # xml_metadata = self._generate_metadata_using_xml(root)
            #if self._debug:
            #    log..debug("XML direct metadata extracted: %s", xml_metadata)

            # Combine all metadata sources with priority
            combined_metadata = {
                **owslib_metadata,   # OWSLib base metadata
                # **inspire_metadata,  # Base INSPIRE metadata
                # **xml_metadata,      # Direct XML extraction
            }
            
            # Filter out None values
            filtered_metadata = {
                k: v for k, v in combined_metadata.items() 
                if v is not None
            }
            
            if self._debug:
                log.debug("Final combined metadata: %s", filtered_metadata)
            
            return filtered_metadata
                
        except Exception as e:
            log.error("Error extracting metadata: %s", str(e), exc_info=True)
            return {}
    
    #TODO: Not used
    def extract_metadata(self, xml_content):
        """
        Main extraction method that combines INSPIRE metadata with additional fields.
        """
        try:
            # Extract base INSPIRE metadata
            inspire_metadata = _generate_metadata_inspire(xml_content)
            
            # Parse XML for additional metadata
            root = etree.fromstring(xml_content)
            metadata = MD_Metadata(root)
            
            # Extract additional non-INSPIRE metadata
            additional = self._generate_additional_metadata(metadata, root)
            
            # Combine INSPIRE and additional metadata
            return {**inspire_metadata, **additional}
            
        except Exception as e:
            log.error(f"Error extracting metadata: {str(e)}")
            return {}

    # Main method
    def _generate_metadata_with_owslib(self, metadata):
        """Extract standard ISO 19139 metadata using owslib"""
        try:
            # Get dataset identifier first
            identifier = getattr(metadata, 'identifier', None)

            # Extract translated fields
            title, title_translated = self._get_translated_field(
                metadata, 'title', 'identification', 'title'
            )
            notes, notes_translated = self._get_translated_field(
                metadata, 'notes', 'identification', 'abstract'
            )
            
            provenance, provenance_translated = self._extract_provenance(metadata)
            version_notes, version_notes_translated = self._get_translated_field(
                metadata, 'version_notes', 'identification', 'version'
            )
            
            # Get contact information
            contact_name, contact_email, contact_role = self._extract_contact(metadata)
            
            # Get distributions with dataset identifier
            resources = self._extract_distributions(metadata, dataset_identifier=identifier)

            # Example: if metadata.language is 'eng', this will return
            # 'http://publications.europa.eu/resource/authority/language/ENG'
            metadata_language = metadata.language if metadata.language else self._default_lang_code_3

            language_uri = self._validate_value_to_uri(
                value=metadata_language,
                valid_values=valid_languages,
                vocabulary_base_uri=f"{BASE_VOCABS['eu_publications']}language/",
                uppercase=True,
                default_value=f"{BASE_VOCABS['eu_publications']}language/{self._default_lang_code_3.upper()}"
            )
            
            # Get keywords and INSPIRE themes
            tags, tags_uri, inspire_themes = self._extract_keywords(metadata)
            
            dates = self._extract_dates(metadata)
            
            # Return extracted metadata
            return {
                # Basic metadata
                "identifier": identifier,
                "dcat_type": self._extract_dcat_type(metadata),
                "title": title,
                "title_translated": title_translated,
                "notes": notes,
                "notes_translated": notes_translated,
                "tags": tags,
                "tag_uri": tags_uri,
                "issued": dates.get('issued'),
                "modified": dates.get('modified') or self._normalize_date(metadata.datestamp),
                "created": dates.get('created'),
                "language": language_uri,
                "metadata_profile": ISO19115_INSPIRE_DEFAULT_VALUES['metadata_profile'],
                "encoding": self._extract_character_encoding(metadata),
                "reference": [self._extract_metadata_value(metadata, None, 'parentidentifier')],
                "graphic_overview": self._extract_metadata_value(metadata, 'identification', 'graphicoverview'),
                "version_notes": version_notes_translated,
                "conforms_to": ISO19115_INSPIRE_DEFAULT_VALUES['conformance'],

                # Temporal
                "temporal_start": self._normalize_date(self._extract_metadata_value(metadata, 'identification', 'temporalextent_start')),
                "temporal_end": self._normalize_date(self._extract_metadata_value(metadata, 'identification', 'temporalextent_end')),

                # Contact Point
                "contact_name": contact_name,
                "contact_email": contact_email,
                "contact_role": contact_role,
                
                # Maintainer info

                # INSPIRE
                "provenance": provenance_translated,
                "inspire_id": self._extract_metadata_value(metadata, 'identification', 
                                                       'uricode'),
                "reference_system": self._extract_reference_system(metadata),
                "representation_type": self._extract_mapped_value(metadata, 'identification', 'spatialrepresentationtype', ISO19115_REPRESENTATION_TYPE),
                "spatial": self._extract_bounding_box(metadata),
                "topic": self._extract_mapped_value(metadata, 'identification', 'topiccategory', ISO19115_TOPIC_CATEGORY),
                "theme": inspire_themes,

                # Distributions
                "resources": resources,
            }
                
        except Exception as e:
            log.error(f"Error in _generate_metadata_with_owslib: {str(e)}")
            return {}
    
    #TODO: Implement
    def _generate_metadata_using_xml(self, root):
        """Extract additional metadata directly from XML"""
        namespaces = root.nsmap
        try:
            return {
                "language": self._get_xml_value(root, ".//gmd:language/gco:CharacterString/text()", namespaces),
                "spatial": self._extract_spatial(root, namespaces),
                "temporal_extent": self._extract_temporal_extent(root, namespaces),
                "lineage": self._get_xml_value(root, ".//gmd:lineage//gmd:statement/gco:CharacterString/text()", namespaces),
                "quality": self._extract_quality_info(root, namespaces),
                "constraints": self._extract_constraints(root, namespaces)
            }
        except Exception as e:
            log.warning(f"Error extracting additional metadata: {str(e)}")
            return {}

    # OWSLib
    def _get_metadata_list(self, metadata, attribute, object_attribute=None):
        """
        Safely extracts list values from metadata attributes.
        
        Args:
            metadata (MD_Metadata): The metadata object
            attribute (str): The attribute name to extract
            object_attribute (str, optional): For lists of objects, the attribute to extract from each object
            
        Returns:
            list: List of values or empty list if not found
            
        Examples:
            # For simple lists:
            keywords = extractor._get_metadata_list(metadata, 'keywords')
            
            # For lists of objects:
            titles = extractor._get_metadata_list(metadata, 'identification', 'title')
            contacts = extractor._get_metadata_list(metadata, 'contact', 'organization')
        """
        try:
            # Get the attribute value
            values = getattr(metadata, attribute, None)
            
            # Return empty list if no values
            if not values:
                return []
                
            # Ensure we have a list
            if not isinstance(values, list):
                values = [values]
                
            # For simple lists, return as is
            if not object_attribute:
                return values
                
            # For lists of objects, extract specified attribute
            result = []
            for item in values:
                if hasattr(item, object_attribute):
                    value = getattr(item, object_attribute)
                    if value:
                        result.append(value)
                        
            return result
            
        except Exception as e:
            log.warning(f"Error extracting {attribute} list: {str(e)}")
            return []

    def _build_multilingual_dict(self, value, lang_code):
        """
        Builds a multilingual dictionary from a value and language code.
        
        Args:
            value (str): The text value to include in the dictionary
            lang_code (str): The language code for the value
            
        Returns:
            dict: A dictionary with language codes as keys and text as values,
                or empty dict if value is None or empty
                
        Example:
            >>> _build_multilingual_dict("Test title", "es")
            {'es': 'Test title'}
        """
        if not value or not lang_code:
            return {}
            
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
            
        return {lang_code: value} if value else {}

    def _normalize_date(self, date, source_date_format=None):
        """
        Normalize the given date to the format 'YYYY-MM-DD'.

        Args:
            date (str or datetime): The date to be normalized.
            source_date_format (str): The format of the source date.

        Returns:
            str: The normalized date in the format 'YYYY-MM-DD', or None if the date cannot be normalized.

        """
        if date is None:
            return None

        if isinstance(date, str):
            date = date.strip()
            if not date:
                return None
            try:
                if source_date_format:
                    date = datetime.strptime(date, source_date_format).strftime("%Y-%m-%d")
                else:
                    date = parse(date).strftime("%Y-%m-%d")
            except ValueError:
                log.error('normalize_date failed for: "%s" Check config source_date_format: "%s"', date, source_date_format)
                return None
        elif isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        
        return date
    
    def _get_translated_field(self, metadata, field_name, attribute, object_attribute=None):
        """
        Extract both translated and single language versions of a field.
        
        Args:
            metadata (MD_Metadata): The metadata object
            field_name (str): Base name for the field (e.g. 'title', 'notes')
            attribute (str): The attribute to extract from metadata
            object_attribute (str, optional): For lists of objects, the attribute to extract
        
        Returns:
            tuple: (single_value, translated_dict) where:
                - single_value is the value in default language or first available
                - translated_dict is the full dictionary of translations
        """
        try:
            # Get language code
            lang_code = self._map_language_code(metadata.language, output_format='2')
            
            # Get raw value
            raw_value = self._get_metadata_list(metadata, attribute, object_attribute)
            
            # Build translated dictionary
            translated_dict = self._build_multilingual_dict(raw_value, lang_code)
            
            # Get single language value
            single_value = (translated_dict.get(self._default_lang_code_2) or 
                        next(iter(translated_dict.values()), None) 
                        if translated_dict else None)
            
            return single_value, translated_dict
            
        except Exception as e:
            log.error(f"Error extracting translated field {field_name}: {str(e)}")
            return None, {}
        
    def _extract_mapped_value(self, metadata, category, property_name, mapping_dict, 
                             default_key='default', base_uri=None):
        """
        Generic function to extract and map metadata values using codelists.
        
        Args:
            metadata (MD_Metadata): The metadata object
            category (str): Metadata category to extract from (e.g. 'identification')
            property_name (str): Property name to extract (e.g. 'spatialrepresentationtype')
            mapping_dict (dict): Dictionary mapping source values to target values
            default_key (str): Key to use in mapping_dict if value not found
            base_uri (str, optional): Base URI to prepend to mapped values
            
        Returns:
            str: Mapped value from codelist, with optional base URI
            
        Examples:
            >>> # Extract representation type
            >>> type = self._extract_mapped_value(
            ...     metadata,
            ...     'identification',
            ...     'spatialrepresentationtype', 
            ...     ISO19115_REPRESENTATION_TYPE
            ... )
            
            >>> # Extract hierarchy with base URI
            >>> hierarchy = self._extract_mapped_value(
            ...     metadata,
            ...     'hierarchy',
            ...     'hierarchylevel',
            ...     ISO19115_HIERARCHY,
            ...     base_uri='http://example.org/types/'
            ... )
        """
        try:
            if self._debug:
                log.debug(f"Extracting {category}.{property_name} for mapping")
                
            # Extract raw value
            raw_value = self._extract_metadata_value(metadata, category, property_name)
            
            if not raw_value:
                if self._debug:
                    log.debug(f"No value found for {category}.{property_name}, using default")
                mapped_value = mapping_dict.get(default_key)
            else:
                # Map value using provided dictionary
                mapped_value = mapping_dict.get(raw_value, mapping_dict.get(default_key))
                
            if self._debug:
                log.debug(f"Mapped {raw_value} to {mapped_value}")
                
            # Add base URI if provided
            if base_uri and mapped_value:
                return f"{base_uri}{mapped_value}"
                
            return mapped_value
            
        except Exception as e:
            if self._debug:
                log.error(f"Error mapping {category}.{property_name}: {str(e)}")
            return mapping_dict.get(default_key)

    def _validate_value_to_uri(self, value, valid_values, vocabulary_base_uri, 
                              uppercase=False, default_value=None, append_to_uri=True):
        """
        Validates if a value exists in a controlled vocabulary and generates a URI.
    
        Args:
            value (str): The value to validate
            valid_values (list): List of valid values to check against
            vocabulary_base_uri (str): Base URI for the vocabulary
            uppercase (bool): Whether to convert the value to uppercase in final URI
            default_value (str): Value to return if value not in valid_values
            append_to_uri (bool): Whether to append the value to the URI
    
        Returns:
            str: Complete URI if value is valid, or default_value if not
    
        Examples:
            >>> valid_langs = ['eng', 'spa', 'fra']
            >>> self._validate_value_to_uri(
            ...     'ENG', 
            ...     valid_languages,
            ...     'http://publications.europa.eu/resource/authority/language/',
            ...     uppercase=True
            ... )
            'http://publications.europa.eu/resource/authority/language/ENG'
        """
        if not value or not isinstance(value, str):
            return default_value
    
        # Convert both input value and valid values to lowercase for comparison
        value_lower = value.strip().lower()
        valid_values_lower = [v.lower() for v in valid_values] if valid_values else []
    
        if value_lower not in valid_values_lower:
            return default_value
    
        # Find original case from valid_values if it exists
        original_index = valid_values_lower.index(value_lower)
        final_value = valid_values[original_index]
    
        # Apply case transformation if requested
        if uppercase:
            final_value = final_value.upper()
        
        if not append_to_uri:
            return final_value
            
        return f"{vocabulary_base_uri}{final_value}"
    
    def _map_language_code(self, code, output_format='auto'):
        """
        Converts between ISO 639-2 (3-letter) and ISO 639-1 (2-letter) language codes.
        
        Args:
            code (str): The language code to convert
            output_format (str): Desired output format:
                - 'auto': matches input length (default)
                - '2': forces 2-letter output
                - '3': forces 3-letter output

        Returns:
            str: The converted language code in specified format

        Examples:
            >>> _map_language_code('eng')  # self._default_lang_code_2='es'
            'es'
            >>> _map_language_code('en', output_format='3')
            'spa'
            >>> _map_language_code(None, output_format='2')
            'es'
            >>> _map_language_code('xyz', output_format='3')
            'spa'
        """
        # Create reverse mapping once
        reverse_mapping = {v: k for k, v in ISO19115_LANGUAGE.items()}

        # Handle invalid input
        if not code or not isinstance(code, str):
            return (self._default_lang_code_2 if output_format == '2' 
                    else self._default_lang_code_3 if output_format == '3'
                    else self._default_lang_code_3)  # default to 3-letter for 'auto'

        code = code.lower().strip()
        
        # Determine source format and map accordingly
        if len(code) == 3:
            mapped_code = ISO19115_LANGUAGE.get(code, self._default_lang_code_2)
            mapped_3_letter = code if code in ISO19115_LANGUAGE else self._default_lang_code_3
        elif len(code) == 2:
            mapped_3_letter = reverse_mapping.get(code, self._default_lang_code_3)
            mapped_code = code if code in ISO19115_LANGUAGE.values() else self._default_lang_code_2
        else:
            # Invalid length
            mapped_code = self._default_lang_code_2
            mapped_3_letter = reverse_mapping[self._default_lang_code_2]

        # Return in requested format
        if output_format == '2':
            return mapped_code
        elif output_format == '3':
            return mapped_3_letter
        else:  # 'auto' - match input length
            return mapped_code if len(code) == 2 else mapped_3_letter
        
    def _extract_metadata_value(self, metadata, category, property_name, return_object=False):
        """
        Extract a value from metadata object, handling both categories and root properties.
        
        Args:
            metadata (MD_Metadata): The metadata object
            category (str, optional): The category to look in (e.g., 'identification', 'dataquality').
                                    If None or not found, will look in root metadata.
            property_name (str): The property name to extract
            return_object (bool): If True, returns the raw object instead of converting to string
                
        Returns:
            str or object: The first value found (as string or original object) or None if not found/valid
        
        Examples:
            >>> # Get string value from category
            >>> inspire_id = self._extract_metadata_value(metadata, 'identification', 'uricode')
            >>> # Get object value
            >>> bbox_obj = self._extract_metadata_value(metadata, 'identification', 'bbox', return_object=True)
        """
        try:
            if self._debug:
                log.debug(f"Attempting to extract {property_name}" + 
                         f" from {category if category else 'root'}")
            
            target_obj = metadata
            
            # If category is provided and exists, use it
            if category and hasattr(metadata, category):
                category_obj = getattr(metadata, category)
                
                # Handle different category types
                if isinstance(category_obj, list):
                    if not category_obj:
                        return None
                    target_obj = category_obj[0]
                elif category_obj is None:
                    return None
                else:
                    target_obj = category_obj
                    
            # Check for property in target object
            if not hasattr(target_obj, property_name):
                if self._debug:
                    location = f"in {category}" if category else "in root metadata"
                    log.warning(f"Property '{property_name}' not found {location}")
                return None
                
            value = getattr(target_obj, property_name)
            
            # Return raw object if requested
            if return_object:
                if self._debug:
                    log.debug(f"Returning raw object for {property_name}")
                return value
            
            # Handle property value types
            if isinstance(value, list):
                if not value:
                    return None
                result = str(value[0]).strip()
                if self._debug:
                    log.debug(f"Extracted first value from list: '{result}'")
                return result
                
            elif isinstance(value, (str, int, float)):
                result = str(value).strip()
                if self._debug:
                    log.debug(f"Extracted single value: '{result}'")
                return result
                
            elif value is None:
                return None
                
            if self._debug:
                log.warning(f"Unexpected value type: {type(value)}")
            return None
                
        except Exception as e:
            if self._debug:
                location = f"{category}." if category else ""
                log.error(f"Error extracting {location}{property_name}: {str(e)}")
            return None
        
    # OWSLIb: ISO extraction
    def extract_bounding_box_from_iso(self, dataset, bounding_box):
        """Sets the bounding box for a dataset based on an ISO bounding box.

        Args:
            dataset: The dataset to set the bounding box for.
            bounding_box: An ISO bounding box object.

        Returns:
            None.

        Raises:
            None.
        """
        # Need to convert a string to float
        self._set_min_max_coordinates(dataset, float(bounding_box.minx), float(bounding_box.maxx), float(bounding_box.miny), float(bounding_box.maxy))

    def _extract_character_encoding(self, metadata):
        """
        Extract and map character encoding metadata to encoding using ISO19115_CHARACTER_ENCODING mapping.
        
        Args:
            metadata (MD_Metadata): The metadata object
            
        Returns:
            str: Mapped charset URI from ISO19115_CHARACTER_ENCODING
        """
        try:
            # Default value
            charset = 'default'
            
            # Try to extract hierarchy level from metadata
            if hasattr(metadata, 'charset') and metadata.charset:
                charset = metadata.charset.lower() if metadata.charset else charset
            
            # Map using ISO19115_CHARACTER_ENCODING dictionary
            encoding = ISO19115_CHARACTER_ENCODING.get(
                charset, 
                ISO19115_CHARACTER_ENCODING['default']
            )
            
            return encoding
            
        except Exception as e:
            log.error(f"Error extracting encoding: {str(e)}")
            return ISO19115_CHARACTER_ENCODING['default']
 
    def _extract_dcat_type(self, metadata):
        """
        Extract and map hierarchy metadata to dcat_type using ISO19115_HIERARCHY mapping.
        
        Args:
            metadata (MD_Metadata): The metadata object
            
        Returns:
            str: Mapped dcat_type URI from ISO19115_HIERARCHY
        """
        try:
            # Default value
            hierarchy_level = 'default'
            
            # Try to extract hierarchy level from metadata
            if hasattr(metadata, 'hierarchy') and metadata.hierarchy:
                # Get the first hierarchy level if it exists
                if getattr(metadata.hierarchy, 'level', None):
                    hierarchy_level = metadata.hierarchy.level[0].lower() if metadata.hierarchy.level else hierarchy_level
            
            # Map using ISO19115_HIERARCHY dictionary
            dcat_type = ISO19115_HIERARCHY.get(
                hierarchy_level, 
                ISO19115_HIERARCHY['default']
            )
            
            return dcat_type
            
        except Exception as e:
            log.error(f"Error extracting dcat_type: {str(e)}")
            return ISO19115_HIERARCHY['default']

    def _extract_provenance(self, metadata):
        """
        Extract lineage statement and process it as a multilingual field.
        
        ISO19115: DQ_DataQuality.lineage > LI_Lineage.statement
        
        Args:
            metadata (MD_Metadata): The metadata object
            
        Returns:
            tuple: (provenance_value, provenance_translated) where:
                - provenance_value is the value in default language or first available
                - provenance_translated is the full dictionary of translations
                
        Example:
            >>> provenance, provenance_translated = self._extract_provenance(metadata)
            >>> # Returns statement like: "This dataset was created by..."
        """
        try:
            if self._debug:
                log.debug("Extracting lineage/provenance information")
                
            # Get lineage statement from metadata using the dataquality and lineage paths
            lineage_statement = None
            
            # First try to access through dataquality
            if hasattr(metadata, 'dataquality'):
                dataquality = metadata.dataquality
                
                # Handle list or single object
                if isinstance(dataquality, list):
                    if dataquality:
                        dq = dataquality[0]
                        if hasattr(dq, 'lineage') and hasattr(dq.lineage, 'statement'):
                            lineage_statement = dq.lineage.statement
                else:
                    if hasattr(dataquality, 'lineage') and hasattr(dataquality.lineage, 'statement'):
                        lineage_statement = dataquality.lineage.statement
                        
            # Get language code for translation dictionary
            lang_code = self._map_language_code(metadata.language, output_format='2')
            
            # Build translated dictionary from lineage statement
            translated_dict = {}
            if lineage_statement:
                translated_dict = self._build_multilingual_dict(lineage_statement, lang_code)
                
            # Get single language value
            single_value = (translated_dict.get(self._default_lang_code_2) or 
                        next(iter(translated_dict.values()), None) 
                        if translated_dict else None)
                        
            return single_value, translated_dict
            
        except Exception as e:
            log.error(f"Error extracting provenance/lineage: {str(e)}")
            return None, {}

    def _extract_distributions(self, metadata, dataset_identifier=None):
        """
        Extract distributions from CSW metadata and map them to CKAN resources
        with improved format detection and access_services detection.
        Also standardizes OGC service URLs by adding GetCapabilities request if missing.
        
        Args:
            metadata (MD_Metadata): The metadata object containing distributions
            dataset_identifier (str): The identifier of the dataset to associate with access services
            
        Returns:
            list: List of dictionaries containing resource information
        """
        resources = []
        
        try:
            if not hasattr(metadata, 'distribution') or not metadata.distribution:
                if self._debug:
                    log.debug("No distributions found in metadata")
                return resources
    
            # Extract online resources
            online_resources = []
            if hasattr(metadata.distribution, 'online'):
                online_resources.extend(metadata.distribution.online or [])
    
            if not online_resources and self._debug:
                log.debug("No online resources found in distribution")
                return resources
    
            # Process each online resource
            for resource in online_resources:
                if not resource:
                    continue
    
                # Extract basic resource information
                resource_dict = {
                    "name": getattr(resource, 'name', None),
                    "description": getattr(resource, 'description', None),
                    "url": getattr(resource, 'url', None),
                    "protocol": getattr(resource, 'protocol', None),
                    "function": getattr(resource, 'function', None),
                    "availability": ISO19115_INSPIRE_DEFAULT_VALUES['availability'],
                }
    
                # Skip resources without URL
                if not resource_dict["url"]:
                    if self._debug:
                        log.debug(f"Skipping resource without URL: {resource_dict}")
                    continue
    
                # Default format to HTML
                resource_dict["format"] = 'HTML'
                format_found = False
    
                # 1. Try to determine format from protocol
                if resource_dict["protocol"]:
                    protocol_lower = resource_dict["protocol"].lower()
                    
                    # Check for exact match
                    if protocol_lower in [k.lower() for k in PROTOCOL_MAPPING]:
                        for protocol_key, format_value in PROTOCOL_MAPPING.items():
                            if protocol_key.lower() == protocol_lower:
                                resource_dict["format"] = format_value
                                format_found = True
                                if self._debug:
                                    log.debug(f"Format determined from exact protocol match: {protocol_key} -> {format_value}")
                                break
                    
                    # If not found, check for partial match
                    if not format_found:
                        for protocol_key, format_value in PROTOCOL_MAPPING.items():
                            if protocol_key.lower() in protocol_lower:
                                resource_dict["format"] = format_value
                                format_found = True
                                if self._debug:
                                    log.debug(f"Format determined from partial protocol match: {protocol_key} -> {format_value}")
                                break
    
                # 2. If format not determined from protocol, try URL patterns
                if not format_found and resource_dict["url"]:
                    url_lower = resource_dict["url"].lower()
                    
                    # Check for service indicators in URL
                    for service, indicators in SERVICE_INDICATORS.items():
                        for indicator in indicators:
                            if indicator in url_lower:
                                resource_dict["format"] = service
                                format_found = True
                                if self._debug:
                                    log.debug(f"Format determined from URL service indicator: {indicator} -> {service}")
                                break
                        if format_found:
                            break
                    
                    # Check for file extensions and other patterns in URL
                    if not format_found:
                        for pattern, format_value in FORMAT_STANDARDIZATION['format_patterns'].items():
                            if pattern.lower() in url_lower:
                                resource_dict["format"] = format_value
                                format_found = True
                                if self._debug:
                                    log.debug(f"Format determined from URL pattern: {pattern} -> {format_value}")
                                break
                
                # 3. Check for format hints in name or description
                if not format_found:
                    name_desc = ""
                    if resource_dict["name"]:
                        name_desc += resource_dict["name"].lower() + " "
                    if resource_dict["description"]:
                        name_desc += resource_dict["description"].lower()
                    
                    if name_desc:
                        for pattern, format_value in FORMAT_STANDARDIZATION['format_patterns'].items():
                            if pattern.lower() in name_desc:
                                resource_dict["format"] = format_value
                                format_found = True
                                if self._debug:
                                    log.debug(f"Format determined from name/description: {pattern} -> {format_value}")
                                break
                
                # 4. If still not found, use default
                if not format_found:
                    resource_dict["format"] = PROTOCOL_MAPPING.get('default', 'HTML')
                    if self._debug:
                        log.debug(f"Using default format: {resource_dict['format']}")
    
                # Add MIME type based on format
                resource_dict["mimetype"] = FORMAT_STANDARDIZATION['mimetype_mapping'].get(
                    resource_dict["format"], 
                    FORMAT_STANDARDIZATION['mimetype_mapping'].get('default')
                )
                
                # Standardize OGC service URLs by adding GetCapabilities if missing
                url = resource_dict["url"]
                format_value = resource_dict["format"]
                
                # Check if the URL is for an OGC service by format
                is_ogc_service = format_value in OGC_SERVICES_LIST
                
                if is_ogc_service and url:
                    # Check if the URL already contains a request parameter
                    has_request_param = "request=" in url.lower()
                    
                    if not has_request_param:
                        # Determine the appropriate GetCapabilities parameter based on the service
                        service_param = format_value.lower()
                        
                        # Add query parameters correctly whether URL already has parameters or not
                        if "?" in url:
                            # URL already has parameters, append the GetCapabilities request
                            resource_dict["url"] = f"{url}&service={service_param}&request=GetCapabilities"
                        else:
                            # URL has no parameters, add the GetCapabilities request
                            resource_dict["url"] = f"{url}?service={service_param}&request=GetCapabilities"
                        
                        if self._debug:
                            log.debug(f"Standardized OGC service URL with GetCapabilities: {resource_dict['url']}")
    
                # ENHANCEMENT: Add access_services with dataset identifier
                access_services, resource_dict = self._extract_access_services(resource_dict, dataset_identifier)
                log.info("access_services: %s", access_services)
                if access_services:
                    resource_dict["access_services"] = access_services
                    if self._debug:
                        log.debug(f"Added {len(access_services)} access services to resource")
    
                # Clean up None values and empty strings
                resource_dict = {k: v for k, v in resource_dict.items() 
                            if v is not None and v != ''}
    
                # Use description as name if name is missing
                if "name" not in resource_dict:
                    resource_dict["name"] = (
                        resource_dict.get("description") or 
                        resource_dict.get("format", "Resource")
                    )
                
                resources.append(resource_dict)
                if self._debug:
                    log.debug(f"Added resource: {resource_dict}")
    
            return resources
    
        except Exception as e:
            log.error(f"Error extracting distributions: {str(e)}", exc_info=True)
            return []

    def _extract_access_services(self, resource_dict, dataset_identifier=None):
        """
        Extract access services information from resource metadata.
        Also adds service standard URI to resource conforms_to field.
        
        Args:
            resource_dict (dict): The resource dictionary with metadata
            dataset_identifier (str): The identifier of the dataset to associate with this service
            
        Returns:
            list: List of access_services dictionaries
            resource_dict (dict): The resource dictionary with metadata
        """
        ckan_site_url = schemingdcat_get_ckan_site_url()
        services = []
        
        try:        
            # Get required fields for detection
            url = resource_dict.get("url")
            protocol = resource_dict.get("protocol", "").lower()
            format_value = resource_dict.get("format", "").upper()
            name = resource_dict.get("name", "")
            description = resource_dict.get("description", "")
            
            if not url:
                return services, resource_dict
                
            # Initialize detection variables
            service_type = None
            
            # 1. Check if format directly matches a service type
            if format_value in DCAT_SERVICE_TYPES:
                service_type = format_value
            
            # 2. If not found, check protocol indicators
            if not service_type and protocol:
                for type_key, type_info in DCAT_SERVICE_TYPES.items():
                    for indicator in type_info["protocol_indicators"]:
                        if indicator.lower() in protocol:
                            service_type = type_key
                            break
                    if service_type:
                        break
                        
            # 3. If still not found, check URL patterns
            if not service_type:
                url_lower = url.lower()
                for type_key, type_info in DCAT_SERVICE_TYPES.items():
                    for indicator in type_info["url_indicators"]:
                        if indicator.lower() in url_lower:
                            service_type = type_key
                            break
                    if service_type:
                        break
            
            # 4. Check name and description if still not found
            if not service_type:
                name_desc = (name + " " + description).lower()
                for type_key, type_info in DCAT_SERVICE_TYPES.items():
                    for indicator in type_info["name_indicators"]:
                        if indicator.lower() in name_desc:
                            service_type = type_key
                            break
                    if service_type:
                        break
            
            # If we found a service type, create the access service entry
            if service_type and service_type in DCAT_SERVICE_TYPES:
                service_info = DCAT_SERVICE_TYPES[service_type]
                
                # Create resource title
                resource_title = name.strip() if name else description.strip() if description else ""
                if resource_title:
                    title = f"{service_type} Service: {resource_title}"
                else:
                    title = service_info["default_title"]
                
                # Get base endpoint URL by removing query parameters if present
                base_url = schemingdcat_extract_base_url(url)
                    
                # Create the service info dictionary with base URL as the endpoint
                access_service = {
                    "uri": base_url,
                    "title": title,
                    "endpoint_url": [base_url],  # Base endpoint URL without parameters
                }
                
                # Generate GetCapabilities URL for endpoint description
                capabilities_param = service_info["capabilities_param"]
                if capabilities_param:
                    # Always use the clean base URL for capabilities
                    access_service["endpoint_description"] = f"{base_url}?{capabilities_param}"
                else:
                    # For services without capabilities, use the original URL
                    access_service["endpoint_description"] = url
                                    
                # Add serves_dataset reference if we have an identifier
                if dataset_identifier:
                    access_service["serves_dataset"] = f"{ckan_site_url}/dataset/{dataset_identifier}"
                else:
                    access_service["serves_dataset"] = []
                    
                # Add to services list
                services.append(access_service)
                    
                # Add service standard URI to resource conforms_to field if available
                if "uri" in service_info and service_info["uri"]:
                    # Initialize conforms_to list if it doesn't exist
                    if "conforms_to" not in resource_dict:
                        resource_dict["conforms_to"] = []
                    
                    # Add URI only if it's not already in the list
                    if service_info["uri"] not in resource_dict["conforms_to"]:
                        resource_dict["conforms_to"].append(service_info["uri"])
                        if self._debug:
                            log.debug(f"Added service standard URI to conforms_to: {service_info['uri']}")
    
            return services, resource_dict
            
        except Exception as e:
            if self._debug:
                log.warning(f"Error extracting access services: {str(e)}")
            return [], resource_dict

    def _extract_reference_system(self, metadata):
        """
        Extract and normalize coordinate reference system info to OpenGIS URI format.
        
        Returns:
            str: Normalized CRS in format 'http://www.opengis.net/def/crs/EPSG/0/{code}' 
                 or None if not found/invalid
        """
        try:
            if not hasattr(metadata, 'referencesystem') or not metadata.referencesystem.code:
                return None
                
            code = metadata.referencesystem.code
            
            # Extract EPSG code using regex
            epsg_match = re.search(r'EPSG:?(\d+)', code)
            
            if epsg_match:
                return f"{BASE_VOCABS['epsg_opengis']}{epsg_match.group(1)}"
                
            # Try to extract just numbers if EPSG pattern not found
            numbers = re.search(r'(\d+)', code)
            if numbers:
                return f"{BASE_VOCABS['epsg_opengis']}{numbers.group(1)}"
                
            return None
                
        except Exception as e:
            log.warning(f"Error extracting reference system: {str(e)}")
            return None
        
    def _extract_contact(self, metadata):
        """
        Extract contact information using _get_metadata_list
        
        Returns:
            tuple: (contact_name, contact_email, contact_role) or (None, None, None) if no valid information
        """
        try:
            # Get contact details using _get_metadata_list with fallback for name
            organizations = self._get_metadata_list(metadata, 'contact', 'organization')
            names = self._get_metadata_list(metadata, 'contact', 'name')
            emails = self._get_metadata_list(metadata, 'contact', 'email')
            roles = self._get_metadata_list(metadata, 'contact', 'role')
            
            # Get name with fallback logic
            contact_name = next((
                value for value in [
                    organizations[0] if organizations else None,
                    names[0] if names else None
                ] if value and value.strip()
            ), None)
            
            # Get email and role safely
            contact_email = emails[0] if emails else None
            contact_role = (f"{BASE_VOCABS['eu_inspire']}/ResponsiblePartyRole/{roles[0]}" 
                        if roles else None)
            
            return contact_name, contact_email, contact_role
                
        except Exception as e:
            log.warning(f"Error extracting contact information: {str(e)}")
            return None, None, None
        
    def _extract_keywords(self, metadata):
        """
        Extract keyword names and URIs from metadata, identifying INSPIRE themes directly from URLs.
        
        Args:
            metadata (MD_Metadata): The metadata object with nested MD_Keywords objects
            
        Returns:
            tuple: (keywords_list, inspire_themes_list) where:
                - keywords_list is a list of dictionaries with keyword names
                - inspire_themes_list is a list of INSPIRE theme URIs
        """
        try:
            # Initialize lists for regular keywords and INSPIRE themes
            keywords = []
            keywords_url = []
            inspire_themes = []
            
            # Get all keyword groups from identification
            identification = self._get_metadata_list(metadata, 'identification')
            if not identification:
                return keywords, inspire_themes
                
            # Get keywords from first identification object
            keyword_groups = getattr(identification[0], 'keywords', []) or []
            
            # Process each MD_Keywords group
            for keyword_group in keyword_groups:
                # Extract keywords from this group
                group_keywords = getattr(keyword_group, 'keywords', []) or []
                    
                # Process each keyword
                for kw in group_keywords:
                    # Extract name and URL directly
                    keyword_name = getattr(kw, 'name', None)
                    keyword_url = getattr(kw, 'url', None)
                    
                    # If we have a valid name, add it as a tag
                    if keyword_name:
                        keywords.append({"name": keyword_name})
                    
                    # If exists an URL add to keywords_url
                    if keyword_url:
                        keywords_url.append(keyword_url)
                    
                    # Check if URL is an INSPIRE theme
                    if keyword_url and 'inspire.ec.europa.eu/theme/' in keyword_url:
                        inspire_themes.append(keyword_url)
                
            # Remove duplicates from inspire_themes while preserving order
            inspire_themes = list(dict.fromkeys(inspire_themes))
                
            return keywords, keywords_url, inspire_themes
                
        except Exception as e:
            log.error(f"Error extracting keywords: {str(e)}", exc_info=True)
            return [], []
        
    def _extract_dates(self, metadata):
        """
        Extract dates from metadata identification dates list.
        Handles multiple date types (publication, revision, creation, etc).
        
        Args:
            metadata (MD_Metadata): The metadata object
            
        Returns:
            dict: Dictionary with date types as keys and normalized dates as values
                    e.g. {'issued': '2025-02-10', 'modified': '2025-02-11'}
                    
        Example:
            >>> dates = self._extract_dates(metadata)
            >>> dates.get('issued')  # Returns publication date
            '2025-02-10'
        """
        try:
            dates = {}
            
            # Get identification object first
            identification = self._extract_metadata_value(metadata, 'identification', 'date')
            
            if not identification:
                if self._debug:
                    log.debug("No dates found in metadata identification")
                return dates
                
            # Ensure we have a list
            if not isinstance(identification, list):
                identification = [identification]
                
            # Map date types to standardized keys
            date_type_mapping = {
                'publication': 'issued',
                'revision': 'modified',
                'creation': 'created',
                # Add more mappings as needed
            }
            
            # Process each date object
            for date_obj in identification:
                try:
                    if hasattr(date_obj, 'date') and hasattr(date_obj, 'type'):
                        date_value = self._normalize_date(date_obj.date)
                        date_type = date_obj.type.lower()
                        
                        # Map to standard key or use original
                        mapped_type = date_type_mapping.get(date_type, date_type)
                        
                        if date_value:
                            dates[mapped_type] = date_value
                            if self._debug:
                                log.debug(f"Found {mapped_type} date: {date_value}")
                                
                except AttributeError as e:
                    if self._debug:
                        log.warning(f"Error processing date object: {str(e)}")
                    continue
                    
            return dates
            
        except Exception as e:
            if self._debug:
                log.error(f"Error extracting dates: {str(e)}")
            return {}        
        

    def _extract_bounding_box(self, metadata):
        """
        Extract bounding box from metadata and convert to GeoJSON Polygon.
        
        Args:
            metadata (MD_Metadata): The metadata object
            
        Returns:
            str: GeoJSON string representation of the bounding box polygon or None if invalid
            
        Example:
            >>> bbox = self._extract_bounding_box(metadata)
            >>> # Returns GeoJSON like:
            >>> # {"type": "Polygon", "coordinates": [[[-19.0, 27.0], [4.57, 27.0], 
            >>> #   [4.57, 44.04], [-19.0, 44.04], [-19.0, 27.0]]]}
        """
        try:
            # Get identification object first with return_object=True
            bbox = self._extract_metadata_value(metadata, 'identification', 'bbox', return_object=True)
            
            if not bbox:
                return None
    
            try:
                minx = float(bbox.minx)
                miny = float(bbox.miny)
                maxx = float(bbox.maxx)
                maxy = float(bbox.maxy)
            except (ValueError, AttributeError) as e:
                log.warning(f"Invalid bounding box coordinates: {str(e)}")
                return None
                
            # Create GeoJSON polygon using shapely
            bbox_polygon = Polygon([
                (minx, miny),  # Bottom left
                (maxx, miny),  # Bottom right
                (maxx, maxy),  # Top right
                (minx, maxy),  # Top left
                (minx, miny)   # Close polygon
            ])
            
            # Convert to GeoJSON using shapely's mapping and json
            geojson_dict = mapping(bbox_polygon)
            geojson_str = json.dumps(geojson_dict)
                
            return geojson_str
            
        except Exception as e:
            log.error(f"Error extracting bounding box: {str(e)}")
            return None
        
    # XML: Metadata direct extraction using etree
    def _get_xml_value(self, root, xpath, namespaces):
        """Safe XML value extraction"""
        elements = root.xpath(xpath, namespaces=namespaces)
        return elements[0] if elements else None

    def _extract_spatial(self, root, namespaces):
        """Extract spatial extent"""
        bbox = root.xpath(".//gmd:EX_GeographicBoundingBox", namespaces=namespaces)
        if not bbox:
            return None
            
        return {
            "west": self._get_xml_value(bbox[0], ".//gmd:westBoundLongitude/gco:Decimal/text()", namespaces),
            "east": self._get_xml_value(bbox[0], ".//gmd:eastBoundLongitude/gco:Decimal/text()", namespaces),
            "north": self._get_xml_value(bbox[0], ".//gmd:northBoundLatitude/gco:Decimal/text()", namespaces),
            "south": self._get_xml_value(bbox[0], ".//gmd:southBoundLatitude/gco:Decimal/text()", namespaces)
        }

    def _extract_temporal_extent(self, root, namespaces):
        """Extract temporal coverage"""
        extent = root.xpath(".//gmd:EX_TemporalExtent//gml:TimePeriod", namespaces=namespaces)
        if not extent:
            return None
            
        return {
            "start": self._get_xml_value(extent[0], ".//gml:beginPosition/text()", namespaces),
            "end": self._get_xml_value(extent[0], ".//gml:endPosition/text()", namespaces)
        }
        
    def _get_character_encoding(self, root: etree.Element) -> str:
        """Extract character encoding if not UTF-8"""
        try:
            encoding = root.xpath(
                ".//gmd:characterSet/gmd:MD_CharacterSetCode/@codeListValue",
                namespaces=root.nsmap
            )
            return encoding[0] if encoding else "utf8"
        except Exception:
            return "utf8"

    def _get_maintenance_info(self, root: etree.Element) -> dict:
        """Extract maintenance information"""
        try:
            frequency = root.xpath(
                ".//gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",
                namespaces=root.nsmap
            )
            note = root.xpath(
                ".//gmd:maintenanceNote/gco:CharacterString/text()",
                namespaces=root.nsmap
            )
            return {
                "frequency": frequency[0] if frequency else None,
                "note": note[0] if note else None
            }
        except Exception:
            return {}
