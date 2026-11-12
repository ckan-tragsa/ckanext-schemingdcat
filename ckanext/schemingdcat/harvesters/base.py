import logging
import uuid
from functools import lru_cache
import json
import os
import re
from datetime import datetime
from dateutil.parser import parse
import six
import hashlib
import csv

import urllib.request
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError
import mimetypes
import requests

import ckan.logic as logic
from ckan.model import Session
from ckan.logic.schema import default_create_package_schema
from ckan.lib.navl.validators import ignore_missing, ignore
from ckan import plugins as p
from ckan import model
from ckantoolkit import config

from ckanext.harvest.harvesters import HarvesterBase
from ckanext.harvest.logic.schema import unicode_safe
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
from ckanext.schemingdcat.lib.field_mapping import FieldMappingValidator
from ckanext.schemingdcat.signals import schemingdcat_harvest_package_updated, schemingdcat_harvest_package_created

from ckanext.schemingdcat.config import (
    DATASET_DEFAULT_SCHEMA,
    RESOURCE_DEFAULT_SCHEMA,
    mimetype_base_uri,
    OGC2CKAN_HARVESTER_MD_CONFIG,
    OGC2CKAN_MD_FORMATS,
    DATE_FIELDS,
    DATASET_DEFAULT_FIELDS,
    RESOURCE_DEFAULT_FIELDS,
    CUSTOM_FORMAT_RULES,
    DATADICTIONARY_DEFAULT_SCHEMA,
    URL_REGEX,
    INVALID_CHARS,
    ACCENT_MAP,
    AUX_TAG_FIELDS,
    slugify_pat,
    field_mapping_extras_prefix,
    field_mapping_extras_prefix_symbol,
)

log = logging.getLogger(__name__)


