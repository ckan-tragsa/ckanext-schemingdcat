import logging
import json
import traceback
import dateutil
from urllib.parse import urlparse, urlunparse
from abc import ABC, abstractmethod
import uuid

from ckan import logic
import ckan.plugins as p
import ckan.model as model
from ckantoolkit import config
from ckan.model import Session
from ckan.logic.schema import default_create_package_schema
from ckan.lib.navl.validators import ignore_missing, ignore

from ckanext.harvest.logic.schema import unicode_safe
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra

from ckanext.schemingdcat.harvesters.base import SchemingDCATHarvester
from ckanext.schemingdcat.interfaces import ISchemingDCATHarvester, ISQLHarvester
from ckanext.schemingdcat.lib.sql_field_mapping import SqlFieldMappingValidator as FieldMappingValidator
from ckanext.schemingdcat.config import (
    AUX_TAG_FIELDS
)

log = logging.getLogger(__name__)


class DatabaseManager(ABC):
    _retry = 5
    
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def check_connection(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def execute_query(self, query):
        pass

class SchemingDCATSQLHarvester(SchemingDCATHarvester):
    """
    A base harvester for harvesting metadata from SQL databases using the SchemingDCAT extension.

    It extends the base `SchemingDCATHarvester` class.
    """

    db_manager = None
    _readme = "https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file"
    _database_types_supported = {
        'postgres': {
            'name': 'postgres',
            'title': 'PostgreSQL',
            'active': True,
        },
        'sqlite': {
            'name': 'sqlite',
            'title': 'SQLite',
            'active': False,
        }
    }
    _database_type = None
    _credentials = None
    _connection = None
    _engine = None
    _metadata = None
    _session = None
    _auth = True
    _queries = {}
    data = None
    config = None
    _field_mapping_info = {
        "dataset_field_mapping": {
            "required": True,
            "content_dicts": "datasets"
        },
        "distribution_field_mapping": {
            "required": False,
            "content_dicts": "distributions",
            "parent_resource_id": "dataset_id"
        },
        "datadictionary_field_mapping": {
            "required": False,
            "content_dicts": "datadictionaries",
            "parent_resource_id": "distribution_id"
        }
    }

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

        supported_types = {st['name'] for st in self._database_types_supported.values() if st['active']}

        # Check basic validation config
        self._set_basic_validate_config(config)
        
        # Instance sql_field_mapping validator
        field_mapping_validator = FieldMappingValidator()

        if 'database_type' in config:
            database_type = config_obj['database_type']
            log.debug("database_type: %s ", database_type)
            if not isinstance(database_type, str):
                raise ValueError('database_type must be a string')

            if database_type not in supported_types:
                raise ValueError(f'database_type should be one of: {", ".join(supported_types)}')

            config = json.dumps({**config_obj, 'database_type': database_type})

        else:
            raise ValueError(f'database_type should be one of: {", ".join(supported_types)}')

        if 'credentials' in config:   
            required_keys = ['user', 'password', 'host', 'port', 'db']  
            credentials = config_obj['credentials']
            
            if not isinstance(credentials, dict):
                raise ValueError('credentials must be a dictionary')
            
            for key in required_keys:
                if key not in credentials:
                    raise ValueError(f'credentials needs key "{key}"')
            
            if not isinstance(credentials['port'], int):
                raise ValueError('"port" must be an integer')
        else:
            raise ValueError("credentials must exist and be a dictionary with the following structure: {'user': 'username', 'password': 'password', 'host': 'hostname', 'port': port_number, 'db': 'database'}")

        # Check if 'field_mapping_schema_version' exists in the config
        field_mapping_schema_version_error_message = f'Insert the schema version: "field_mapping_schema_version: <version>", one of: {", ".join(map(str, self._field_mapping_validator_versions))} . More info: https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#remote-google-sheetonedrive-excel-metadata-upload-harvester'
        if 'field_mapping_schema_version' not in config_obj:
            raise ValueError(field_mapping_schema_version_error_message)
        else:
            # Check if is an integer and if it is in the versions
            if not isinstance(config_obj['field_mapping_schema_version'], int) or config_obj['field_mapping_schema_version'] not in self._field_mapping_validator_versions:
                raise ValueError(field_mapping_schema_version_error_message)

        # Validate if exists a JSON contained the mapping field_names between the remote schema and the local schema        
        for mapping_name, field_mapping in config_obj.items():
            if mapping_name in self._field_mapping_info:
                if not isinstance(field_mapping, dict):
                    raise ValueError(f'{mapping_name} must be a dictionary')

                parent_resource_id = self._field_mapping_info[mapping_name].get('parent_resource_id')

                # Check if parent_resource_id is in the field_mapping
                if parent_resource_id and parent_resource_id not in field_mapping:
                    raise ValueError(f'"{parent_resource_id}" is mandatory for "{mapping_name}". It represents the id of the record to which it is appended.')

                schema_version = config_obj['field_mapping_schema_version']

                try:
                    # Validate field_mappings according to schema versions
                    field_mapping = field_mapping_validator.validate(field_mapping, schema_version)
                except ValueError as e:
                    raise ValueError(f"The field mapping is invalid: {e}") from e

                config = json.dumps({**config_obj, mapping_name: field_mapping})

    def gather_stage(self, harvest_job):
        """
        This method is responsible for reading the remote SQL database. The contents are then processed, cleaned, and added to the database.

        Args:
            harvest_job (HarvestJob): The harvest job object.

        Returns:
            list: A list of object IDs for the harvested datasets.
        """
        # Get file contents of source url
        harvest_source_title = harvest_job.source.title
        source_url = harvest_job.source.url    
        content_dicts = {}
        self._names_taken = []
        
        log.debug('In SchemingDCATSQLHarvester gather_stage with harvest source: %s and database URL: %s', harvest_source_title, source_url)
        
        # Get config options
        if harvest_job.source.config:
            self._set_config(harvest_job.source.config)
            self.get_harvester_basic_info(harvest_job.source.config)

        log.debug('Using config: %r', self._secret_properties(self.config))
        
        if self.config:
            self._database_type = self.config.get("database_type")
            self._auth = self.config.get("auth")
            self._credentials = self.config.get("credentials")
            credential_keys = ', '.join(self._credentials .keys())
            log.debug('Loaded credentials with keys: %s', credential_keys)
            dataset_id_colname = self.config.get("dataset_id_colname", "dataset_id")
        else:
            err_msg = f'The credentials are not provided. The harvest source: "{harvest_source_title}" has finished.'
            log.error(err_msg)
            self._save_gather_error(f'{err_msg}', harvest_job)
            return []

        # Check if the host and port in the credentials match the ones in the URL
        is_valid = self._validate_source_url(harvest_job, source_url)
        
        if not is_valid:
            log.error('The host and port in the credentials do not match the ones in the source URL. The harvest source: "%s" has finished.', harvest_source_title)
            return []
        
        log.debug('Database type: %s', self._database_type)

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
        
        # Get database url from credentials and database_type
        conn_url = self._generate_conn_url()
                
        # Call the routing function with the credentials
        log.debug("Starting database remote schema harvest: %s", self.obfuscate_credentials_in_url(conn_url))
    
        # Check if the content_dicts colnames correspond to the local schema
        try:
            # Standardizes the field_mapping           
            field_mappings = {
            'dataset_field_mapping': self._standardize_field_mapping(self.config.get("dataset_field_mapping")),
            'distribution_field_mapping': self._standardize_field_mapping(self.config.get("distribution_field_mapping")),
            'datadictionary_field_mapping': None
        }

        except RemoteSchemaError as e:
            self._save_gather_error('Error standardize field mapping: {0}'.format(e), harvest_job)
            return []

        # before_sql_retrieve interface
        for harvester in p.PluginImplementations(ISQLHarvester):
            if hasattr(harvester, 'before_sql_retrieve'):
                field_mappings, before_sql_retrieve_errors = harvester.before_sql_retrieve(field_mappings, conn_url, harvest_job)
                        
                for error_msg in before_sql_retrieve_errors:
                    self._save_gather_error(error_msg, harvest_job)
                        
                if not field_mappings:
                    return []

        # Read database
        if self.db_manager is not None:
            self.db_manager.check_connection(conn_url)
            log.debug('Connection is ready.')
            content_dicts = self._read_remote_database(field_mappings, conn_url)
            #log.debug('content_dicts %s', content_dicts)
                 
        # after_sql_retrieve interface
        for harvester in p.PluginImplementations(ISQLHarvester):
            if hasattr(harvester, 'after_sql_retrieve'):
                content_dicts, after_sql_retrieve_errors = harvester.after_sql_retrieve(content_dicts, harvest_job)
                        
                for error_msg in after_sql_retrieve_errors:
                    self._save_gather_error(error_msg, harvest_job)
                        
                if not content_dicts:
                    return []

        # Create default values dict from config mappings.
        try:
            self.create_default_values(field_mappings)
    
        except ReadError as e:
            self._save_gather_error('Error generating default values for dataset/distribution config field mappings: {0}'.format(e), harvest_job)
        
        # Check if the content_dicts colnames correspond to the local schema
        try:
            #log.debug('content_dicts: %s', content_dicts)
            # Standardizes the field names
            content_dicts['datasets'], remote_dataset_field_mapping = self._standardize_df_fields_from_field_mapping(content_dicts['datasets'], field_mappings.get('dataset_field_mapping'))
            content_dicts['distributions'], remote_distribution_field_mapping = self._standardize_df_fields_from_field_mapping(content_dicts['distributions'], field_mappings.get('distribution_field_mapping'))
            
            # Validate field names
            remote_dataset_field_names = set(content_dicts['datasets'].columns)
            remote_resource_field_names = set(content_dicts['distributions'].columns)

            self._validate_remote_schema(remote_dataset_field_names=remote_dataset_field_names, remote_ckan_base_url=None, remote_resource_field_names=remote_resource_field_names, remote_dataset_field_mapping=remote_dataset_field_mapping, remote_distribution_field_mapping=remote_distribution_field_mapping)

        except RemoteSchemaError as e:
            self._save_gather_error('Error validating remote schema: {0}'.format(e), harvest_job)
            return []
        
        # before_cleaning interface
        for harvester in p.PluginImplementations(ISQLHarvester):
            if hasattr(harvester, 'before_cleaning'):
                content_dicts, before_cleaning_errors = harvester.before_cleaning(content_dicts, harvest_job, self.config)

                for error_msg in before_cleaning_errors:
                    self._save_gather_error(error_msg, harvest_job)

        # Clean tables
        try:
            clean_datasets = self._process_content(content_dicts, conn_url, field_mappings)
            log.debug('"%s" remote database cleaned successfully.', self._database_types_supported[self._database_type]['title'])
            clean_datasets = self._update_dict_lists(clean_datasets)
            #log.debug('clean_datasets: %s', clean_datasets)
            log.debug('Update dict string lists. Number of datasets imported: %s', len(clean_datasets))
            
        except Exception as e:
            self._save_gather_error('Error cleaning the remote database: {0}'.format(e), harvest_job)
            return []
    
        # after_cleaning interface
        for harvester in p.PluginImplementations(ISQLHarvester):
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
            if not self.force_import and previous_object and dateutil.parser.parse(harvest_object.metadata_modified_date) <= previous_object.metadata_modified_date:
                log.info('Package with GUID: %s unchanged, skipping...' % harvest_object.guid)
                return 'unchanged'
            else:
                log.info("Dataset dates - Harvest date: %s and Previous date: %s", harvest_object.metadata_modified_date, previous_object.metadata_modified_date)

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

    #TODO: método para crear/actualizar los datasets e importado por otros harvesters
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
        log.debug('In SchemingDCATSQLHarvester _create_or_update_package')
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
                            and dateutil.parser.parse(resource["modified"]) > dateutil.parser.parse(existing_resources[resource["url"]])
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

    # DB methods
    def _save_queries(self):
        raise NotImplementedError("The _save_queries method must be defined in the subclass for the specific database type: {}".format(self._database_type))

    def _build_query(self):
        raise NotImplementedError("The _build_query method must be defined in the subclass for the specific database type: {}".format(self._database_type))
            
    # Harvester
    def _standardize_field_mapping(self, field_mapping):
        """
        Standardizes the field_mapping based on the schema version of SqlFieldMappingValidator.

        Args:
            field_mapping (dict): A dictionary mapping the current column names to the desired column names.

        Returns:
            dict: The standardized field_mapping.
        """
        if field_mapping is not None:
            schema_version = self.config.get("field_mapping_schema_version", 1)
            if schema_version not in self._field_mapping_validator_versions:
                raise ValueError(f"Unsupported schema version: {schema_version}")
        
        return field_mapping
    
    def _validate_source_url(self, harvest_job, source_url):
        """
        Validates the source URL against the host and port in the credentials.

        This method parses the source URL to extract the host and port. It then checks if these match the host and port in the credentials. If they do not match, it saves an error message and returns False. If a key is missing in the credentials, it also saves an error message and returns False.

        Args:
            harvest_job (HarvestJob): The harvest job object.
            source_url (str): The source URL to validate.

        Returns:
            bool: True if the host and port in the credentials match the ones in the source URL, False otherwise.
        """
        try:
            # Parse the source URL
            parsed_url = urlparse(source_url)

            # Extract the host and port from the URL
            url_host = parsed_url.hostname
            url_port = parsed_url.port if parsed_url.port else 80  # Default to port 80 if no port is specified in the URL

            # Check if the host and port in the credentials match the ones in the URL
            if self._credentials['host'] != url_host or str(self._credentials['port']) != str(url_port):
                msg = f'The source URL: "{source_url}" and the credentials URI: "http://{self._credentials["host"]}:{self._credentials["port"]}" are not the same. Check the credentials dict.'
                self._save_gather_error(msg, harvest_job)
                return False
        except KeyError as e:
            msg = f"Missing key in credentials: {e}"
            self._save_gather_error(msg, harvest_job)
            return False

        return True

    # Clean datasets
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

    def _clean_table_distributions(self, data, dataset_id_colname='dataset_id'):
        """
        Clean the table distributions data.

        Args:
            data (pandas.DataFrame): The table distributions data.
            dataset_id_colname (str, optional): The column name representing the dataset ID. Defaults to 'dataset_id'.

        Returns:
            dict or None: A dictionary containing the cleaned distributions data grouped by dataset_id,
            or None if no distributions are loaded.
        """
        if dataset_id_colname is None:
            dataset_id_colname = 'dataset_id'

        # Select only the columns of type 'object' and apply the strip() method to them
        data.loc[:, data.dtypes == object] = data.select_dtypes(include=['object']).apply(lambda x: x.str.strip())

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
        """
        try:
            return [
                {
                    **d,
                    'resources': [
                        {**dr, 'datadictionaries': table_datadictionaries_grouped.get(dr[datadictionary_id_field], []) if table_datadictionaries_grouped else []}
                        for dr in table_distributions_grouped.get(
                            d.get(identifier_field) or d.get(alternate_identifier_field) or d.get(inspire_id_field), []
                        )
                    ]
                }
                for d in table_datasets
            ]
        except Exception as e:
            log.error("Error while adding distributions and datadictionaries to datasets: %s", str(e))
            raise

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
                if key in list_fields and isinstance(value, str):
                    element[key] = self._set_string_to_list(value)
                elif key == 'distributions':
                    for distribution in value:
                        for key_dist, value_dist in distribution.items():
                            if key_dist in list_fields and isinstance(value_dist, str):
                                distribution[key_dist] = self._set_string_to_list(value_dist)

        # Return the updated data
        return data

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

    @staticmethod
    def obfuscate_credentials_in_url(conn_url):
        """
        Obfuscates the username and password in a connection URL for safe logging.

        Args:
            conn_url (str): The original connection URL containing sensitive information.

        Returns:
            str: The connection URL with the username and password obfuscated.

        Example:
            >>> obfuscate_credentials_in_url("postgresql://user:password@localhost:5432/my_database")
            'postgresql://****:****@localhost:5432/my_database'
        """
        parts = urlparse(conn_url)

        obfuscated_netloc = parts.netloc.replace(parts.username, '****', 1).replace(parts.password, '****', 1) if parts.username and parts.password else parts.netloc
        obfuscated_parts = parts._replace(netloc=obfuscated_netloc)

        return urlunparse(obfuscated_parts)

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