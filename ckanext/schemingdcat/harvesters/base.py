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
import pandas as pd

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

from ckanext.schemingdcat.config import (
    OGC2CKAN_HARVESTER_MD_CONFIG,
    OGC2CKAN_MD_FORMATS,
    DATE_FIELDS,
    DATASET_DEFAULT_FIELDS,
    RESOURCE_DEFAULT_FIELDS,
    CUSTOM_FORMAT_RULES,
    DATADICTIONARY_DEFAULT_SCHEMA,
    URL_REGEX,
    INVALID_CHARS,
    ACCENT_MAP
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
    _supported_schemas = []
    _readme = "https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file"
    config = None
    api_version = 2
    action_api_version = 3
    force_import = False
    _site_user = None
    _source_date_format = None
    _dataset_default_values = {}
    _distribution_default_values = {}
    _field_mapping_validator = FieldMappingValidator()
    _field_mapping_validator_versions = _field_mapping_validator.validators.keys()

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

    @lru_cache(maxsize=None)
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
            dict: The remote schema as a dictionary.

        Raises:
            HarvesterBase.ContentFetchError: If there is an error fetching the remote schema content.
            ValueError: If there is an error decoding the remote schema content.
            KeyError: If the remote schema content does not contain the expected result.

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
            return content_dict["result"]
        except (HarvesterBase.ContentFetchError, ValueError, KeyError):
            log.debug("Could not fetch/decode remote schema")
            raise HarvesterBase.RemoteResourceError(
                "Could not fetch/decode remote schema"
            )

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
        self._supported_schemas.append(self._local_schema_name)

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
                log.debug('standardized_mapping: %s', standardized_mapping)
        return standardized_mapping

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
                        log.debug('standarize value: %s', value['field_position'])
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
                        log.debug('standarize value: %s', value['field_name'])
                        # Apply the function to each row in the dataframe
                        df[key] = df.apply(lambda row: merge_values(row, value['field_name']), axis=1)
                        log.debug('df[key]: %s', df[key])
                        # Drop the original value columns
                        for field in value['field_name']:
                            df.drop(field, axis=1, inplace=True)
                    else:
                        rename_and_update(df, value['field_name'], key, value)
                elif isinstance(value, dict) and 'languages' in value:
                    for lang, lang_value in value['languages'].items():
                        if 'field_position' in lang_value:
                            rename_and_update(df, lang_value['field_position'], f"{key}-{lang}", lang_value)
                        elif 'field_name' in lang_value:
                            rename_and_update(df, lang_value['field_name'], f"{key}-{lang}", lang_value)
                        # translated_fields only str

        # Calculate the difference between the DataFrame columns and the field_mapping keys
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
        remote_resource_field_mapping=None,
    ):
        """
        Validates the remote schema by comparing it with the local schema.

        Args:
            remote_ckan_base_url (str, optional): The base URL of the remote CKAN instance. If provided, the remote schema will be fetched from this URL.
            remote_dataset_field_names (set, optional): The field names of the remote dataset schema. If provided, the remote schema will be validated using these field names.
            remote_resource_field_names (set, optional): The field names of the remote resource schema. If provided, the remote schema will be validated using these field names.
            remote_dataset_field_mapping (dict, optional): A mapping of local dataset field names to remote dataset field names. If provided, the local dataset fields will be mapped to the corresponding remote dataset fields.
            remote_resource_field_mapping (dict, optional): A mapping of local resource field names to remote resource field names. If provided, the local resource fields will be mapped to the corresponding remote resource fields.

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

                remote_datasets_colnames = set(
                    field["field_name"]
                    for field in self._remote_schema["dataset_fields"]
                )
                remote_distributions_colnames = set(
                    field["field_name"]
                    for field in self._remote_schema["resource_fields"]
                )

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

            def get_mapped_fields(fields, field_mapping):
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

            self._mapped_schema = {
                "dataset_fields": get_mapped_fields(
                    self._local_schema.get("dataset_fields", []),
                    remote_dataset_field_mapping,
                ),
                "resource_fields": get_mapped_fields(
                    self._local_schema.get("resource_fields", []),
                    remote_resource_field_mapping,
                ),
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

    def _check_url(self, url, harvest_job, auth=False):
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
        basic_fields = [
            "id",
            "name",
            "title",
            "title_translated",
            "notes_translated",
            "provenance",
            "notes",
            "provenance",
            "private",
            "groups",
            "tags",
            "tag_string",
            "owner_org",
        ]
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

                    translated_fields["dataset_fields"].append(
                        local_field_name
                    )

                    if isinstance(remote_field_name, dict):
                        package_dict[local_field_name] = {
                            lang: package_dict.get(name, None)
                            for lang, name in remote_field_name.items()
                        }
                        if local_field_name.endswith('_translated'):
                            if self._local_required_lang in remote_field_name:
                                package_dict[local_field_name.replace('_translated', '')] = package_dict.get(remote_field_name[self._local_required_lang], None)
                            else:
                                raise ValueError("Missing translated field: %s for required language: %s" % (remote_field_name, self._local_required_lang))
                    else:
                        if remote_field_name not in package_dict:
                            raise KeyError(f"Field {remote_field_name} does not exist in the local schema")
                        package_dict[local_field_name] = package_dict.get(remote_field_name, None)

            if package_dict["resources"]:
                for i, resource in enumerate(package_dict["resources"]):
                    for field in self._mapped_schema["resource_fields"]:
                        if field.get("modified", True):
                            local_field_name = field["local_field_name"]
                            remote_field_name = field["remote_field_name"]

                            translated_fields["resource_fields"].append(
                                local_field_name
                            )

                            if isinstance(remote_field_name, dict):
                                package_dict[local_field_name] = {
                                    lang: package_dict.get(name, None)
                                    for lang, name in remote_field_name.items()
                                }
                                if local_field_name.endswith('_translated'):
                                    if self._local_required_lang in remote_field_name:
                                        package_dict[local_field_name.replace('_translated', '')] = package_dict.get(remote_field_name[self._local_required_lang], None)
                                    else:
                                        raise ValueError("Missing translated field: %s for required language: %s" % (remote_field_name, self._local_required_lang))

                    # Update the resource in package_dict
                    package_dict["resources"][i] = resource

            log.debug('Translated fields: %s', translated_fields)

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
            Exception: If the 'content-type' header is not found in the response.
        """
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
            format = mimetype.split('/')[-1] if mimetype else url.rsplit('.', 1)[-1]
            encoding = encoding or OGC2CKAN_HARVESTER_MD_CONFIG["encoding"]

        mimetype = f"http://www.iana.org/assignments/media-types/{mimetype}" if mimetype else None

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
                log.error('normalize_date failed')
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
            elif field['field_name'] not in package_dict or package_dict[field['field_name']] is None:
                package_dict[field['field_name']] = field['default_value']
            elif package_dict[field['field_name']] is None and field['fallback'] is not None:
                package_dict[field['field_name']] = field['fallback']
        return package_dict

    def _update_package_dict_with_config_mapping_default_values(self, package_dict):
        """
        Update the package dictionary with default values.

        This method updates the package dictionary with default values from
        `self._dataset_default_values` and `self._distribution_default_values` (config property: *_field_mapping).
        If a key from the default values does not exist in the package dictionary,
        it is added with its corresponding default value. The same process is applied
        to each resource in `package_dict["resources"]` with `self._distribution_default_values`.
        If the value in the package dictionary is a list and the default value is also a list,
        the default values are appended to the list in the package dictionary.

        Args:
            package_dict (dict): The package dictionary to be updated.

        Returns:
            dict: The updated package dictionary.
        """
        if self._dataset_default_values and isinstance(self._dataset_default_values, dict):
            for key, value in self._dataset_default_values.items():
                if key not in package_dict:
                    package_dict[key] = value
                elif isinstance(package_dict[key], list) and isinstance(value, list):
                    package_dict[key].extend(value)

        if self._distribution_default_values and isinstance(self._distribution_default_values, dict):
            for i in range(len(package_dict["resources"])):
                for key, value in self._distribution_default_values.items():
                    if key not in package_dict["resources"][i]:
                        package_dict["resources"][i][key] = value
                    elif isinstance(package_dict["resources"][i][key], list) and isinstance(value, list):
                        package_dict["resources"][i][key].extend(value)

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
        package_dict, existing_tags_ids = self._set_ckan_tags(package_dict)

        harvester_info = self.info()
        extras = {
            'harvester_name': harvester_info['name'],
        }

        # Check if the dataset is a harvest source and we are not allowed to harvest it
        if (
            package_dict.get("type") == "harvest"
            and self.config.get("allow_harvest_datasets", False) is False
        ):
            log.warn(
                "Remote dataset is a harvest source and allow_harvest_datasets is False, ignoring..."
            )
            return True

        #TODO: Fix existing_tags_ids
        log.debug('TODO:existing_tags_ids: %s', existing_tags_ids)
        
        # Set default tags if needed
        default_tags = self.config.get("default_tags", [])
        if default_tags:
            for tag in default_tags:
                if tag["name"] not in existing_tags_ids:
                    package_dict["tags"].append(tag)
                    existing_tags_ids.add(tag["name"])

        # Local harvest source organization
        source_package_dict = p.toolkit.get_action("package_show")(
            context.copy(), {"id": harvest_object.source.id}
        )
        local_org = source_package_dict.get("owner_org")
        package_dict["owner_org"] = local_org

        # Using dataset config defaults
        package_dict = self._apply_package_defaults_from_config(package_dict, DATASET_DEFAULT_FIELDS)

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

        # Add default_extras from config
        default_extras = self.config.get('default_extras',{})
        if default_extras:
           override_extras = self.config.get('override_extras',False)
           for key,value in default_extras.items():
              log.debug('Processing extra %s', key)
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

    def _set_ckan_tags(self, package_dict, tag_fields=["tag_string", "keywords"]):
        """
        Process the tags from the provided sources.

        Args:
            package_dict (dict): The package dictionary containing the information.
            tag_fields (list): The list of sources to check for tags. Default: ['tag_string', 'keywords']

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
                cleaned_tags = self._clean_tags(tags)

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
    def _update_custom_format(res_format, url=None, **args):
        """Update the custom format based on custom rules.

        The function checks the format and URL against a set of custom rules (CUSTOM_FORMAT_RULES). If a rule matches,
        the format is updated according to that rule. This function is designed to be easily
        extendable with new rules.

        Args:
            res_format (str): The custom format to update.
            url (str, optional): The URL to check. Defaults to None.
            **args: Additional arguments that are ignored.

        Returns:
            str: The updated custom format.
        """
        for rule in CUSTOM_FORMAT_RULES:
            if (
                any(string in res_format for string in rule["format_strings"])
                or rule["url_string"] in url
            ):
                res_format = rule["new_format"]
                break

        return res_format.upper()

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

        if isinstance(resource["format"], str):
            informat = resource["format"].lower()
        else:
            informat = "".join(
                str(value)
                for key, value in resource.items()
                if key in ["title", "url", "description"] and isinstance(value, str)
            ).lower()
            informat = next(
                (key for key in OGC2CKAN_MD_FORMATS if key.lower() in informat),
                None,  # Changed this line to return None instead of the URL
            )

        # Check if _update_custom_format
        informat = self._update_custom_format(informat.lower() if informat else "", resource.get("url", ""))

        if informat is not None:
            resource["format"] = informat
        else:
            format, mimetype, encoding = self._infer_format_from_url(resource.get('url'))

            resource['format'] = format if format else resource.get('format', '')
            resource['mimetype'] = mimetype if mimetype else resource.get('mimetype', '')
            resource['encoding'] = encoding if encoding else resource.get('encoding', '')

        return resource

    def _clean_tags(self, tags):
        """
        Cleans the names of tags.

        Each keyword is cleaned by removing non-alphanumeric characters,
        allowing only: a-z, ñ, 0-9, _, -, ., and spaces, and truncating to a
        maximum length of 100 characters. If the name of the keyword is a URL,
        it is converted into a standard CKAN name using the _url_to_ckan_name function.

        Args:
            tags (list): The tags to be cleaned. Each keyword is a
            dictionary with a 'name' key.

        Returns:
            list: A list of dictionaries with cleaned keyword names.
        """
        cleaned_tags = []
        for k in tags:
            if k and "name" in k:
                name = k["name"]
                if self._is_url(name):
                    name = self._url_to_ckan_name(name)
                cleaned_tags.append({"name": self._clean_name(name), "display_name": k["name"]})
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

                    package_dict["resources"] = new_resources

                    for field in p.toolkit.aslist(
                        config.get("ckan.harvest.not_overwrite_fields")
                    ):
                        if field in existing_package_dict:
                            package_dict[field] = existing_package_dict[field]
                    try:
                        package_id = p.toolkit.get_action("package_update")(
                            context, package_dict
                        )
                        log.info(
                            "Updated package: %s with GUID: %s",
                            package_id,
                            harvest_object.guid,
                        )
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

                log.info(
                    "Created new package ID: %s with GUID: %s",
                    package_dict["id"],
                    harvest_object.guid,
                )

                # log.debug('Package: %s', package_dict)
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

    def _create_or_update_pkg(self, package_dict, harvest_object):
        print(True)


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