class SchemingDCATHarvester(HarvesterBase):
    """
    A custom harvester for harvesting metadata using the Scheming DCAT extension.

    It extends the base `HarvesterBase` class provided by CKAN's harvest extension.
    """

    _mapped_schema = {}
    _local_schema = None
    _local_required_lang = None
    _remote_schema = None
    _local_schema_name = None
    _remote_schema_name = None
    _supported_schemas = set()
    _readme = "https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file"
    config = None
    api_version = 2
    action_api_version = 3
    force_import = False
    _site_user = None
    _source_date_format = '%Y-%m-%d'
    _dataset_default_values = {}
    _distribution_default_values = {}
    _field_mapping_validator = FieldMappingValidator()
    _field_mapping_validator_versions = _field_mapping_validator.validators.keys()
    _field_mapping_info = {
        "dataset_field_mapping": {
            "required": True,
            "content_dicts": "datasets"
        },
        "distribution_field_mapping": {
            "required": False,
            "content_dicts": "distributions"
        },
        "datadictionary_field_mapping": {
            "required": False,
            "content_dicts": "datadictionaries"
        }
    }

    def get_harvester_basic_info(self, config):
        """
        Retrieves basic information about the harvester.

        Args:
            config (str): The configuration in JSON format.

        Returns:
            dict: The configuration object parsed from the JSON.

        Raises:
            ValueError: If the configuration is empty or not in valid JSON format.
        """
        if not config:
            readme_doc = self.info().get("about_url", self._readme)
            raise ValueError(
                f"Configuration must be a JSON. Check README: {readme_doc}"
            )

        # Get local schema
        self._get_local_schemas_supported()

        if self._local_schema_name is not None and not config:
            return json.dumps(self._local_schema)

        # Load the configuration
        try:
            config_obj = json.loads(config)

        except ValueError as e:
            raise ValueError(f"Unable to load configuration: {e}")

        return config_obj

    def _set_config(self, config_str):
        """
        Sets the configuration for the harvester.

        Args:
            config_str (str): A JSON string representing the configuration.

        Returns:
            None
        """
        if config_str:
            self.config = json.loads(config_str)
            self.api_version = int(self.config.get("api_version", self.api_version))
        else:
            self.config = {}

    def _set_basic_validate_config(self, config):
        """
        Validates and sets the basic configuration for the harvester.

        Args:
            config (str): The configuration string in JSON format.

        Returns:
            str: The validated and updated configuration string.

        Raises:
            ValueError: If the configuration is invalid.

        """
        if not config:
            return config

        try:
            config_obj = json.loads(config)
            if "api_version" in config_obj:
                try:
                    int(config_obj["api_version"])
                except ValueError:
                    raise ValueError("api_version must be an integer")

            if "default_tags" in config_obj:
                if not isinstance(config_obj["default_tags"], list):
                    raise ValueError("default_tags must be a list")
                if config_obj["default_tags"] and not isinstance(
                    config_obj["default_tags"][0], dict
                ):
                    raise ValueError("default_tags must be a list of dictionaries")

            if "default_groups" in config_obj:
                if not isinstance(config_obj["default_groups"], list):
                    raise ValueError(
                        "default_groups must be a *list* of group names/ids"
                    )
                if config_obj["default_groups"] and not isinstance(
                    config_obj["default_groups"][0], str
                ):
                    raise ValueError(
                        "default_groups must be a list of group names/ids (i.e. strings)"
                    )

                # Check if default groups exist
                context = {"model": model, "user": p.toolkit.c.user}
                config_obj["default_group_dicts"] = []
                for group_name_or_id in config_obj["default_groups"]:
                    try:
                        group = logic.get_action("group_show")(
                            context, {"id": group_name_or_id}
                        )
                        # save the dict to the config object, as we'll need it
                        # in the import_stage of every dataset
                        config_obj["default_group_dicts"].append(
                            {"id": group["id"], "name": group["name"]}
                        )
                    except logic.NotFound:
                        raise ValueError("Default group not found")
                config = json.dumps(config_obj)

            if "default_extras" in config_obj:
                if not isinstance(config_obj["default_extras"], dict):
                    raise ValueError("default_extras must be a dictionary")

            if "user" in config_obj:
                # Check if user exists
                context = {"model": model, "user": p.toolkit.c.user}
                try:
                    logic.get_action("user_show")(
                        context, {"id": config_obj.get("user")}
                    )
                except logic.NotFound:
                    raise ValueError("User not found")

            for key in ("read_only", "force_all", "override_local_datasets"):
                if key in config_obj:
                    if not isinstance(config_obj[key], bool):
                        raise ValueError("%s must be boolean" % key)

        except ValueError as e:
            raise e

        return config

    @lru_cache(maxsize=8)
    def _get_local_schema(self, schema_type="dataset"):
        """
        Retrieves the schema for the dataset instance and caches it using the LRU cache decorator for efficient retrieval.

        Args:
            schema_type (str, optional): The type of schema to retrieve. Defaults to 'dataset'.

        Returns:
            dict: The schema of the dataset instance.
        """
        return logic.get_action("scheming_dataset_schema_show")(
            {}, {"type": schema_type}
        )

    @lru_cache(maxsize=None)
    def _get_remote_schema(self, base_url, schema_type="dataset"):
        """
        Fetches the remote schema for a given base URL and schema type.
    
        Args:
            base_url (str): The base URL of the remote server.
            schema_type (str, optional): The type of schema to fetch. Defaults to 'dataset'.
    
        Returns:
            dict: The remote schema as a dictionary, or None if there is an error.
    
        """
        url = (
            base_url
            + self._get_action_api_offset()
            + "/scheming_dataset_schema_show?type="
            + schema_type
        )
        try:
            content = self._get_content(url)
            content_dict = json.loads(content)
            #log.debug('content_dict: %s', content_dict)
            
            # Check if content_dict is a dictionary and contains 'result'.
            if isinstance(content_dict, dict) and "result" in content_dict:
                return content_dict["result"]
            else:
                return None
        except (ContentFetchError, ValueError, KeyError) as e:
            log.debug("Could not fetch/decode remote schema: %s", e)
            return None

    def _get_local_required_lang(self):
        """
        Retrieves the required language for the local schema.

        Returns:
            str: The required language for the local schema.
        """
        if self._local_schema is None:
            self._local_schema = self._get_local_schema()

        if self._local_required_lang is None:
            self._local_required_lang = self._local_schema.get(
                "required_language", None
            )

        return self._local_required_lang

    def _get_local_schemas_supported(self):
        """
        Retrieves the local schema supported by the harvester.

        Returns:
            list: A list of supported local schema names.
        """

        if self._local_schema is None:
            self._local_schema = self._get_local_schema()

        if self._local_schema_name is None:
            self._local_schema_name = self._local_schema.get("schema_name", None)

        if self._local_required_lang is None:
            self._local_required_lang = self._get_local_required_lang()

        # Get the set of available schemas
        # self._supported_schemas = set(schemingdcat_get_schema_names())
        self._supported_schemas.add(self._local_schema_name)

    def _get_object_extra(self, harvest_object, key):
        """
        Helper function for retrieving the value from a harvest object extra,
        given the key
        """
        for extra in harvest_object.extras:
            if extra.key == key:
                return extra.value
        return None

    def _get_dict_value(self, _dict, key, default=None):
        """
        Returns the value for the given key on a CKAN dict

        By default a key on the root level is checked. If not found, extras
        are checked.

        If not found, returns the default value, which defaults to None
        """

        if key in _dict:
            return _dict[key]

        for extra in _dict.get("extras", []):
            if extra["key"] == key:
                return extra["value"]

        return default

    def _generate_identifier(self, dataset_dict):
        """
        Generate a unique identifier for a dataset based on its attributes. First checks if the 'identifier' attribute exists in the dataset_dict. If not, it generates a unique identifier based on the 'inspire_id' or 'title' attributes.

        Args:
            dataset_dict (dict): The dataset object containing attributes like 'identifier', 'inspire_id', and 'title'.

        Returns:
            str: The generated unique identifier for the dataset_dict.

        Raises:
            ValueError: If neither 'inspire_id' nor 'title' is a string or does not exist in the dataset_dict.
        """
        identifier_source = self._get_dict_value(dataset_dict, "identifier") or None

        if identifier_source:
            return identifier_source
        elif dataset_dict.get("inspire_id") and isinstance(
            dataset_dict["inspire_id"], str
        ):
            identifier_source = dataset_dict["inspire_id"]
        elif dataset_dict.get("title") and isinstance(dataset_dict["title"], str):
            identifier_source = dataset_dict["title"]

        if identifier_source:
            # Convert to lowercase, replace all spaces with '-'
            joined_words = "-".join(identifier_source.lower().split())
            # Generate a SHA256 hash of the joined words
            hash_value = hashlib.sha256(joined_words.encode("utf-8")).hexdigest()
            # Generate a UUID based on the SHA256 hash
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, hash_value))
        else:
            raise ValueError(
                "Dataset identifier could not be generated. Need at least: inspire_id or title"
            )

    def _get_guid(self, dataset_dict, source_url=None):
        """
        Try to get a unique identifier for a harvested dataset

        It will be the first found of:
         * URI identifier
         * identifier
         * Source URL + Dataset name
         * Dataset name
         * uuid4

         The last two are obviously not optimal, as depend on title, which
         might change.

         Returns None if no guid could be decided.
        """
        guid = None

        guid = self._get_dict_value(dataset_dict, "uri") or self._get_dict_value(
            dataset_dict, "identifier"
        )
        if guid:
            return guid

        if dataset_dict.get("name"):
            guid = dataset_dict["name"]
            if source_url:
                guid = source_url.rstrip("/") + "/" + guid

        if not guid:
            guid = str(uuid.uuid4())

        return guid

    def _map_dataframe_columns_to_spreadsheet_format(self, df):
        """
        Maps the column positions of a DataFrame to spreadsheet column names.

        This function assigns the column names from 'A' to 'Z' for the first 26 columns,
        and then 'AA', 'AB', etc. for additional columns. It can handle an unlimited number
        of columns.

        Args:
            df (pandas.DataFrame): The DataFrame whose columns to rename.

        Returns:
            pandas.DataFrame: The DataFrame with renamed columns.
        """
        col_names = []
        for i in range(len(df.columns)):
            col_name = ""
            j = i
            while j >= 0:
                col_name = chr(j % 26 + 65) + col_name
                j = j // 26 - 1
            col_names.append(col_name)
        df.columns = col_names
        return df

    def _field_mapping_extract_default_values(self, field_mapping):
        """
        Extract default values from field mappings, keeping only field_value entries
        and properly handling multilingual fields.
        
        Args:
            field_mapping (dict): The field mapping dictionary
            
        Returns:
            dict: Dictionary with default values extracted from field_value entries
        """
        if not field_mapping:
            return {}
            
        defaults = {}
        
        for field_name, mapping in field_mapping.items():
            if isinstance(mapping, dict):
                # Handle multilingual fields
                if 'languages' in mapping:
                    translated = {}
                    for lang, lang_mapping in mapping['languages'].items():
                        if 'field_value' in lang_mapping:
                            translated[lang] = lang_mapping['field_value']
                    
                    if translated:
                        defaults[field_name] = translated
                
                # Handle regular fields with field_value
                elif 'field_value' in mapping:
                    defaults[field_name] = mapping['field_value']
        
        return defaults

    def _apply_field_mapping_default_values(self, package_dict):
        """
        Apply default values from field_mapping configuration to package_dict.
        These values are extracted from the 'field_value' properties in the field mapping.
        
        Args:
            package_dict (dict): The package dictionary to apply default values to
            
        Returns:
            dict: Updated package dictionary with field_mapping default values applied
        """
        if not hasattr(self, 'config_default_values') or not self.config_default_values:
            log.debug('No field mapping default values available')
            return package_dict
        
        dataset_defaults = self.config_default_values.get('dataset', {})
        distribution_defaults = self.config_default_values.get('distribution', {})

        # Apply dataset-level defaults
        for field, default_value in dataset_defaults.items():
            # Skip if field already has a value
            if field in package_dict and package_dict[field] is not None and package_dict[field] != '':
                continue
                
            # Handle translated fields
            if isinstance(default_value, dict) and any(lang in default_value for lang in p.toolkit.config.get('ckan.locales_offered', '').split()):
                if field not in package_dict:
                    package_dict[field] = {}
                for lang, value in default_value.items():
                    if lang not in package_dict[field] or not package_dict[field][lang]:
                        package_dict[field][lang] = self.substitute_ckan_site_url(value)
            else:
                # Regular field
                package_dict[field] = self.substitute_ckan_site_url(default_value)

        # Apply distribution-level defaults
        if distribution_defaults and 'resources' in package_dict:
            for resource in package_dict['resources']:
                for field, default_value in distribution_defaults.items():
                    # Skip if field already has a value
                    if field in resource and resource[field] is not None and resource[field] != '':
                        continue
                        
                    # Handle translated fields
                    if isinstance(default_value, dict) and any(lang in default_value for lang in p.toolkit.config.get('ckan.locales_offered', '').split()):
                        if field not in resource:
                            resource[field] = {}
                        for lang, value in default_value.items():
                            if lang not in resource[field] or not resource[field][lang]:
                                resource[field][lang] = self.substitute_ckan_site_url(value)
                    else:
                        # Regular field
                        resource[field] = self.substitute_ckan_site_url(default_value)
        
        return package_dict

    def _standardize_field_mapping(self, field_mapping):
        """
        Standardizes the field_mapping based on the schema version.

        Args:
            field_mapping (dict): A dictionary mapping the current column names to the desired column names.

        Returns:
            dict: The standardized field_mapping.
        """
        if field_mapping is not None:
            schema_version = self.config.get("field_mapping_schema_version", 2)
            if schema_version not in self._field_mapping_validator_versions:
                raise ValueError(f"Unsupported schema version: {schema_version}")

            if schema_version == 1:
                return self._standardize_field_mapping_v1(field_mapping)
            else:
                # If the schema version is the latest, return the field_mapping as is
                return field_mapping
        
        return field_mapping

    def _standardize_field_mapping_v1(self, field_mapping):
        """
        Standardizes the field_mapping for the first version of the schema.

        In the first version of the schema, the field_mapping is a dictionary where each key is a field_name and the value
        is either a field_name or a dictionary mapping language codes to field_names.

        Args:
            field_mapping (dict): A dictionary mapping the current column names to the desired column names.

        Returns:
            dict: The standardized field_mapping.
        """
        standardized_mapping = {}
        for key, value in field_mapping.items():
            if isinstance(value, dict):
                # If the value is a dictionary, it is a multilingual field
                standardized_mapping[key] = {'languages': {}}
                for lang, field_name in value.items():
                    standardized_mapping[key]['languages'][lang] = {'field_name': field_name}
            else:
                # If the value is not a dictionary, it is a single-language field
                standardized_mapping[key] = {'field_name': value}
        return standardized_mapping
    
    def _standardize_ckan_dict_from_field_mapping(self, dataset, field_mapping):
        """
        Standardizes a CKAN dataset dictionary according to the provided field mapping.
    
        Args:
            dataset (dict): The CKAN dataset dictionary.
            field_mapping (dict): The mapping of local field names to remote field names or values.
    
        Returns:
            dict: The standardized CKAN dataset dictionary.
        """
        def normalize_key(key):
            """
            Helper function to normalize the key by removing accents, converting to lowercase, replacing non-alphanumeric characters with '-', and trimming spaces.
            """
            try:
                key = key.strip()
                
                # Remove accents
                norm_key = key.translate(ACCENT_MAP)
                
                # Replace non-alphanumeric characters with underscores
                normalized_key = slugify_pat.sub('-', norm_key.lower())
                                
                #log.debug('key: %s normalize key: %s', key, normalized_key)
                
                return normalized_key
        
            except AttributeError:
                # Manejar el caso donde 'key' no es una cadena
                raise ValueError("The provided key must be a string")
            
            except Exception as e:
                # Manejar cualquier otra excepción
                raise RuntimeError(f"An unexpected error occurred: {e}")
    
        def get_extra_value(extras, key):
            """
            Helper function to get the value from the extras list where the key matches (case insensitive and normalized).
            """            
            normalized_key = normalize_key(key)
            for item in extras:
                if normalize_key(item['key']) == normalized_key:
                    #log.debug('"extras" dict key: %s - normalized: %s', key, normalized_key)
                    return item['value']
            
            return None
    
        def apply_field_mapping(d, mapping):
            new_dict = {}
            #TODO: If not field_mapping, items() fails.
            for local_field, remote_info in mapping.items():
                if 'field_name' in remote_info:
                    remote_field = remote_info['field_name']
                    if remote_field and remote_field.startswith(field_mapping_extras_prefix):
                        extra_key = remote_field.split(field_mapping_extras_prefix + field_mapping_extras_prefix_symbol, 1)[1]
                        extra_value = get_extra_value(d.get(field_mapping_extras_prefix, []), extra_key)
                        if extra_value is not None:
                            new_dict[local_field] = extra_value
                    elif remote_field in d:
                        new_dict[local_field] = d[remote_field]
                if 'field_value' in remote_info:
                    new_dict[local_field] = remote_info['field_value']
                if 'languages' in remote_info:
                    for lang, lang_info in remote_info['languages'].items():
                        if 'field_name' in lang_info:
                            remote_field = lang_info['field_name']
                            if remote_field and remote_field.startswith(field_mapping_extras_prefix):
                                extra_key = remote_field.split(field_mapping_extras_prefix + field_mapping_extras_prefix_symbol, 1)[1]
                                extra_value = get_extra_value(d.get(field_mapping_extras_prefix, []), extra_key)
                                if extra_value is not None:
                                    if local_field not in new_dict:
                                        new_dict[local_field] = {}
                                    new_dict[local_field][lang] = extra_value
                            elif remote_field in d:
                                if local_field not in new_dict:
                                    new_dict[local_field] = {}
                                new_dict[local_field][lang] = d[remote_field]
                        if 'field_value' in lang_info:
                            if local_field not in new_dict:
                                new_dict[local_field] = {}
                            new_dict[local_field][lang] = lang_info['field_value']
            return new_dict

        # Apply dataset field mapping
        dataset_field_mapping = field_mapping.get('dataset_field_mapping', {})
        standardized_dataset = apply_field_mapping(dataset, dataset_field_mapping)
    
        # Ensure default schema fields are included in the dataset
        for field in DATASET_DEFAULT_SCHEMA:
            if field in dataset:
                standardized_dataset[field] = dataset[field]
    
        # Maintain the tags list
        standardized_dataset['tags'] = dataset.get('tags', [])
    
        # Apply distribution field mapping to each resource
        distribution_field_mapping = field_mapping.get('distribution_field_mapping', {})
        standardized_resources = []
        for resource in dataset.get('resources', []):
            standardized_resource = apply_field_mapping(resource, distribution_field_mapping)
            
            # Ensure default schema fields are included in each resource
            for field in RESOURCE_DEFAULT_SCHEMA:
                if field in resource:
                    standardized_resource[field] = resource[field]
            
            standardized_resources.append(standardized_resource)
    
        standardized_dataset['resources'] = standardized_resources
    
        return standardized_dataset

    def _standardize_df_fields_from_field_mapping(self, df, field_mapping):
        """
        Standardizes the DataFrame columns based on the field_mapping.

        Args:
            df (pd.DataFrame): The DataFrame to standardize.
            field_mapping (dict): A dictionary mapping the current column names to the desired column names.
        """

        def rename_and_update(df, old_name, new_name, value_dict):
            if isinstance(old_name, list):
                # If old_name is a list, iterate over its elements
                for name in old_name:
                    df.rename(columns={name: new_name}, inplace=True)
            else:
                df.rename(columns={old_name: new_name}, inplace=True)
            value_dict['field_name'] = new_name

        def merge_values(row, fields):
            """
            Merges the values of specified fields in a row into a single string.

            This function takes a dictionary (row) and a list of fields. It checks if each field is present in the row.
            If the field value is a list, it joins the list into a string with comma separators.
            If the field value is a string and contains a comma, it strips the string of leading and trailing whitespace.
            If the field value is neither a list nor a string with a comma, it converts the value to a string and strips it of leading and trailing whitespace.
            Finally, it joins all the field values into a single string with comma separators.

            Args:
                row (dict): The row of data as a dictionary.
                fields (list): The list of fields to merge.

            Returns:
                str: The merged field values as a single string.

            """
            merged = []
            for field in fields:
                if field in row:  # Check if the field is in the row
                    val = row[field]
                    if isinstance(val, list):
                        merged.append(','.join(str(v).strip() for v in val))
                    elif isinstance(val, str) and ',' in val:
                        merged.append(val.strip())
                    else:
                        merged.append(str(val).strip())
            return ','.join(merged)

        removed_columns = []
        reserved_columns = ['dataset_id', 'identifier', 'resource_id', 'datadictionary_id']

        if field_mapping is not None:
            # Check if any field mapping contains 'field_position'
            if any('field_position' in value for value in field_mapping.values()):
                # Map the DataFrame columns to spreadsheet format
                df = self._map_dataframe_columns_to_spreadsheet_format(df)

            for key, value in field_mapping.items():
                if 'field_position' in value:
                    if isinstance(value['field_position'], list):
                        # Merge fields
                        # Apply the function to each row in the dataframe
                        df[key] = df.apply(lambda row: merge_values(row, value['field_position']), axis=1)
                        # Drop the original value columns
                        for field in value['field_position']:
                            df.drop(field, axis=1, inplace=True)
                    else:
                        rename_and_update(df, value['field_position'], key, value)
                elif 'field_name' in value:
                    if isinstance(value['field_name'], list):
                        # Merge fields
                        # Apply the function to each row in the dataframe
                        df[key] = df.apply(lambda row: merge_values(row, value['field_name']), axis=1)
                        # Drop the original value columns
                        for field in value['field_name']:
                            df.drop(field, axis=1, inplace=True)
                    else:
                        rename_and_update(df, value['field_name'], key, value)
                elif isinstance(value, dict) and 'languages' in value:
                    for lang, lang_value in value['languages'].items():
                        if 'field_position' in lang_value:
                            rename_and_update(df, lang_value['field_position'].upper(), f"{key}-{lang}", lang_value)
                        elif 'field_name' in lang_value:
                            rename_and_update(df, lang_value['field_name'], f"{key}-{lang}", lang_value)
                        # translated_fields only str

        # Calculate the difference between the DataFrame columns and the field_mapping keys
        log.debug('field_mapping: %s', field_mapping)
        columns_to_remove = set(df.columns) - set(field_mapping.keys())

        # Filter out columns that contain '-{lang}' or are in the columns_to_keep list
        columns_to_remove = [col for col in columns_to_remove if not re.search(r'-[a-z]{2}$', col) and col not in reserved_columns]

        # Convert the set to a list, sort it, and store it for logging
        removed_columns = sorted(list(columns_to_remove))

        # Remove the columns
        df.drop(columns=columns_to_remove, inplace=True)

        log.warning(f"Removed unused columns from remote sheet: {removed_columns}")

        return df, field_mapping

    def _validate_remote_schema(
        self,
        remote_ckan_base_url=None,
        remote_dataset_field_names=None,
        remote_resource_field_names=None,
        remote_dataset_field_mapping=None,
        remote_distribution_field_mapping=None,
    ):
        """
        Validates the remote schema by comparing it with the local schema.

        Args:
            remote_ckan_base_url (str, optional): The base URL of the remote CKAN instance. If provided, the remote schema will be fetched from this URL.
            remote_dataset_field_names (set, optional): The field names of the remote dataset schema. If provided, the remote schema will be validated using these field names.
            remote_resource_field_names (set, optional): The field names of the remote resource schema. If provided, the remote schema will be validated using these field names.
            remote_dataset_field_mapping (dict, optional): A mapping of local dataset field names to remote dataset field names. If provided, the local dataset fields will be mapped to the corresponding remote dataset fields.
            remote_distribution_field_mapping (dict, optional): A mapping of local resource field names to remote resource field names. If provided, the local resource fields will be mapped to the corresponding remote resource fields.

        Returns:
            bool: True if the remote schema is valid, False otherwise.

        Raises:
            RemoteSchemaError: If there is an error validating the remote schema.

        """
        def simplify_colnames(colnames):
            """
            Simplifies column names by removing language suffixes.

            Args:
                colnames (list): A list of column names.

            Returns:
                set: A set of simplified column names.
            """
            return set(name.split('-')[0] for name in colnames)

        def check_field_mapping(mapping_name, mapping_value):
            """
            Checks if a field mapping is required and if it is provided.

            Args:
                mapping_name (str): The name of the field mapping.
                mapping_value (str): The value of the field mapping.

            Returns:
                The value of the field mapping if it exists, otherwise None.

            Raises:
                ValueError: If the field mapping is required but not provided.
            """
            
            mapping_info = self._field_mapping_info.get(mapping_name)

            # If mapping_info is None, it means that mapping_name is invalid.
            if mapping_info is None:
                raise ValueError(f"{mapping_name} is not a valid field mapping.")

            # Checks if the mapping is required and if a value has not been provided
            if mapping_info["required"] and not mapping_value:
                raise ValueError(f"Field mapping '{mapping_name}' is required, but it is not provided.")

            return mapping_value

        def get_mapped_fields(fields, field_mapping):
            """
            Generates a list of mapped fields based on the provided fields and field mapping.

            Args:
                fields (list): A list of fields to be mapped.
                field_mapping (dict): A dictionary containing the field mapping.

            Returns:
                A list of dictionaries, each containing the local field name, the remote field name, 
                a flag indicating if the field was modified, and optionally the form languages and 
                the required language.

            Raises:
                Exception: If there is an error generating the mapping schema.
            """
            if field_mapping is None:
                return []

            try:
                return [
                    {
                        "local_field_name": field["field_name"],
                        "remote_field_name": (
                            {lang: f"{field['field_name']}-{lang}" for lang in field_mapping[field['field_name']]['languages'].keys()}
                            if 'languages' in field_mapping.get(field['field_name'], {})
                            else field['field_name']
                        ),
                        "modified": 'languages' in field_mapping.get(field['field_name'], {}),
                        **(
                            {"form_languages": list(field_mapping[field['field_name']]['languages'].keys())}
                            if 'languages' in field_mapping.get(field['field_name'], {})
                            else {}
                        ),
                        **(
                            {"required_language": field["required_language"]}
                            if field.get("required_language")
                            else {}
                        ),
                    }
                    for field in fields
                ]
            except Exception as e:
                logging.error("Error generating mapping schema: %s", e)
                raise

        try:
            if self._local_schema is None:
                self._local_schema = self._get_local_schema()

            if self._local_required_lang is None:
                self._local_required_lang = self._get_local_required_lang()

            local_datasets_colnames = set(
                field["field_name"] for field in self._local_schema["dataset_fields"]
            )
            local_distributions_colnames = set(
                field["field_name"] for field in self._local_schema["resource_fields"]
            )

            if remote_ckan_base_url is not None:
                log.debug("Validating remote schema from: %s", remote_ckan_base_url)
                if self._remote_schema is None:
                    self._remote_schema = self._get_remote_schema(remote_ckan_base_url)
            
                if self._remote_schema is not None:
                    remote_datasets_colnames = set(
                        field["field_name"]
                        for field in self._remote_schema["dataset_fields"]
                    )
                    remote_distributions_colnames = set(
                        field["field_name"]
                        for field in self._remote_schema["resource_fields"]
                    )
                else:
                    log.warning("Failed to retrieve remote schema from: %s. Using local schema and config field_mapping by default.", remote_ckan_base_url)
                    remote_datasets_colnames = set(remote_dataset_field_mapping.keys())
                    remote_distributions_colnames = set(remote_distribution_field_mapping.keys())
            
            elif remote_dataset_field_names is not None:
                log.debug(
                    "Validating remote schema using field names from package dict"
                )
                remote_datasets_colnames = remote_dataset_field_names
                remote_distributions_colnames = remote_resource_field_names

            datasets_diff = local_datasets_colnames - simplify_colnames(remote_datasets_colnames)
            distributions_diff = (
                local_distributions_colnames - simplify_colnames(remote_distributions_colnames)
            )

            # Check if field mapping is required for dataset and distribution
            remote_dataset_field_mapping = check_field_mapping("dataset_field_mapping", remote_dataset_field_mapping)
            remote_distribution_field_mapping = check_field_mapping("distribution_field_mapping", remote_distribution_field_mapping)

            if remote_dataset_field_mapping is None and remote_distribution_field_mapping is None:
                self._mapped_schema = None
            else:
                self._mapped_schema = {
                    "dataset_fields": get_mapped_fields(
                        self._local_schema.get("dataset_fields", []),
                        remote_dataset_field_mapping,
                    ) if remote_dataset_field_mapping is not None else None,
                    "resource_fields": get_mapped_fields(
                        self._local_schema.get("resource_fields", []),
                        remote_distribution_field_mapping,
                    ) if remote_distribution_field_mapping is not None else None,
                }

            log.info("Local required language: %s", self._local_required_lang)
            log.info(
                "Field names differences in dataset: %s and resource: %s",
                datasets_diff,
                distributions_diff,
            )
            log.info("Mapped schema: %s", self._mapped_schema)

        except SearchError as e:
            raise RemoteSchemaError("Error validating remote schema: %s" % str(e))

        return True

    def _clean_extras(self, dataset_dict, keys_to_clean):
        """
        Remove specified keys from extras and move their values to dataset_dict.
    
        Args:
            dataset_dict (dict): The dataset dictionary.
            keys_to_clean (list): List of keys to remove from extras and move to dataset_dict.
        """
        if 'extras' in dataset_dict:
            new_extras = []
            for extra in dataset_dict['extras']:
                if extra['key'] in keys_to_clean:
                    dataset_dict[extra['key']] = extra['value']
                else:
                    new_extras.append(extra)
            dataset_dict['extras'] = new_extras

    def _remove_duplicate_keys_in_extras(self, dataset_dict):
        """
        Remove duplicate keys in the 'extras' list of dictionaries of the given dataset_dict.

        Args:
            dataset_dict (dict): The dataset dictionary.

        Returns:
            dict: The updated dataset dictionary with duplicate keys removed from the 'extras' list of dictionaries.
        """
        common_keys = set(
            extra["key"] for extra in dataset_dict["extras"]
        ).intersection(dataset_dict)
        dataset_dict["extras"] = [
            extra for extra in dataset_dict["extras"] if extra["key"] not in common_keys
        ]

        return dataset_dict

    def _check_accesible_url(self, url, harvest_job, auth=False):
        """
        Check if the given URL is valid and accessible.

        Args:
            url (str): The URL to check.
            harvest_job (HarvestJob): The harvest job associated with the URL.
            auth (bool): Whether authentication is expected.

        Returns:
            bool: True if the URL is valid and accessible, False otherwise.
        """
        if not url.lower().startswith("http"):
            # Check local file
            if os.path.exists(url):
                return True
            else:
                self._save_gather_error(
                    "Could not get content for this url", harvest_job
                )
                return False

        try:
            # Open the URL without downloading the content
            urllib.request.urlopen(url)

            # If no exception was thrown, the URL is valid
            return True

        except HTTPError as e:
            if auth and e.code == 401:
                msg = f"Authorisation required, remember 'config.credentials' needed for: {url}"
                log.info(msg)
                return True
            else:
                msg = f"Could not get content from {url} because the connection timed out. {e}"
                self._save_gather_error(msg, harvest_job)
                return False
        except URLError as e:
            msg = """Could not get content from %s because a
                                connection error occurred. %s""" % (url, e)
            self._save_gather_error(msg, harvest_job)
            return False
        except FileNotFoundError:
            msg = "File %s not found." % url
            self._save_gather_error(msg, harvest_job)
            return False

    def _get_content_and_type(self, url, harvest_job, content_type=None):
        """
        Retrieves the content and content type from a given URL.

        Args:
            url (str): The URL to retrieve the content from.
            harvest_job (HarvestJob): The harvest job associated with the URL.
            content_type (str, optional): The expected content type. Defaults to None.

        Returns:
            tuple: A tuple containing the content and content type.
                   If an error occurs, returns None, None.
        """
        if not url.lower().startswith("http"):
            # Check local file
            if os.path.exists(url):
                with open(url, "r") as f:
                    content = f.read()
                content_type = content_type or "xlsx"
                return content, content_type
            else:
                self._save_gather_error(
                    "Could not get content for this url", harvest_job
                )
                return None, None

        try:
            log.debug("Getting file %s", url)

            # Retrieve the file and the response headers
            content, headers = urllib.request.urlretrieve(url)

            # Get the content type from the headers
            content_type = headers.get_content_type()

        except HTTPError as e:
            msg = f"Could not get content from {url} because the connection timed out. {e}"
            self._save_gather_error(msg, harvest_job)
            return None, None
        except URLError as e:
            msg = """Could not get content from %s because a
                                connection error occurred. %s""" % (url, e)
            self._save_gather_error(msg, harvest_job)
            return None, None
        except FileNotFoundError:
            msg = "File %s not found." % url
            self._save_gather_error(msg, harvest_job)
            return None, None

        return True

    # TODO: Implement this method
    def _load_datadictionaries(self, harvest_job, datadictionaries):
        return True

    def _find_existing_package_by_field_name(
        self, package_dict, field_name, return_fields=None
    ):
        """
        Find an existing package by a specific field name.

        Args:
            package_dict (dict): The package dictionary containing the field name.
            field_name (str): The name of the field to search for.
            return_fields (list, optional): List of fields to return. Defaults to None.

        Returns:
            dict: The existing package dictionary matching the field name.

        This method searches for an existing package in the CKAN instance based on its specific id. It takes a package dictionary and a field name as input parameters. The package dictionary should contain the field name to search for. The method returns the existing package dictionary that matches the field name. https://docs.ckan.org/en/2.9/api/#ckan.logic.action.get.package_search
        """
        data_dict = {
            "fq": f"{field_name}:{package_dict[field_name]}",
            "include_private": True,
        }

        if return_fields and isinstance(return_fields, list):
            data_dict["fl"] = ",".join(
                field
                if isinstance(field, str) and field == field.strip()
                else str(field).strip()
                for field in return_fields
            )

        package_search_context = {
            "model": model,
            "session": Session,
            "ignore_auth": True,
        }

        try:
            return logic.get_action("package_search")(package_search_context, data_dict)
        except p.toolkit.ObjectNotFound:
            pass

    def _check_existing_package_by_ids(self, package_dict):
        """
        Check if a package with the given identifiers already exists in the CKAN instance.

        Args:
            package_dict (dict): A dictionary containing the package information.

        Returns:
            package (dict or None): The existing package dictionary if found, None otherwise.
        """
        basic_id_fields = [
            "name",
            "id",
            "identifier",
            "alternate_identifier",
            "inspire_id",
        ]
        for field_name in basic_id_fields:
            if package_dict.get(field_name):
                package = self._find_existing_package_by_field_name(
                    package_dict, field_name
                )
                if package["results"] and package["results"][0]:
                    return package["results"][0]

        # If no existing package was found after checking all fields, return None
        return None

    def _set_translated_fields(self, package_dict):
        """
        Sets translated fields in the package dictionary based on the mapped schema.
    
        Args:
            package_dict (dict): The package dictionary to update with translated fields.
    
        Returns:
            dict: The updated package dictionary.
    
        Raises:
            ReadError: If there is an error translating the dataset.
    
        """
        if (
            not hasattr(self, "_mapped_schema")
            or "dataset_fields" not in self._mapped_schema
            or "resource_fields" not in self._mapped_schema
        ):
            return package_dict
        try:
            translated_fields = {"dataset_fields": [], "resource_fields": []}
            for field in self._mapped_schema["dataset_fields"]:
                if field.get("modified", True):
                    local_field_name = field["local_field_name"]
                    remote_field_name = field["remote_field_name"]
    
                    translated_fields["dataset_fields"].append(local_field_name)
    
                    if isinstance(remote_field_name, dict):
                        local_field_value = package_dict.get(local_field_name, {})
                        if not isinstance(local_field_value, dict):
                            local_field_value = {}
                        package_dict[local_field_name] = {
                            lang: package_dict.get(name, local_field_value.get(lang))
                            for lang, name in remote_field_name.items()
                        }
                        if local_field_name.endswith('_translated'):
                            if self._local_required_lang in remote_field_name:
                                package_dict[local_field_name.replace('_translated', '')] = package_dict.get(remote_field_name[self._local_required_lang], package_dict.get(local_field_name.replace('_translated', '')))
                            else:
                                raise ValueError("Missing translated field: %s for required language: %s" % (remote_field_name, self._local_required_lang))
                    else:
                        if remote_field_name not in package_dict:
                            raise KeyError(f"Field {remote_field_name} does not exist in the local schema")
                        package_dict[local_field_name] = package_dict.get(remote_field_name, package_dict.get(local_field_name))
    
            if package_dict["resources"]:
                for i, resource in enumerate(package_dict["resources"]):
                    if self._mapped_schema and "resource_fields" in self._mapped_schema and self._mapped_schema["resource_fields"] is not None:
                        for field in self._mapped_schema["resource_fields"]:
                            if field.get("modified", True):
                                local_field_name = field["local_field_name"]
                                remote_field_name = field["remote_field_name"]
    
                                translated_fields["resource_fields"].append(local_field_name)
    
                                if isinstance(remote_field_name, dict):
                                    resource[local_field_name] = {
                                        lang: resource.get(name, resource.get(local_field_name, {}).get(lang))
                                        for lang, name in remote_field_name.items()
                                    }
                                    if local_field_name.endswith('_translated'):
                                        if self._local_required_lang in remote_field_name:
                                            resource[local_field_name.replace('_translated', '')] = resource.get(remote_field_name[self._local_required_lang], resource.get(local_field_name.replace('_translated', '')))
                                        else:
                                            raise ValueError("Missing translated field: %s for required language: %s" % (remote_field_name, self._local_required_lang))
                                else:
                                    if remote_field_name not in resource:
                                        raise KeyError(f"Field {remote_field_name} does not exist in the local schema")
                                    resource[local_field_name] = resource.get(remote_field_name, resource.get(local_field_name))
    
                    else:
                        log.warning("self._mapped_schema['resource_fields'] is None, skipping resource fields translation.")
    
                    # Update the resource in package_dict
                    package_dict["resources"][i] = resource
    
            #log.debug('Translated fields: %s', translated_fields)
    
        except Exception as e:
            raise ReadError(
                "Error translating dataset: %s. Error: %s"
                % (package_dict["title"], str(e))
            )
    
        return package_dict

    # TODO: Fix this method
    def _get_allowed_values(self, field_name, field_type="dataset_fields"):
        """
        Get the allowed values for a given field name.

        Args:
            field_name (str): The name of the field.
            field_type (str, optional): The type of the field. Defaults to 'dataset_fields'.

        Returns:
            list: A list of allowed values for the field.
        """
        # Check if field_type is valid
        if field_type not in ["dataset_fields", "resource_fields"]:
            field_type = "dataset_fields"

        # Get the allowed values from the local schema
        allowed_values = [
            choice["value"]
            for field in self._local_schema[field_type]
            if field["field_name"] == field_name
            for choice in field.get("choices", [])
        ]
        return allowed_values

    def _set_basic_dates(self, package_dict):
        """
        Sets the basic dates for the package.

        Args:
            package_dict (dict): The package dictionary.

        Returns:
            None
        """
        issued_date = self._normalize_date(
            package_dict.get("issued"), self._source_date_format
        ) or datetime.now().strftime("%Y-%m-%d")

        for date_field in DATE_FIELDS:
            if date_field["override"]:
                field_name = date_field["field_name"]
                fallback = date_field["fallback"] or date_field["default_value"]

                fallback_date = (
                    issued_date
                    if fallback and fallback == "issued"
                    else self._normalize_date(package_dict.get(fallback), self._source_date_format)
                )

                package_dict[field_name] = (
                    self._normalize_date(package_dict.get(field_name), self._source_date_format) or fallback_date
                )

                if field_name == "issued":
                    package_dict["extras"].append(
                        {"key": "issued", "value": package_dict[field_name]}
                    )
                    
                # Update resource dates
                for resource in package_dict['resources']:
                    if resource.get(field_name) is not None:
                        self._normalize_date(resource.get(field_name), self._source_date_format) or fallback_date

    @staticmethod
    def _infer_format_from_url(url):
        """
        Infers the format and encoding of a file from its URL.

        This function sends a HEAD request to the URL and checks the 'content-type'
        header to determine the file's format and encoding. If the 'content-type'
        header is not found or an exception occurs, it falls back to guessing the
        format and encoding based on the URL's extension.

        Args:
            url (str): The URL of the file.

        Returns:
            tuple: A tuple containing the format, mimetype, and encoding of the file.

        Raises:
            Exception: If the 'content-type' header is not found in the response or if url is None.
        """
        if url is None or url == "":
            return None, None, None

        try:
            response = requests.head(url, allow_redirects=True)
            content_type = response.headers.get('content-type')
            if content_type:
                mimetype, *encoding = content_type.split(';')
                format = mimetype.split('/')[-1]
                encoding = encoding[0].split('charset=')[-1] if encoding and 'charset=' in encoding[0] else OGC2CKAN_HARVESTER_MD_CONFIG["encoding"]
            else:
                raise Exception("Content-Type header not found")
        except Exception:
            mimetype, encoding = mimetypes.guess_type(url)
            format = mimetype.split('/')[-1].upper() if mimetype else url.rsplit('.', 1)[-1]
            encoding = encoding or OGC2CKAN_HARVESTER_MD_CONFIG["encoding"]

        mimetype = f"{mimetype_base_uri}/{mimetype}" if mimetype else None

        return format, mimetype, encoding

    @staticmethod
    def _normalize_date(date, source_date_format=None):
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

    def _apply_package_defaults_from_config(self, package_dict, default_fields):
        """
        Applies default values from the configuration to the package dictionary.

        This function iterates over the default fields. If 'override' is True, it sets the value of the field in the package dictionary to the 'default_value'. If 'override' is False and the field does not exist in the package dictionary or its value is None, it sets the value of the field in the package dictionary to the 'default_value'. If the value of the field in the package dictionary is None and 'fallback' is not None, it sets the value of the field in the package dictionary to the 'fallback'.

        Args:
            package_dict (dict): The package dictionary to which default values are applied.
            default_fields (list): A list of dictionaries, each containing the field name, whether to override, the default value, and the fallback value.

        Returns:
            dict: The package dictionary with applied default values.
        """
        for field in default_fields:
            if field['override']:
                package_dict[field['field_name']] = field['default_value']
            elif field['field_name'] not in package_dict or package_dict[field['field_name']] in [None, '']:
                package_dict[field['field_name']] = field['default_value']
            elif package_dict[field['field_name']] in [None, ''] and field['fallback'] is not None:
                package_dict[field['field_name']] = field['fallback']

        return package_dict

    def create_default_values(self, field_mappings):
      """
      Creates default values for datasets and distributions based on the provided field mappings.

      This function processes the 'field_mappings' dictionary to extract default values for both
      dataset fields and distribution fields. It handles multilingual fields by extracting 'field_value'
      for each language specified under 'languages'. For non-multilingual fields, it directly extracts
      'field_value'. The extracted default values are stored in '_dataset_default_values' and
      '_distribution_default_values' attributes of the class.

      Parameters:
      - field_mappings (dict): A dictionary containing mappings for dataset and distribution fields.
        The expected keys are "dataset_field_mapping" and "distribution_field_mapping", each with
        a dictionary value that maps field names to their configurations, which may include 'languages'
        for multilingual fields and 'field_value' for default values.
      """
      def extract_default_values(field_mapping):
        default_values = {}
        for key, value in (field_mapping or {}).items():
          if isinstance(value, dict):
            if 'languages' in value:  # Handling multilingual fields
              default_values[key] = {lang: lang_details['field_value'] for lang, lang_details in value['languages'].items() if 'field_value' in lang_details}
            elif 'field_value' in value:  # Handling non-multilingual fields
              default_values[key] = value['field_value']
        return default_values

      # Create default values for dataset and distribution
      self._dataset_default_values = extract_default_values(field_mappings.get("dataset_field_mapping"))
      self._distribution_default_values = extract_default_values(field_mappings.get("distribution_field_mapping"))

      # Log if there are no default values
      if not self._dataset_default_values:
        log.info('No default values for dataset.')
      if not self._distribution_default_values:
        log.info('No default values for distribution.')

    def _update_package_dict_with_config_mapping_default_values(self, package_dict):
      """
      Updates the package dictionary with default values for dataset and distribution.

      This method iterates through the package dictionary, updating it with default values
      specified in `_dataset_default_values` and `_distribution_default_values`. For each
      key in the default values, if the key is not present in the target dictionary or its
      value is None, it updates the target dictionary with the default value. If the default
      value is a list, it extends the corresponding list in the target dictionary. If the
      default value is a dictionary, it recursively updates the target dictionary with the
      default dictionary values.

      Args:
        package_dict (dict): The package dictionary to update with default values.

      Returns:
        dict: The updated package dictionary.
      """         
      field_mappings = {
            'dataset_field_mapping': self._standardize_field_mapping(self.config.get("dataset_field_mapping")),
            'distribution_field_mapping': self._standardize_field_mapping(self.config.get("distribution_field_mapping")),
            'datadictionary_field_mapping': None
        }

      # Create default values dict from config mappings.
      try:
        self.create_default_values(field_mappings)
        
      except Exception as e:
        raise ReadError(
            "Error generating default values from config field mappings. Error: %s"
            % (str(e))
        )

      def update_dict_with_defaults(target_dict, default_values):
        for key, default_value in default_values.items():
          if key not in target_dict or target_dict[key] is None:
            target_dict[key] = default_value
          elif isinstance(target_dict[key], list) and isinstance(default_value, list):
            target_dict[key].extend(default_value)
            target_dict[key] = list(set(target_dict[key]))
          elif isinstance(default_value, dict):
            target_dict[key] = target_dict.get(key, {})
            for subkey, subvalue in default_value.items():
              if subkey not in target_dict[key] or target_dict[key][subkey] is None:
                target_dict[key][subkey] = subvalue

      if self._dataset_default_values and isinstance(self._dataset_default_values, dict):
        update_dict_with_defaults(package_dict, self._dataset_default_values)

      if self._distribution_default_values and isinstance(self._distribution_default_values, dict):
        for resource in package_dict.get("resources", []):
          if isinstance(resource, dict):
            update_dict_with_defaults(resource, self._distribution_default_values)

      return package_dict

    def _set_package_dict_default_values(self, package_dict, harvest_object, context):
        """
        Sets default values for the given package_dict based on the configuration.

        Args:
            package_dict (dict): The package_dict to set default values for.
            harvest_object (object): The harvest object associated with the package_dict.
            context (dict): The context for the action.

        Returns:
            dict: The package_dict with default values set.
        """
        # Add default values: tags, groups, etc.
        harvester_info = self.info()
        extras = {
            'harvester_name': harvester_info['name'],
        }

        # Check if the dataset is a harvest source and we are not allowed to harvest it
        if (
            package_dict.get("type") == "harvest"
            and self.config.get("allow_harvest_datasets", False) is False
        ):
            log.warning(
                "Remote dataset is a harvest source and allow_harvest_datasets is False, ignoring..."
            )
            return True

        # Local harvest source organization
        source_package_dict = p.toolkit.get_action("package_show")(
            context.copy(), {"id": harvest_object.source.id}
        )
        local_org = source_package_dict.get("owner_org")
        package_dict["owner_org"] = local_org
        
        if not package_dict.get("id") or package_dict.get("id") is None and package_dict.get("identifier"):
            package_dict["id"] = package_dict["identifier"]
        else:
            package_dict["id"] = str(uuid.uuid4())

        # Add default_extras from config
        default_extras = self.config.get('default_extras',{})
        if default_extras:
           override_extras = self.config.get('override_extras',False)
           for key,value in default_extras.items():
              #log.debug('Processing extra %s', key)
              if not key in extras or override_extras:
                 # Look for replacement strings
                 if isinstance(value,six.string_types):
                    value = value.format(
                            harvest_source_id=harvest_object.job.source.id,
                            harvest_source_url=harvest_object.job.source.url.strip('/'),
                            harvest_source_title=harvest_object.job.source.title,
                            harvest_job_id=harvest_object.job.id,
                            harvest_object_id=harvest_object.id,
                            dataset_id=package_dict["id"],)
                 extras[key] = value

        extras_as_dict = []
        for key, value in extras.items():
            if isinstance(value, (list, dict)):
                extras_as_dict.append({'key': key, 'value': json.dumps(value)})
            else:
                extras_as_dict.append({'key': key, 'value': value})

        package_dict['extras'] = extras_as_dict

        # Resources defaults
        if package_dict["resources"]:
            package_dict["resources"] = [
                self._update_resource_dict(resource)
                for resource in package_dict["resources"]
            ]

        # Using self._dataset_default_values and self._distribution_default_values based on config mappings
        package_dict = self._update_package_dict_with_config_mapping_default_values(package_dict)

        # Prepare tags        
        package_dict, existing_tags_ids = self._set_ckan_tags(package_dict, clean_tags=self.config.get("clean_tags", True))

        # Existing_tags_ids
        #log.debug('existing_tags_ids: %s', existing_tags_ids)
        
        # Set default tags if needed
        default_tags = self.config.get("default_tags", [])
        if default_tags:
            for tag in default_tags:
                if tag["name"] not in existing_tags_ids:
                    package_dict["tags"].append(tag)
                    existing_tags_ids.add(tag["name"])

        # Prepare groups
        cleaned_groups = self._set_ckan_groups(package_dict.get("groups", []))
        default_groups = self.config.get("default_groups", [])
        if default_groups:
            cleaned_default_groups = self._set_ckan_groups(default_groups)
            #log.debug("cleaned_default_groups: %s", cleaned_default_groups)
            existing_group_ids = set(g["name"] for g in cleaned_groups)
            for group in cleaned_default_groups:
                if group["name"] not in existing_group_ids:
                    cleaned_groups.append(group)

        package_dict["groups"] = cleaned_groups

        # Remove duplicates in list or dictionary fields
        for key, value in package_dict.items():
            if key not in ['groups', 'resources', 'tags']:
                if isinstance(value, list):
                    package_dict[key] = list({json.dumps(item): item for item in value}.values())
                elif isinstance(value, dict):
                    package_dict[key] = {k: v for k, v in value.items()}

        # Fallback: Using schemingdcat config defaults if no default values are set
        package_dict = self._apply_package_defaults_from_config(package_dict, DATASET_DEFAULT_FIELDS)

        # log.debug('package_dict default values: %s', package_dict)
        return package_dict

    def _update_resource_dict(self, resource):
        """
        Update the given resource dictionary with default values and normalize date fields.

        Args:
            resource (dict): The resource dictionary to be updated.

        Returns:
            dict: The updated resource dictionary in CKAN format.
        """
        for field in RESOURCE_DEFAULT_FIELDS:
            field_name = field["field_name"]
            fallback = field["fallback"] or field["default_value"]

            if field_name == "size" and field_name is not None:
                if "size" in resource and isinstance(resource["size"], str):
                    resource["size"] = resource["size"].replace(".", "")
                    resource["size"] = (
                        int(resource["size"]) if resource["size"].isdigit() else 0
                    )

            if field_name not in resource or resource[field_name] is None:
                resource[field_name] = fallback

        for field in DATE_FIELDS:
            if field["override"]:
                field_name = field["field_name"]
                if field_name in resource and resource[field_name]:
                    resource[field_name] = self._normalize_date(resource[field_name], self._source_date_format)

        return self._get_ckan_format(resource)

    def _set_ckan_tags(self, package_dict, tag_fields=AUX_TAG_FIELDS, clean_tags=True):
        """
        Process the tags from the provided sources.

        Args:
            package_dict (dict): The package dictionary containing the information.
            tag_fields (list): The list of sources to check for tags. Default: ['tag_string', 'keywords']
            clean_tags (bool): By default, tags are stripped of accent characters, spaces and capital letters for display. Setting this option to `False` will keep the original tag names. Default is `True`.

        Returns:
            list: A list of processed tags.
        """
        if "tags" not in package_dict:
            package_dict["tags"] = []

        existing_tags_ids = set(t["name"] for t in package_dict["tags"])

        for source in tag_fields:
            if source in package_dict:
                tags = package_dict.get(source, [])
                if isinstance(tags, dict):
                    tags = tags
                elif isinstance(tags, list):
                    tags = [{"name": tag} for tag in tags]
                elif isinstance(tags, str):
                    tags = [{"name": tags}]
                else:
                    raise ValueError("Unsupported type for tags")
                
                # Clean tags
                cleaned_tags = self._clean_tags(tags=tags, clean_tag_names=clean_tags, existing_dataset=True)

                for tag in cleaned_tags:
                    if tag["name"] not in existing_tags_ids:
                        package_dict["tags"].append(tag)
                        existing_tags_ids.add(tag["name"])

        # Remove tag_fields from package_dict
        for field in tag_fields:
            package_dict.pop(field, None)

        return package_dict, existing_tags_ids

    @staticmethod
    def _set_ckan_groups(groups):
        """
        Sets the CKAN groups based on the provided package dictionary.

        Args:
            groups (list): The package dictionary containing the information.

        Returns:
            list: A list of CKAN groups.

        """
        # Normalize groups for CKAN
        if isinstance(groups, str):
            # If groups is a string, split it into a list
            groups = groups.split(",")
        elif isinstance(groups, list):
            # If groups is a list of dictionaries, extract 'name' from each dictionary
            if all(isinstance(item, dict) for item in groups):
                groups = [group.get('name', '') for group in groups]
            # If groups is a list but not of dictionaries, keep it as it is
        else:
            # If groups is neither a list nor a string, return an empty list
            return []

        # Create ckan_groups
        ckan_groups = [{"name": g.lower().replace(" ", "-").strip()} for g in groups]

        return ckan_groups

    @staticmethod
    def _update_custom_format(res_format, mimetype=None, url=None, **args):
      """Update of the custom format based on custom rules.

      This optimized version pre-processes the rules to lower case outside the main loop to enhance efficiency.
      It checks the format and URL against a set of custom rules (CUSTOM_FORMAT_RULES). If a rule matches,
      the format is updated accordingly. This function is designed for easy extension with new rules.

      Args:
        res_format (str): The custom format to update.
        mimetype (str, optional): The source mimetype.
        url (str, optional): The URL to check. Defaults to None.
        **args: Additional arguments that are ignored.

      Returns:
        tuple: A tuple containing the updated custom format as a string and the MIME type as a string or None.
      """
      if not res_format:
          return ("", None)  # Return a default tuple if format is None or empty

      res_format_lower = res_format.lower()
      url_lower = url.lower() if url is not None else ""

      preprocessed_rules = [
          {
              "format_strings_lower": [s.lower() for s in rule["format_strings"]] if rule["format_strings"] is not None else None,
              "url_string_lower": rule["url_string"].lower() if rule["url_string"] is not None else None,
              "format": rule["format"].upper(),
              "mimetype": rule['mimetype'].strip()
          }
          for rule in CUSTOM_FORMAT_RULES
      ]

      for rule in preprocessed_rules:
          if rule["format_strings_lower"] and any(s in res_format_lower for s in rule["format_strings_lower"]):
              return rule["format"], rule['mimetype']
          elif rule["url_string_lower"] and rule["url_string_lower"] in url_lower:
              return rule["format"], rule['mimetype']

      return res_format, mimetype  # Ensure a tuple is returned

    @staticmethod
    def _secret_properties(input_dict, secrets=None):
        """
        Obfuscates specified properties of a dict, returning a copy with the obfuscated values.

        Args:
            input_dict (dict): The dictionary whose properties are to be obfuscated.
            secrets (list, optional): List of properties that should be obfuscated. If None, a default list will be used.

        Returns:
            dict: A copy of the original dictionary with the specified properties obfuscated.
        """
        # Default properties to be obfuscated if no specific list is provided
        secrets = secrets or ['password', 'secret', 'credentials', 'private_key']
        default_secret_value = '****'

        # Use dictionary comprehension to create a copy and obfuscate in one step
        return {key: (default_secret_value if key in secrets else value) for key, value in input_dict.items()}

    def _get_ckan_format(self, resource):
        """Get the CKAN format information for a distribution.

        Args:
            resource (dict): A dictionary containing information about the distribution.

        Returns:
            dict: The updated distribution information.
        """

        encoding = "UTF-8"

        informat = resource.get("format", "").lower() if isinstance(resource.get("format"), str) else None

        if informat is None:
            informat = "".join(
                str(value)
                for key, value in resource.items()
                if key in ["title", "url", "description"] and isinstance(value, str)
            ).lower()
            informat = next(
                (key for key in OGC2CKAN_MD_FORMATS if key.lower() in informat),
                None,
            )

        format, mimetype = (informat, OGC2CKAN_MD_FORMATS[informat][1]) if informat in OGC2CKAN_MD_FORMATS else (informat, None)

        if format is None or format == "":
            format, mimetype, encoding = self._infer_format_from_url(resource.get('url'))

        format, mimetype = self._update_custom_format(format, mimetype, resource.get("url", "")) if format else ("", None)

        resource['format'] = format if format else resource.get('format', None)
        resource['mimetype'] = mimetype if mimetype else resource.get('mimetype', None)
        resource['encoding'] = encoding if encoding else resource.get('encoding', None)

        #log.debug('resource: %s', resource)
        return resource

    def _clean_tags(self, tags, clean_tag_names=True, existing_dataset=False):
        """
        Cleans the names of tags.
    
        Each keyword is cleaned by removing non-alphanumeric characters,
        allowing only: a-z, ñ, 0-9, _, -, ., and spaces, and truncating to a
        maximum length of 100 characters. If the name of the keyword is a URL,
        it is converted into a standard CKAN name using the _url_to_ckan_name function.
    
        Args:
            tags (list): The tags to be cleaned. Each keyword is a dictionary with a `name` key.
    
            clean_tag_names (bool): By default, tags are stripped of accent characters, spaces and capital letters for display. Setting this harvester config option `clean_tags` to `False` will keep the original tag names. Default is `True`.
    
            existing_dataset (bool): If the tags are from a dataset from the local CKAN instance.
    
        Returns:
            list: A list of dictionaries with cleaned keyword names.
        """
        cleaned_tags = []
        seen_names = set()
    
        for k in tags:
            if k and "name" in k:
                name = k["name"]
                vocabulary_id = k.get("vocabulary_id") or None
                if self._is_url(name):
                    name = self._url_to_ckan_name(name)
    
                normalized_name = self._clean_name(name)
    
                if normalized_name in seen_names:
                    continue
    
                seen_names.add(normalized_name)
    
                tag = {
                    "name": normalized_name if clean_tag_names else name,
                    "display_name": k["name"]
                }
    
                if vocabulary_id and existing_dataset:
                    tag["vocabulary_id"] = vocabulary_id
    
                cleaned_tags.append(tag)

        return cleaned_tags

    def _is_url(self, name):
        """
        Checks if a string is a valid URL.

        Args:
            name (str): The string to check.

        Returns:
            bool: True if the string is a valid URL, False otherwise.
        """
        return bool(URL_REGEX.match(name))

    def _url_to_ckan_name(self, url):
        """
        Converts a URL into a standard CKAN name.

        This function extracts the path from the URL, removes leading and trailing slashes,
        replaces other slashes with hyphens, and cleans the name using the _clean_name function.

        Args:
            url (str): The URL to convert.

        Returns:
            str: The standard CKAN name.
        """
        path = urlparse(url).path
        name = path.strip('/')
        name = name.replace('/', '-')
        return self._clean_name(name)

    def _clean_name(self, name):
        """
        Cleans a name by removing accents, special characters, and spaces.

        Args:
            name (str): The name to clean.

        Returns:
            str: The cleaned name.
        """
        # Convert the name to lowercase
        name = name.lower()

        # Replace accented and special characters with their unaccented equivalents or -
        name = name.translate(ACCENT_MAP)
        name = INVALID_CHARS.sub("-", name.strip())

        # Truncate the name to 40 characters
        name = name[:40]

        return name

    def _fill_translated_properties(self, package_dict):
        """
        Fills properties without the _translated suffix using the default language or the first available translation.
    
        Args:
            package_dict (dict): The package dictionary to be modified.
            default_language (str): The default language of the instance.
    
        Returns:
            dict: The modified package dictionary.
        """
        default_lang = self._get_local_required_lang()
        
        for key in list(package_dict.keys()):
            if key.endswith('_translated'):
                base_key = key[:-11]  # Remove '_translated' suffix
                translations = package_dict[key]
    
                # Use the default language if available
                if default_lang and default_lang in translations:
                    package_dict[base_key] = translations[default_lang]
                else:
                    # Use the first available translation with a value
                    for lang, value in translations.items():
                        if value:
                            package_dict[base_key] = value
                            break
    
        return package_dict

    def _create_or_update_package(
        self, package_dict, harvest_object, package_dict_form="rest"
    ):
        """
        Creates a new package or updates an existing one according to the
        package dictionary provided.

        The package dictionary can be in one of two forms:

        1. 'rest' - as seen on the RESTful API:

                http://datahub.io/api/rest/dataset/1996_population_census_data_canada

           This is the legacy form. It is the default to provide backward
           compatibility.

           * 'extras' is a dict e.g. {'theme': 'health', 'sub-theme': 'cancer'}
           * 'tags' is a list of strings e.g. ['large-river', 'flood']

        2. 'package_show' form, as provided by the Action API (CKAN v2.0+):

               http://datahub.io/api/action/package_show?id=1996_population_census_data_canada

           * 'extras' is a list of dicts
                e.g. [{'key': 'theme', 'value': 'health'},
                        {'key': 'sub-theme', 'value': 'cancer'}]
           * 'tags' is a list of dicts
                e.g. [{'name': 'large-river'}, {'name': 'flood'}]

        Note that the package_dict must contain an id, which will be used to
        check if the package needs to be created or updated (use the remote
        dataset id).

        If the remote server provides the modification date of the remote
        package, add it to package_dict['metadata_modified'].

        :returns: The same as what import_stage should return. i.e. True if the
                  create or update occurred ok, 'unchanged' if it didn't need
                  updating or False if there were errors.
        """
        assert package_dict_form in ("rest", "package_show")
        try:
            if package_dict is None:
                pass

            # Change default schema
            schema = default_create_package_schema()
            schema["id"] = [ignore_missing, unicode_safe]
            schema["__junk"] = [ignore]

            # Check API version
            if self.config:
                try:
                    api_version = int(self.config.get("api_version", 2))
                except ValueError:
                    raise ValueError("api_version must be an integer")
            else:
                api_version = 2

            user_name = self._get_user_name()
            context = {
                "model": model,
                "session": Session,
                "user": user_name,
                "api_version": api_version,
                "schema": schema,
                "ignore_auth": True,
            }

            if self.config and self.config.get("clean_tags", True):
                tags = package_dict.get("tags", [])
                package_dict["tags"] = self._clean_tags(tags)

            # Check if package exists. Can be overridden if necessary
            #existing_package_dict = self._check_existing_package_by_ids(package_dict)
            existing_package_dict = None

            # Flag this object as the current one
            harvest_object.current = True
            harvest_object.add()

            if existing_package_dict is not None:
                package_dict["id"] = existing_package_dict["id"]
                log.debug(
                    "existing_package_dict title: %s and ID: %s",
                    existing_package_dict["title"],
                    existing_package_dict["id"],
                )

                # In case name has been modified when first importing. See issue #101.
                package_dict["name"] = existing_package_dict["name"]

                # Check modified date
                if "metadata_modified" not in package_dict or package_dict[
                    "metadata_modified"
                ] > existing_package_dict.get("metadata_modified"):
                    log.info(
                        "Package ID: %s with GUID: %s exists and needs to be updated",
                        package_dict["id"],
                        harvest_object.guid,
                    )
                    # Update package
                    context.update({"id": package_dict["id"]})

                    # Map existing resource URLs to their resources
                    existing_resources = {
                        resource["url"]: resource["modified"]
                        for resource in existing_package_dict.get("resources", [])
                        if "modified" in resource
                    }

                    new_resources = existing_package_dict.get("resources", []).copy()
                    for resource in package_dict.get("resources", []):
                        # If the resource URL is in existing_resources and the resource's
                        # modification date is more recent, update the resource in new_resources
                        if (
                            "url" in resource
                            and resource["url"] in existing_resources
                            and "modified" in resource
                            and parse(resource["modified"]) > parse(existing_resources[resource["url"]])
                        ):
                            log.info('Resource dates - Harvest date: %s and Previous date: %s', resource["modified"], existing_resources[resource["url"]])

                            # Find the index of the existing resource in new_resources
                            index = next(i for i, r in enumerate(new_resources) if r["url"] == resource["url"])
                            # Replace the existing resource with the new resource
                            new_resources[index] = resource
                        # If the resource URL is not in existing_resources, add the resource to new_resources
                        elif "url" in resource and resource["url"] not in existing_resources:
                            new_resources.append(resource)
                            
                        if resource["url"] is None or resource["url"] == "" or "url" not in resource:
                            self._save_object_error(
                                "Warning: Resource URL is None. Add it!",
                                harvest_object,
                                "Import",
                            )

                    package_dict["resources"] = new_resources

                    # Clean tags before update existing dataset
                    tags = package_dict.get("tags", [])

                    if hasattr(self, 'config') and self.config:
                        package_dict["tags"] = self._clean_tags(tags=tags, clean_tag_names=self.config.get("clean_tags", True), existing_dataset=False)
                    else:
                        package_dict["tags"] = self._clean_tags(tags=tags, clean_tag_names=True, existing_dataset=True)

                    # Remove tag_fields from package_dict
                    for field in AUX_TAG_FIELDS:
                        package_dict.pop(field, None)

                    for field in p.toolkit.aslist(
                        config.get("ckan.harvest.not_overwrite_fields")
                    ):
                        if field in existing_package_dict:
                            package_dict[field] = existing_package_dict[field]
                    try:
                        updated_package = p.toolkit.get_action("package_update")(
                            context, package_dict
                        )
                        log.info(
                            "Updated package: %s with GUID: %s",
                            updated_package["name"],
                            harvest_object.guid,
                        )
                        
                        schemingdcat_harvest_package_updated.send(self, package_id=updated_package["name"], harvest_object_id=harvest_object.guid)
                        
                    except p.toolkit.ValidationError as e:
                        error_message = ", ".join(
                            f"{k}: {v}" for k, v in e.error_dict.items()
                        )
                        self._save_object_error(
                            f"Validation Error: {error_message}",
                            harvest_object,
                            "Import",
                        )
                        return False

                else:
                    log.info(
                        "No changes to package with GUID: %s, skipping..."
                        % harvest_object.guid
                    )
                    # NB harvest_object.current/package_id are not set
                    return "unchanged"

                # Flag this as the current harvest object
                harvest_object.package_id = package_dict["id"]
                harvest_object.save()

            else:
                # Package needs to be created
                package_dict["id"] = package_dict["identifier"]

                # Get rid of auth audit on the context otherwise we'll get an
                # exception
                context.pop("__auth_audit", None)

                # Set name for new package to prevent name conflict, see issue #117
                if package_dict.get("name", None):
                    package_dict["name"] = self._gen_new_name(package_dict["name"])
                else:
                    package_dict["name"] = self._gen_new_name(package_dict["title"])

                for resource in package_dict.get("resources", []):
                    if resource["url"] is None or resource["url"] == "" or "url" not in resource:
                        self._save_object_error(
                            "Warning: Resource URL is None. Add it!",
                            harvest_object,
                            "Import",
                        )

                # Clean tags before create. Not existing_dataset 
                tags = package_dict.get("tags", [])

                if hasattr(self, 'config') and self.config:
                    package_dict["tags"] = self._clean_tags(tags=tags, clean_tag_names=self.config.get("clean_tags", True), existing_dataset=False)
                else:
                    package_dict["tags"] = self._clean_tags(tags=tags, clean_tag_names=True, existing_dataset=False)

                # Remove tag_fields from package_dict
                for field in AUX_TAG_FIELDS:
                    package_dict.pop(field, None)

                #log.debug('Package: %s', package_dict)
                harvest_object.package_id = package_dict["id"]
                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                harvest_object.add()

                model.Session.execute(
                    "SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED"
                )
                model.Session.flush()

                try:
                    new_package = p.toolkit.get_action("package_create")(
                        context, package_dict
                    )
                    log.info(
                        "Created new package: %s with GUID: %s",
                        new_package["name"],
                        harvest_object.guid,
                    )
                    
                    schemingdcat_harvest_package_created.send(self, package_id=new_package["name"], harvest_object_id=harvest_object.guid)
                    
                except p.toolkit.ValidationError as e:
                    error_message = ", ".join(
                        f"{k}: {v}" for k, v in e.error_dict.items()
                    )
                    self._save_object_error(
                        f"Validation Error: {error_message}", harvest_object, "Import"
                    )
                    return False

            Session.commit()

            return True

        except p.toolkit.ValidationError as e:
            log.exception(e)
            self._save_object_error(
                "Invalid package with GUID: %s: %r"
                % (harvest_object.guid, e.error_dict),
                harvest_object,
                "Import",
            )
        except Exception as e:
            log.exception(e)
            self._save_object_error("%r" % e, harvest_object, "Import")

        return None

    @staticmethod
    def log_export_to_csv(data, harvest_source_title, filename_suf, log_dir='harvester-log', fieldnames=None):
        """
        Export data to a CSV file for logging, with filenames based on the harvest source title and current timestamp.
        The files are saved in a 'log' directory.

        Args:
            data (list): A list of dictionaries (for clean_datasets) or a list of values (for object_ids).
            harvest_source_title (str): The title of the harvest source to be included in the filename.
            filename_suf (str): Suffix for the filename indicating the type of data (e.g., 'clean_datasets', 'ids').
            log_dir (str, optional): Dir to ouput files.
            fieldnames (list, optional): List of keys to write as the first row if data is a list of dictionaries. If None, it will use the keys of the first dictionary in data.
        """
        # Normalize the harvest source title: replace spaces with _, and convert to lowercase
        normalized_title = harvest_source_title.replace(" ", "_").lower()

        # Get the current date and time in string format
        now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        # Format the filename with the normalized title and the current date/time
        filename = f"{normalized_title}_{now}_{filename_suf}.csv"

        # Ensure the log_dir exists
        os.makedirs(log_dir, exist_ok=True)

        # Combine the directory with the filename
        filepath = os.path.join(log_dir, filename)

        # Export logic remains the same
        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
                if all(isinstance(item, dict) for item in data):
                    # Data is a list of dictionaries
                    if fieldnames is None:
                        fieldnames = data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for item in data:
                        # Filter each item to include only the keys in fieldnames
                        filtered_item = {key: item[key] for key in fieldnames if key in item}
                        writer.writerow(filtered_item)
                else:
                    # Data is a simple list
                    writer = csv.writer(csvfile)
                    for item in data:
                        writer.writerow([item])
        except Exception as e:
            raise RuntimeError(f"Failed to export data to CSV: {e}")

    def _log_export_clean_datasets_and_ids(self, harvest_source_title, clean_datasets, ids):
        """
        Logs and exports clean datasets and object IDs to CSV files.

        This method exports two sets of data: 'clean_datasets' and 'ids'. Each set is exported to a separate CSV file
        named with the harvest source title and the type of data. The 'clean_datasets' export includes all fields from
        the dataset, while the 'ids' export is limited to 'id', 'name', and 'identifier'.

        Args:
            harvest_source_title (str): The title of the harvest source, used in naming the export files.
            clean_datasets (list of dict): A list of dictionaries, each representing a clean dataset to be logged.
            ids (list of dict): A list of dictionaries, each representing an object ID to be logged.

        """
        # Log clean_datasets/ ids
        log_dir = 'harvester-log'
        # Export clean_datasets
        fieldnames = clean_datasets[0].keys() if clean_datasets else []
        self.log_export_to_csv(clean_datasets, harvest_source_title, 'clean_datasets', log_dir, fieldnames=fieldnames)

        # Export object_ids
        fieldnames_ids = ['name', 'identifier']
        self.log_export_to_csv(ids, harvest_source_title, 'ids', log_dir, fieldnames=fieldnames_ids)
        
        log.debug('"clean_datasets" and "ids" files logging in %s', log_dir)

class ContentFetchError(Exception):
    pass

class ContentNotFoundError(ContentFetchError):
    pass

class RemoteResourceError(Exception):
    pass

class SearchError(Exception):
    pass

class ReadError(Exception):
    pass

class RemoteSchemaError(Exception):
    pass
