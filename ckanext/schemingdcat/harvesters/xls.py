from builtins import str
import json
import logging
import re
import uuid
import base64
import traceback
import six
import dateutil

import gspread
import pandas as pd

from ckan.logic import NotFound, get_action
from ckan import logic
import ckan.plugins as p
import ckan.model as model

from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
from ckanext.schemingdcat.harvesters.base import SchemingDCATHarvester, RemoteResourceError, ReadError, RemoteSchemaError
from ckanext.schemingdcat.interfaces import ISchemingDCATHarvester
from ckanext.schemingdcat.lib.field_mapping import FieldMappingValidator

from ckanext.schemingdcat.config import (
    COMMON_DATE_FORMATS,
    XLS_HARVESTER_FIELDS_NOT_LIST
)
from ckanext.schemingdcat.helpers import schemingdcat_get_dataset_schema_field_names

log = logging.getLogger(__name__)


class SchemingDCATXLSHarvester(SchemingDCATHarvester):
    """
    """

    def info(self):
        return {
            'name': 'schemingdcat_xls',
            'title': 'Remote Google Sheet/Onedrive Excel metadata upload Harvester',
            'description': 'A harvester for remote sheets files with Metadata records. Google Sheets or Onedrive Excel files.',
            'about_url': 'https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#remote-google-sheetonedrive-excel-metadata-upload-harvester'
        }

    _storage_types_supported = {
        'gspread': {
            'name': 'gspread',
            'title': 'Google Sheets',
            'active': True
        },
        'onedrive': {
            'name': 'onedrive',
            'title': 'OneDrive',
            'active': True
        },
        'gdrive': {
            'name': 'gdrive',
            'title': 'Google Drive',
            'active': False
        }
    }
    
    _storage_type = None
    _auth = False
    _credentials = None
    _names_taken = []

    def _set_config_credentials(self, storage_type, config_obj):
        """
        Set the credentials based on the storage type and configuration object.

        Args:
            storage_type (str): The type of storage (e.g., 'onedrive', 'gspread', 'gdrive').
            config_obj (dict): The configuration object containing the credentials.

        Returns:
            dict: The credentials dictionary.

        Raises:
            ValueError: If the credentials are not provided or are in an invalid format.

        """
        credentials = {}

        #TODO: Improve the credentials validation for Onedrive
        if storage_type == 'onedrive':
            if 'credentials' in config_obj:
                credentials = config_obj['credentials']
                if not isinstance(config_obj, dict):
                    raise ValueError('credentials must be a dictionary')
                if 'credentials' not in config_obj or not isinstance(config_obj['credentials'], dict):
                    raise ValueError('credentials must be a dictionary')
                if 'username' not in config_obj['credentials'] or not isinstance(config_obj['credentials']['username'], str):
                    raise ValueError('username must be a string')
                if 'password' not in config_obj['credentials'] or not isinstance(config_obj['credentials']['password'], str):
                    raise ValueError('password must be a string')

                credentials = {'username': credentials['username'].strip(), 'password': credentials['password'].strip()}

            else:
                raise ValueError('Credentials for Onedrive: e.g. "credentials": {"username": "john", "password": "password"}')

        elif storage_type == 'gspread' or storage_type == 'gdrive':
            if 'credentials' in config_obj:
                credentials = config_obj['credentials']
                if not isinstance(credentials, dict):
                    raise ValueError('credentials must be a dictionary')

            else:
                raise ValueError('Need credentials for Gspread/Gdrive. See: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account')

        return credentials
    
    def _get_storage_base_url(self, url, storage_type="gspread"):
        """
        Get the base URL for the given storage type.

        Args:
            url (str): The URL to extract the base URL from.
            storage_type (str, optional): The type of storage. Defaults to "gspread".

        Returns:
            str: The base URL.

        """        
        if storage_type == 'gspread':
            base_url = url[:url.find('/', url.rfind('d/') + 2)]

        elif storage_type == 'onedrive':
            base_url = url
            
        else:
            return url

        return base_url
    
    def _get_storage_url(self, url, storage_type='gspread'):
        """
        Get the remote source URL based on the given URL and storage type.

        Args:
            url (str): The input URL.
            storage_type (str, optional): The type of storage. Defaults to 'gspread'.

        Returns:
            str: The remote source URL.

        Raises:
            ValueError: If an invalid storage_type is provided.
        """
        try:
            if storage_type == 'onedrive':
                data_bytes64 = base64.urlsafe_b64encode(url.encode('utf-8')).rstrip(b'=')
                data_bytes64_str = data_bytes64.decode('utf-8')
                remote_source_url = f'https://api.onedrive.com/v1.0/shares/u!{data_bytes64_str}/root/content'

            elif storage_type == 'gspread':
                remote_source_url = url

            else:
                raise ValueError(f'Invalid storage_type: {storage_type}')

            return remote_source_url

        except Exception as e:
            raise ValueError('Invalid storage_type') from e
 
    @staticmethod
    def _transform_column_names(content_dicts, field_mapping):
        transformed_content_dict = content_dicts.copy()
        for key, value in field_mapping.items():
            if value['field_position'] in transformed_content_dict.columns:
                transformed_content_dict.rename(columns={value['field_position'].upper(): key}, inplace=True)
        return transformed_content_dict
 
    @staticmethod
    def _map_dataframe_columns_to_spreadsheet_format(df):
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
            col_names.append(col_name.upper())
        df.columns = col_names
        return df
   
    def _read_remote_sheet(self, url, sheet_name, storage_type, engine='openpyxl', harvest_job=None):
        """
        Reads an Excel sheet from a given URL and returns the data as a pandas DataFrame.

        Args:
            url (str): The URL of the Excel file.
            sheet_name (str): The name of the sheet to read.
            storage_type (str): The type of storage where the Excel file is located. Supported types are 'onedrive', 'gspread', and 'gdrive'.
            engine (str, optional): The engine to use for reading the Excel file. Defaults to 'openpyxl'.

        Returns:
            pandas.DataFrame: The data from the specified sheet as a DataFrame.

        Raises:
            ReadError: If there is an error reading the sheet.

        """
        try:
            if storage_type == 'onedrive':
                if self.auth and self._credentials:
                    # TODO: Implement the read_excel_sheet method for Onedrive Auth
                    pass
                else:
                    try:
                        data = pd.read_excel(url, sheet_name=sheet_name, dtype=str, engine=engine)
                    except pd.errors.ParserError as e:
                        error_msg = f'Error reading sheet {sheet_name} using URL {url}. Error: {str(e)}'
                        self._save_gather_error(error_msg, harvest_job)
                        raise ReadError(error_msg)

            elif storage_type in ['gspread', 'gdrive']:
                if self._auth and self._credentials:
                    try:
                        gc = gspread.service_account_from_dict(self._credentials)
                        sh = gc.open_by_url(url)
                        worksheet = sh.worksheet(sheet_name)
                        data = pd.DataFrame(worksheet.get_all_records(), dtype=str)
                    except gspread.exceptions.APIError as e:
                        msg_error = f'Error reading sheet {sheet_name} using URL {url}. Error: {str(e)}. If the file is an XLS file, it needs to be converted to a Google Sheet.'
                        self._save_gather_error(msg_error, harvest_job)
                        raise ReadError(msg_error)
                else:
                    msg_error = 'Need credentials for Gspread/Gdrive. See: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account'
                    self._save_gather_error(msg_error, harvest_job)
                    raise ValueError(msg_error)

            else:
                msg_error = f'Unsupported storage type: {storage_type}'
                self._save_gather_error(msg_error, harvest_job)
                raise ValueError(msg_error)

            return data.fillna('')

        except Exception as e:
            raise ReadError(f'Error reading sheet {sheet_name} using URL {url}. Error: {str(e)}')

    def _clean_table_datasets(self, data):
        """
        Clean the table datasets by removing leading/trailing whitespaces, newlines, and tabs.

        Args:
            data (pandas.DataFrame): The input table dataset.

        Returns:
            list: A list of dictionaries representing the cleaned table datasets.
        """
        # Clean column names by removing leading/trailing whitespaces, newlines, and tabs
        data.columns = data.columns.str.strip().str.replace('\n', '').str.replace('\t', '')

        # Remove all fields that are a nan float and trim all spaces of the values
        data = data.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)
        data = data.fillna(value='')

        # Convert table to list of dicts
        return data.to_dict('records')

    def _clean_table_distributions(self, data, prefix_colnames='resource_', dataset_id_colname='dataset_id'):
        """
        Clean the table distributions data.

        Args:
            data (pandas.DataFrame): The table distributions data.
            prefix_colnames (str, optional): The prefix used in column names that need to be removed. Defaults to 'resource_'.
            dataset_id_colname (str, optional): The column name representing the dataset ID. Defaults to 'dataset_id'.

        Returns:
            dict or None: A dictionary containing the cleaned distributions data grouped by dataset_id,
            or None if no distributions are loaded.
        """
        if dataset_id_colname is None:
            dataset_id_colname = 'dataset_id'

        # Select only the columns of type 'object' and apply the strip() method to them
        data.loc[:, data.dtypes == object] = data.select_dtypes(include=['object']).apply(lambda x: x.str.strip())

        # Remove prefixes from column names in the distributions dataframe if prefix_colnames is not None
        if prefix_colnames is not None:
            data = data.rename(columns=lambda x: x.replace(prefix_colnames, ''))

        # Remove rows where dataset_id_colname is None or an empty string
        try:
            data = data[data[dataset_id_colname].notna() & (data[dataset_id_colname] != '')]
        except Exception as e:
            log.error('Error removing rows: %s | Exception type: %s', str(e), type(e).__name__)
            raise e

        if not data.empty:
            # Group distributions by dataset_id and convert to list of dicts
            return data.groupby(dataset_id_colname).apply(lambda x: x.to_dict('records')).to_dict()
        else:
            log.debug('No distributions loaded. Check "distribution.%s" fields', dataset_id_colname)
            return None

    def _clean_table_datadictionaries(self, data, prefix_colnames='datadictionary_', distribution_id_colname='resource_id'):
        """
        Clean and process the table of data dictionaries.

        Args:
            data (pandas.DataFrame): The table of data dictionaries.
            prefix_colnames (str, optional): The prefix used in column names that need to be removed. Defaults to 'datadictionary_'.
            distribution_id_colname (str, optional): The column name for the resource ID. Defaults to 'resource_id'.

        Returns:
            dict or None: A dictionary containing the cleaned and processed data dictionaries grouped by resource ID,
                          or None if no data dictionaries were loaded.
        """
        if distribution_id_colname is None:
            distribution_id_colname = 'resource_id'

        # Select only the columns of type 'object' and apply the strip() method to them
        object_cols = data.select_dtypes(include=['object']).columns
        data[object_cols] = data[object_cols].apply(lambda x: x.str.strip())

        # Remove prefixes from column names in the datadictionaries dataframe
        new_column_names = {col: re.sub(re.compile(rf'{prefix_colnames}(_info)?_'), '', col).replace('info.', '') for col in data.columns}
        data.rename(columns=new_column_names, inplace=True)

        # Filter datadictionaries where resource_id is not empty or None
        if distribution_id_colname in data.columns:
            data = data[data[distribution_id_colname].notna() & (data[distribution_id_colname] != '')]

            # Group datadictionaries by resource_id and convert to list of dicts
            return data.groupby(distribution_id_colname).apply(lambda x: x.to_dict('records')).to_dict()
        else:
            log.debug('No datadictionaries loaded. Check "datadictionary.%s" fields', distribution_id_colname)
            return None

    def _add_distributions_and_datadictionaries_to_datasets(self, table_datasets, table_distributions_grouped, table_datadictionaries_grouped, identifier_field='identifier', alternate_identifier_field='alternate_identifier', inspire_id_field='inspire_id', datadictionary_id_field="id"):
        """
        Add distributions (CKAN resources) and datadictionaries to each dataset object.
    
        Args:
            table_datasets (list): List of dataset objects.
            table_distributions_grouped (dict): Dictionary of distributions grouped by dataset identifier.
            table_datadictionaries_grouped (dict): Dictionary of datadictionaries grouped by dataset identifier.
            identifier_field (str, optional): Field name for the identifier. Defaults to 'identifier'.
            alternate_identifier_field (str, optional): Field name for the alternate identifier. Defaults to 'alternate_identifier'.
            inspire_id_field (str, optional): Field name for the inspire id. Defaults to 'inspire_id'.
            datadictionary_id_field (str, optional): Field name for the datadictionary id. Defaults to 'id'.
    
        Returns:
            list: List of dataset objects with distributions (CKAN resources) and datadictionaries added.
    
        Notes:
            If 'dataset_id_field' is specified in the Harvester configuration, it will be used as the primary identifier field.
            Otherwise, the function will fall back to using 'identifier_field', 'alternate_identifier_field', and 'inspire_id_field' in that order.
        """
        try:
            dataset_id_field = self.config.get('dataset_id_field', None)
            return [
                {
                    **d,
                    'resources': [
                        {**dr, 'datadictionaries': table_datadictionaries_grouped.get(dr[datadictionary_id_field], []) if table_datadictionaries_grouped else []}
                        for dr in table_distributions_grouped.get(
                            d.get(dataset_id_field) if dataset_id_field else d.get(identifier_field) or d.get(alternate_identifier_field) or d.get(inspire_id_field), []
                        )
                    ]
                }
                for d in table_datasets
            ]
        except Exception as e:
            log.error("Error while adding distributions and datadictionaries to datasets: %s", str(e))
            raise

    def _process_content(self, content_dicts, source_url, distribution_prefix_colnames, dataset_id_colname, datadictionary_prefix_colnames, distribution_id_colname):
        """
        Process the content of the harvested dataset.

        Args:
            content_dicts (dict): A dict of dataframes containing the content of the harvested dataset (datasets, distributions and datadictionaries).
            source_url (str): The URL of the harvested dataset.
            distribution_prefix_colnames (str): The prefix used in column names that need to be removed in the distributions dataframe.
            dataset_id_colname (str): The column name representing the dataset ID.
            datadictionary_prefix_colnames (str): The prefix used in column names that need to be removed in the datadictionaries dataframe.
            distribution_id_colname (str): The column name representing the resource ID.

        Returns:
            dict: A dictionary containing the processed content of the harvested dataset.
        """
        log.debug('In SchemingDCATXLSHarvester process_content: %s', source_url)

        table_datasets = self._clean_table_datasets(content_dicts['datasets'])

        if content_dicts.get('distributions') is not None and not content_dicts['distributions'].empty:
            table_distributions_grouped = self._clean_table_distributions(content_dicts['distributions'], distribution_prefix_colnames, dataset_id_colname)
        else:
            log.debug('No distributions loaded. Check "distribution.%s" fields', dataset_id_colname)
            table_distributions_grouped = None

        if content_dicts.get('datadictionaries') is not None and not content_dicts['datadictionaries'].empty:
            table_datadictionaries_grouped = self._clean_table_datadictionaries(content_dicts['datadictionaries'], datadictionary_prefix_colnames, distribution_id_colname)
        else:
            table_datadictionaries_grouped = None

        return self._add_distributions_and_datadictionaries_to_datasets(table_datasets, table_distributions_grouped, table_datadictionaries_grouped)

    def get_package_dict(self, harvest_object, context, package_dict=None):
        """
        Returns a dictionary representing the CKAN package to be created or updated.

        Args:
            harvest_object (HarvestObject): The harvest object being processed.
            context (dict): The context of the harvest process.
            package_dict (dict, optional): The initial package dictionary (dataset). Defaults to None.

        Returns:
            dict: The package dictionary with translated fields and default values set.
        """
        # Add default values: tags, groups, etc.
        package_dict = self._set_package_dict_default_values(package_dict, harvest_object, context)

        # Update unique ids
        for resource in package_dict['resources']:
            resource['url'] = resource.get('url', "")
            resource['alternate_identifier'] = resource.get('id', None)
            resource['id'] = str(uuid.uuid4())
            resource.pop('dataset_id', None)

        return package_dict

    @staticmethod
    def _set_value_to_list(value):
        """
        Determines whether a value should be converted to a list.

        Args:
            value (str): The value to check.

        Returns:
            bool: True if the value should be converted to a list, False otherwise.
        """
        # Check if the value is a string containing commas but not common sentence punctuation
        return isinstance(value, str) and ',' in value and not any(char in value for char in '.!?')

    @staticmethod
    def _set_string_to_list(value):
        """
        Converts a comma-separated string into a list of items.

        Args:
            value (str): The comma-separated string to convert.

        Returns:
            list: A list of items, with leading and trailing whitespace removed from each item,
                  and leading dashes from each item.

        Example:
            >>> _set_string_to_list('apple, banana, -orange')
            ['apple', 'banana', 'orange']
        """
        return [x.strip(" -") for x in value.split(',') if x.strip()]

    def _update_dict_lists(self, data):
        """
        Update the dictionary lists in the given data.

        Args:
            data (list): The data to be updated.

        Returns:
            list: The updated data.
        """
        if self._local_schema is None:
            self._local_schema = self._get_local_schema()
        
        # Get the list of fields that should be converted to lists
        list_fields = ['groups'] + [
            field['field_name']
            for field in self._local_schema['dataset_fields']
            if any(keyword in field.get(field_type, '').lower() for keyword in ['list', 'multiple', 'tag_string', 'tag', 'group'] for field_type in ['validators', 'output_validators', 'preset']) or 'groups' in field['field_name'].lower()
        ]
    
        for element in data:
            for key, value in element.items():
                if key in list_fields and key not in XLS_HARVESTER_FIELDS_NOT_LIST and isinstance(value, str):
                    element[key] = self._set_string_to_list(value)
                elif key == 'distributions':
                    for distribution in value:
                        for key_dist, value_dist in distribution.items():
                            if key_dist in list_fields and key_dist not in XLS_HARVESTER_FIELDS_NOT_LIST and isinstance(value_dist, str):
                                distribution[key_dist] = self._set_string_to_list(value_dist)
    
        # Return the updated data
        return data

    def validate_config(self, config):
        """
        Validates the configuration for the harvester.

        Args:
            config (dict): The configuration dictionary.

        Returns:
            str: The validated configuration as a JSON string.

        Raises:
            ValueError: If the configuration is invalid.

        """
        config_obj = self.get_harvester_basic_info(config)
        auth = False

        supported_types = {st['name'] for st in self._storage_types_supported.values() if st['active']}

        # Check basic validation config
        self._set_basic_validate_config(config)
        
        # Instance field_mapping validator
        field_mapping_validator = FieldMappingValidator()

        # Check the storage type of the remote file
        if 'storage_type' in config:
            storage_type = config_obj['storage_type']
            if not isinstance(storage_type, str):
                raise ValueError('storage_type must be a string')

            if storage_type not in supported_types:
                raise ValueError(f'storage_type should be one of: {", ".join(supported_types)}')

            config = json.dumps({**config_obj, 'storage_type': storage_type})

        else:
            raise ValueError(f'storage_type should be one of: {", ".join(supported_types)}')

        # Check the the cols info of the remote file
        for mapping_name, default_value in [('distribution_prefix_colnames', 'resource_'), 
                                            ('dataset_id_colname', 'dataset_id'),
                                            ('datadictionary_prefix_colnames', 'datadictionary_'),
                                            ('distribution_id_colname', 'resource_id')]:
            if mapping_name in config:
                mapping_value = config_obj[mapping_name]
                if not isinstance(mapping_value, (str, type(None))):
                    raise ValueError(f'{mapping_name} must be a string or None')
            else:
                if mapping_name == 'distribution_prefix_colnames':
                    raise ValueError(f'{mapping_name} must be provided in the configuration, even if as None, e.g. ("distribution_prefix_colnames": null). If not provided, the default value "{default_value}" will be used.')
                mapping_value = default_value

            config = json.dumps({**config_obj, mapping_name: mapping_value})

        # Check the name of the dataset sheet in the remote table
        if 'dataset_sheet' in config:
            dataset_sheet = config_obj['dataset_sheet']
            if not isinstance(dataset_sheet, str):
                raise ValueError('dataset_sheet must be a string')
    
            config = json.dumps({**config_obj, 'dataset_sheet': dataset_sheet.strip()})

        else:
            raise ValueError('The name of the datasets sheet is required. e.g. "dataset_sheet": "Dataset"')

        # Check the name of the distribution and data dictionary (resourcedictionary) sheets in the remote table
        if 'distribution_sheet' in config:
            distribution_sheet = config_obj['distribution_sheet']
            if not isinstance(distribution_sheet, str):
                raise ValueError('distribution_sheet must be a string')

            config = json.dumps({**config_obj, 'distribution_sheet': distribution_sheet.strip()})
    
        if 'datadictionary_sheet' in config:
            datadictionary_sheet = config_obj['datadictionary_sheet']
            if not isinstance(datadictionary_sheet, str):
                raise ValueError('datadictionary_sheet must be a string')

            config = json.dumps({**config_obj, 'datadictionary_sheet': datadictionary_sheet.strip()})

        # Check and retrieve credentials for the storage type
        if 'credentials' not in config:
            raise ValueError(f'Credentials must exist to access spreadsheets via: {config_obj["storage_type"]}.')
        else:
            credentials = self._set_config_credentials(storage_type, config_obj)
            config_obj.update({'auth': True, 'credentials': credentials})
            config = json.dumps(config_obj)
    
        if 'default_tags' in config_obj:
            if not isinstance(config_obj['default_tags'], list):
                raise ValueError('default_tags must be a list')
            if config_obj['default_tags'] and \
                    not isinstance(config_obj['default_tags'][0], dict):
                raise ValueError('default_tags must be a list of '
                                    'dictionaries')

        if 'default_groups' in config_obj:
            if not isinstance(config_obj['default_groups'], list):
                raise ValueError('default_groups must be a *list* of group'
                                    ' names/ids')
            if config_obj['default_groups'] and \
                    not isinstance(config_obj['default_groups'][0], str):
                raise ValueError('default_groups must be a list of group '
                                    'names/ids (i.e. strings)')

            # Check if default groups exist
            context = {'model': model, 'user': p.toolkit.c.user}
            config_obj['default_group_dicts'] = []
            for group_name_or_id in config_obj['default_groups']:
                try:
                    group = get_action('group_show')(
                        context, {'id': group_name_or_id})
                    # save the id and name to the config object, as we'll need it
                    # in the import_stage of every dataset
                    config_obj['default_group_dicts'].append({'id': group['id'], 'name': group['name']})
                except NotFound:
                    raise ValueError('Default group not found')
            config = json.dumps(config_obj)

        if 'default_extras' in config_obj:
            if not isinstance(config_obj['default_extras'], dict):
                raise ValueError('default_extras must be a dictionary')
        
            # Get the field names from the schema
            schema_field_names = schemingdcat_get_dataset_schema_field_names()

            # Extract dataset_fields
            dataset_field_names = []
            for field_group in schema_field_names:
                if 'dataset_fields' in field_group:
                    dataset_field_names.extend(field_group['dataset_fields'])

            # Check if any field_name in default_extras exists in dataset_fields
            for field_name in config_obj['default_extras']:
                if field_name in dataset_field_names:
                    raise KeyError(f"Field name '{field_name}' in default_extras already exists in the schema")

        if 'user' in config_obj:
            # Check if user exists
            context = {'model': model, 'user': p.toolkit.c.user}
            try:
                get_action('user_show')(
                    context, {'id': config_obj.get('user')})
            except NotFound:
                raise ValueError('User not found')

        # Check if 'allow_harvest_datasets' is not in the config_obj or is not a boolean
        if 'allow_harvest_datasets' not in config_obj or not isinstance(config_obj['allow_harvest_datasets'], bool):
            config = json.dumps({**config_obj, 'allow_harvest_datasets': False})
            
        # Check if source_date_format exists, is a string and is a valid date format
        source_date_format = config_obj.get('source_date_format', '%Y-%m-%d')
        if not isinstance(source_date_format, str):
            raise ValueError('source_date_format must be a string')
        if source_date_format not in COMMON_DATE_FORMATS:
            raise ValueError(f'source_date_format: {str(source_date_format)} is not a valid date format. Accepted formats are: {" | ".join(COMMON_DATE_FORMATS)}. More info: https://docs.python.org/es/3/library/datetime.html#strftime-and-strptime-format-codes')

        # Check if 'field_mapping_schema_version' exists in the config
        field_mapping_schema_version_error_message = f'Insert the schema version: "field_mapping_schema_version: <version>", one of: {", ".join(map(str, self._field_mapping_validator_versions))} . More info: https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#remote-google-sheetonedrive-excel-metadata-upload-harvester'
        if 'field_mapping_schema_version' not in config_obj:
            raise ValueError(field_mapping_schema_version_error_message)
        else:
            # Check if is an integer and if it is in the versions
            if not isinstance(config_obj['field_mapping_schema_version'], int) or config_obj['field_mapping_schema_version'] not in self._field_mapping_validator_versions:
                raise ValueError(field_mapping_schema_version_error_message)

        # Validate if exists a JSON contained the mapping field_names between the remote schema and the local schema        
        for mapping_name in self._field_mapping_info.keys():
            if mapping_name in config:
                field_mapping = config_obj[mapping_name]
                if not isinstance(field_mapping, dict):
                    raise ValueError(f'{mapping_name} must be a dictionary')

                schema_version = config_obj['field_mapping_schema_version']

                try:
                    # Validate field_mappings acordin schema versions
                    field_mapping = field_mapping_validator.validate(field_mapping, schema_version)
                except ValueError as e:
                    raise ValueError(f"The field mapping is invalid: {e}") from e

                config = json.dumps({**config_obj, mapping_name: field_mapping})

        # Check if dataset_id_field exists and is a string
        if 'dataset_id_field' in config_obj:
            dataset_id_field = config_obj['dataset_id_field']
            if not isinstance(dataset_id_field, str):
                raise ValueError('dataset_id_field must be a string')

        return config

    def modify_package_dict(self, package_dict, harvest_object):
        '''
            Allows custom harvesters to modify the package dict before
            creating or updating the actual package.
        '''              
        return package_dict

    def gather_stage(self, harvest_job):
        """
        Performs the gather stage of the SchemingDCATXLSHarvester. This method is responsible for downloading the remote remote table and reading its contents. The contents are then processed, cleaned, and added to the database.

        Args:
            harvest_job (HarvestJob): The harvest job object.

        Returns:
            list: A list of object IDs for the harvested datasets.
        """
        # Get file contents of source url
        harvest_source_title = harvest_job.source.title
        source_url = harvest_job.source.url
        
        log.debug('In SchemingDCATXLSHarvester gather_stage with harvest source: %s and remote sheet: %s', harvest_source_title, source_url)
        
        content_dicts = {}
        self._names_taken = []
        
        # Get config options
        if harvest_job.source.config:
            self._set_config(harvest_job.source.config)
            dataset_sheetname = self.config.get("dataset_sheet")
            distribution_sheetname = self.config.get("distribution_sheet")
            datadictionary_sheetname = self.config.get("datadictionary_sheet")
            self.get_harvester_basic_info(harvest_job.source.config)
        
        log.debug('Using config: %r', self._secret_properties(self.config))
        
        if self.config:
            self._storage_type = self.config.get("storage_type")
            self._auth = self.config.get("auth")
            self._credentials = self.config.get("credentials")
            dataset_id_colname = self.config.get("dataset_id_colname", "dataset_id")

            # Get URLs for remote file
            remote_xls_base_url = self._get_storage_base_url(source_url, self._storage_type)
            remote_sheet_download_url = self._get_storage_url(source_url, self._storage_type)
        
        # Check if the remote file is valid
        is_valid = self._check_accesible_url(remote_sheet_download_url, harvest_job, self._auth)
        
        if not is_valid:
            log.error(f'The URL is not accessible. The harvest source: "{harvest_source_title}" has finished.')
            return []
        
        log.debug('URL is accessible: %s', remote_sheet_download_url)
        log.debug('Storage type: %s', self._storage_type)

        # Get the previous guids for this source
        query = \
            model.Session.query(HarvestObject.guid, HarvestObject.package_id) \
            .filter(HarvestObject.current == True) \
            .filter(HarvestObject.harvest_source_id == harvest_job.source.id)
        guid_to_package_id = {}

        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = set(guid_to_package_id.keys())
        guids_in_harvest = set()

        # before_download interface
        for harvester in p.PluginImplementations(ISchemingDCATHarvester):
            if hasattr(harvester, 'before_download'):
                remote_sheet_download_url, before_download_errors = harvester.before_download(remote_sheet_download_url, harvest_job)
                
                for error_msg in before_download_errors:
                    self._save_gather_error(error_msg, harvest_job)
                
                if not remote_sheet_download_url:
                    return []
        
        # Read sheets
        if is_valid:
            try:
                try:
                    content_dicts['datasets'] = self._read_remote_sheet(remote_sheet_download_url, dataset_sheetname, self._storage_type )
                except RemoteResourceError as e:
                    self._save_gather_error('Error reading the remote Excel datasets sheet: {0}'.format(e), harvest_job)
                    return False
                
                if distribution_sheetname:
                    content_dicts['distributions'] = self._read_remote_sheet(remote_sheet_download_url, distribution_sheetname, self._storage_type, harvest_job)
                    
                #TODO: Implement self._load_datadictionaries() method.
                if datadictionary_sheetname:
                    content_dicts['datadictionaries'] = self._read_remote_sheet(remote_sheet_download_url, datadictionary_sheetname, self._storage_type, harvest_job)

                # after_download interface
                for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                    if hasattr(harvester, 'after_download'):
                        content_dicts, after_download_errors = harvester.after_download(content_dicts, harvest_job)

                        for error_msg in after_download_errors:
                            self._save_gather_error(error_msg, harvest_job)

                if not content_dicts:
                    return []

            except Exception as e:
                self._save_gather_error('Could not read remote sheet file: %s' % str(e), harvest_job)
                return False
        
        # Check if the content_dicts colnames correspond to the local schema
        try:
            # Standardizes the field_mapping           
            field_mappings = {
              'dataset_field_mapping': self._standardize_field_mapping(self.config.get("dataset_field_mapping")),
              'distribution_field_mapping': self._standardize_field_mapping(self.config.get("distribution_field_mapping")),
              'datadictionary_field_mapping': None
            }

            # Standardizes the field names
            content_dicts['datasets'], field_mappings['dataset_field_mapping'] = self._standardize_df_fields_from_field_mapping(content_dicts['datasets'], field_mappings['dataset_field_mapping'])
            content_dicts['distributions'], field_mappings['distribution_field_mapping'] = self._standardize_df_fields_from_field_mapping(content_dicts['distributions'], field_mappings['distribution_field_mapping'])
            
            # Validate field names
            remote_dataset_field_names = set(content_dicts['datasets'].columns)
            remote_resource_field_names = set(content_dicts['distributions'].columns)

            self._validate_remote_schema(remote_dataset_field_names=remote_dataset_field_names, remote_ckan_base_url=None, remote_resource_field_names=remote_resource_field_names, remote_dataset_field_mapping=field_mappings['dataset_field_mapping'], remote_distribution_field_mapping=field_mappings['distribution_field_mapping'])

        except RemoteSchemaError as e:
            self._save_gather_error('Error validating remote schema: {0}'.format(e), harvest_job)
            return []

        # before_cleaning interface
        for harvester in p.PluginImplementations(ISchemingDCATHarvester):
            if hasattr(harvester, 'before_cleaning'):
                content_dicts, before_cleaning_errors = harvester.before_cleaning(content_dicts, harvest_job, self.config)

                for error_msg in before_cleaning_errors:
                    self._save_gather_error(error_msg, harvest_job)

        # Clean tables
        try:
            clean_datasets = self._process_content(content_dicts, remote_xls_base_url, self.config.get("distribution_prefix_colnames"), self.config.get("dataset_id_colname"), self.config.get("datadictionary_prefix_colnames"), self.config.get("distribution_id_colname"))
            log.debug('"%s" remote file cleaned successfully.', self._storage_types_supported[self._storage_type]['title'])
            clean_datasets = self._update_dict_lists(clean_datasets)
            #log.debug('clean_datasets: %s', clean_datasets)
            log.debug('Update dict string lists. Number of datasets imported: %s', len(clean_datasets))
            
        except Exception as e:
            self._save_gather_error('Error cleaning the remote table: {0}'.format(e), harvest_job)
            return []
    
        # after_cleaning interface
        for harvester in p.PluginImplementations(ISchemingDCATHarvester):
            if hasattr(harvester, 'after_cleaning'):
                clean_datasets, after_cleaning_errors = harvester.after_cleaning(clean_datasets)

                for error_msg in after_cleaning_errors:
                    self._save_gather_error(error_msg, harvest_job)

        # Log the length of clean_datasets after after_cleaning
        log.debug(f"Length of clean_datasets after_cleaning ISQLHarvester: {len(clean_datasets)}")

        # Add datasets to the database
        try:
            log.debug('Adding datasets to DB')
            datasets_to_harvest = {}
            source_dataset = model.Package.get(harvest_job.source.id)
            skipped_datasets = 0  # Counter for omitted datasets
            identifier_counts = {}  # To track the frequency of identifiers

            for dataset in clean_datasets:
                #log.debug('dataset: %s', dataset)

                # Set and update translated fields
                dataset = self._set_translated_fields(dataset)
                
                try:
                    if not dataset.get('name'):
                        dataset['name'] = self._gen_new_name(dataset['title'])
                    while dataset['name'] in self._names_taken:
                        suffix = sum(name.startswith(dataset['name'] + '-') for name in self._names_taken) + 1
                        dataset['name'] = '{}-{}'.format(dataset['name'], suffix)
                    self._names_taken.append(dataset['name'])
        
                    # If the dataset has no identifier, use an UUID
                    if not dataset.get('identifier'):
                        dataset['identifier'] = str(uuid.uuid4())
        
                except Exception as e:
                    skipped_datasets += 1
                    self._save_gather_error('Error for the dataset identifier %s [%r]' % (dataset.get('identifier'), e), harvest_job)
                    continue
                
                if not dataset.get('identifier'):
                    skipped_datasets += 1
                    self._save_gather_error('Missing identifier for dataset with title: %s' % dataset.get('title'), harvest_job)
                    continue
                
                # Check if a dataset with the same identifier exists can be overridden if necessary
                #existing_dataset = self._check_existing_package_by_ids(dataset)
                #log.debug('existing_dataset: %s', existing_dataset)
                            
                # Unless already set by the dateutil.parser.parser, get the owner organization (if any)
                # from the harvest source dataset
                if not dataset.get('owner_org') and source_dataset.owner_org:
                    dataset['owner_org'] = source_dataset.owner_org
        
                if 'extras' not in dataset:
                    dataset['extras'] = []

                # if existing_dataset:
                #     dataset['identifier'] = existing_dataset['identifier']

                identifier = dataset['identifier']
                # Track the frequency of each identifier
                identifier_counts[identifier] = identifier_counts.get(identifier, 0) + 1
                if identifier_counts[identifier] > 1:
                    log.warning(f'Duplicate identifier detected: {identifier}. This dataset will overwrite the previous one.')

                #     guids_in_db.add(dataset['identifier'])

                guids_in_harvest.add(identifier)
                datasets_to_harvest[identifier] = dataset
        
            # Register duplicate identifiers
            duplicates = [id for id, count in identifier_counts.items() if count > 1]
            if duplicates:
                log.warning(f"The following duplicate identifiers {len(duplicates)} are found: {duplicates}")
        
        except Exception as e:
            self._save_gather_error('Error when processing dataset: %r / %s' % (e, traceback.format_exc()), harvest_job)
            return []

        # Check guids to create/update/delete
        new = guids_in_harvest - guids_in_db
        # Get objects/datasets to delete (ie in the DB but not in the source)
        delete = set(guids_in_db) - set(guids_in_harvest)
        change = guids_in_db & guids_in_harvest
        
        log.debug(f"Number of skipped datasets: {skipped_datasets}")
        log.debug(f'guids_in_harvest ({len(guids_in_harvest)})')
        log.debug(f'guids_in_db ({len(guids_in_db)}): {guids_in_db}')
        log.debug(f'new ({len(new)})')
        log.debug(f'delete ({len(delete)})')
        log.debug(f'change ({len(change)})')
        
        ids = []
        for guid in new:
            dataset = datasets_to_harvest.get(guid)
            if dataset:
                obj = HarvestObject(guid=guid, job=harvest_job, content=json.dumps(dataset),
                                    extras=[HarvestObjectExtra(key='status', value='new')])
                obj.save()
                ids.append({'id': obj.id, 'name': dataset['name'], 'identifier': dataset['identifier']})
            else:
                log.warning(f'Dataset for GUID {guid} not found in datasets_to_harvest')
        
        for guid in change:
            dataset = datasets_to_harvest.get(guid)
            if dataset:
                obj = HarvestObject(guid=guid, job=harvest_job, content=json.dumps(dataset),
                                    package_id=guid_to_package_id[guid],
                                    extras=[HarvestObjectExtra(key='status', value='change')])
                obj.save()
                ids.append({'id': obj.id, 'name': dataset['name'], 'identifier': dataset['identifier']})
            else:
                log.warning(f'Dataset for GUID {guid} not found in datasets_to_harvest')
        
        for guid in delete:
            dataset = datasets_to_harvest.get(guid)
            if dataset:
                obj = HarvestObject(guid=guid, job=harvest_job, content=json.dumps(dataset),
                                    package_id=guid_to_package_id[guid],
                                    extras=[HarvestObjectExtra(key='status', value='delete')])
                model.Session.query(HarvestObject).\
                    filter_by(guid=guid).\
                    update({'current': False}, False)
                obj.save()
                ids.append({'id': obj.id, 'name': dataset['name'], 'identifier': dataset['identifier']})
            else:
                log.warning(f'Dataset for GUID {guid} not found in datasets_to_harvest')
        
        log.debug('Number of elements in clean_datasets: %s and object_ids: %s', len(clean_datasets), len(ids))
        
        # Log clean_datasets/ ids
        #self._log_export_clean_datasets_and_ids(harvest_source_title, clean_datasets, ids)

        return [id_dict['id'] for id_dict in ids]
    
    def fetch_stage(self, harvest_object):
        # Nothing to do here - we got the package dict in the search in the gather stage
        return True
    
    def import_stage(self, harvest_object):
        """
        Performs the import stage of the SchemingDCATXLSHarvester.

        Args:
            harvest_object (HarvestObject): The harvest object to import.

        Returns:
            bool or str: Returns True if the import is successful, 'unchanged' if the package is unchanged,
                        or False if there is an error during the import.

        Raises:
            None
        """
        log.debug('In SchemingDCATXLSHarvester import_stage')

        harvester_tmp_dict = {}
        context = {
            'model': model,
            'session': model.Session,
            'user': self._get_user_name(),
        }

        if self._local_schema is None:
            self._local_schema = self._get_local_schema()

        if not harvest_object:
            log.error('No harvest object received')
            return False   
        
        self._set_config(harvest_object.source.config)
        
        if self.force_import:
            status = 'change'
        else:
            status = self._get_object_extra(harvest_object, 'status')

        # Get the last harvested object (if any)
        previous_object = model.Session.query(HarvestObject) \
                          .filter(HarvestObject.guid==harvest_object.guid) \
                          .filter(HarvestObject.current==True) \
                          .first()

        if status == 'delete':
            override_local_datasets = self.config.get("override_local_datasets", False)
            if override_local_datasets is True:
                # Delete package
                context.update({
                    'ignore_auth': True,
                })
                p.toolkit.get_action('package_delete')(context, {'id': harvest_object.package_id})
                log.info('The override_local_datasets configuration is %s. Package %s deleted with GUID: %s' % (override_local_datasets, harvest_object.package_id, harvest_object.guid))

                return True
            
            else:
                log.info('The override_local_datasets configuration is %s. Package %s not deleted with GUID: %s' % (override_local_datasets, harvest_object.package_id, harvest_object.guid))

                return 'unchanged'

        # Check if harvest object has a non-empty content
        if harvest_object.content is None:
            self._save_object_error('Empty content for object {0}'.format(harvest_object.id),
                                    harvest_object, 'Import')
            return False

        try:
            dataset = json.loads(harvest_object.content)
        except ValueError:
            self._save_object_error('Could not ateutil.parser.parse content for object {0}'.format(harvest_object.id),
                                    harvest_object, 'Import')
            return False

        # Check if the dataset is a harvest source and we are not allowed to harvest it
        if dataset.get('type') == 'harvest' and self.config.get('allow_harvest_datasets', False) is False:
            log.warn('Remote dataset is a harvest source and allow_harvest_datasets is False, ignoring...')
            return True

        dataset = self.modify_package_dict(dataset, harvest_object)

        # Flag previous object as not current anymore
        if previous_object and not self.force_import:
            previous_object.current = False
            previous_object.add()

        # Dataset dict::Update GUID with the identifier from the dataset
        remote_guid = dataset['identifier']
        if remote_guid and harvest_object.guid != remote_guid:
            # First make sure there already aren't current objects
            # with the same guid
            existing_object = model.Session.query(HarvestObject.id) \
                            .filter(HarvestObject.guid==remote_guid) \
                            .filter(HarvestObject.current==True) \
                            .first()
            if existing_object:
                self._save_object_error('Object {0} already has this guid {1}'.format(existing_object.id, remote_guid),
                        harvest_object, 'Import')
                return False

            harvest_object.guid = remote_guid
            harvest_object.add()

        # Assign GUID if not present (i.e. it's a manual import)
        if not harvest_object.guid:
            harvest_object.guid = remote_guid
            harvest_object.add()

        # Update dates
        self._source_date_format = self.config.get('source_date_format', '%Y-%m-%d')
        self._set_basic_dates(dataset)

        harvest_object.metadata_modified_date = dataset['modified']
        harvest_object.add()

        # Build the package dict
        package_dict = self.get_package_dict(harvest_object, context, dataset)
        if not package_dict:
            log.error('No package dict returned, aborting import for object %s' % harvest_object.id)
            return False

        # Create / update the package
        context.update({
           'extras_as_string': True,
           'api_version': '2',
           'return_id_only': True})

        if self._site_user and context['user'] == self._site_user['name']:
            context['ignore_auth'] = True

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        if status == 'new':       
            # We need to explicitly provide a package ID based on uuid4 identifier created in gather_stage
            # won't be be able to link the extent to the package.
            package_dict['id'] = package_dict['identifier']

            # before_create interface
            for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                if hasattr(harvester, 'before_create'):
                    err = harvester.before_create(harvest_object, package_dict, self._local_schema, harvester_tmp_dict)
                
                    if err:
                        self._save_object_error(f'before_create error: {err}', harvest_object, 'Import')
                        return False
            
            try:
                result = self._create_or_update_package(
                    package_dict, harvest_object, 
                    package_dict_form='package_show')
                
                # after_create interface
                for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                    if hasattr(harvester, 'after_create'):
                        err = harvester.after_create(harvest_object, package_dict, harvester_tmp_dict)

                        if err:
                            self._save_object_error(f'after_create error: {err}', harvest_object, 'Import')
                            return False

            except p.toolkit.ValidationError as e:
                error_message = ', '.join(f'{k}: {v}' for k, v in e.error_dict.items())
                self._save_object_error(f'Validation Error: {error_message}', harvest_object, 'Import')
                return False

        elif status == 'change':
            # Check if the modified date is more recent
            if not self.force_import and previous_object and previous_object.metadata_modified_date and dateutil.parser.parse(harvest_object.metadata_modified_date) <= previous_object.metadata_modified_date:
                log.info('Package with GUID: %s unchanged, skipping...' % harvest_object.guid)
                return 'unchanged'
            else:
                log.info("Dataset dates - Harvest date: %s and Previous date: %s", harvest_object.metadata_modified_date, previous_object.metadata_modified_date if previous_object else 'None')
        
                # update_package_schema_for_update interface
                package_schema = logic.schema.default_update_package_schema()
                for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                    if hasattr(harvester, 'update_package_schema_for_update'):
                        package_schema = harvester.update_package_schema_for_update(package_schema)
                context['schema'] = package_schema
        
                package_dict['id'] = harvest_object.package_id
                
                try:
                    # before_update interface
                    for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                        if hasattr(harvester, 'before_update'):
                            err = harvester.before_update(harvest_object, package_dict, harvester_tmp_dict)
        
                            if err:
                                self._save_object_error(f'TableHarvester plugin error: {err}', harvest_object, 'Import')
                                return False
                    
                    result = self._create_or_update_package(
                        package_dict, harvest_object, 
                        package_dict_form='package_show')
        
                    # after_update interface
                    for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                        if hasattr(harvester, 'after_update'):
                            err = harvester.after_update(harvest_object, package_dict, harvester_tmp_dict)
        
                            if err:
                                self._save_object_error(f'TableHarvester plugin error: {err}', harvest_object, 'Import')
                                return False
        
                    log.info('Updated package %s with GUID: %s' % (package_dict["id"], harvest_object.guid))
                    
                except p.toolkit.ValidationError as e:
                    error_message = ', '.join(f'{k}: {v}' for k, v in e.error_dict.items())
                    self._save_object_error(f'Validation Error: {error_message}', harvest_object, 'Import')
                    return False
        
        return result