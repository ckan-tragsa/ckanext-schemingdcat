import json
import logging
import traceback
import uuid
import dateutil
import time
import pprint

import ckan.plugins as p
from ckan import model
from ckan.logic import NotFound, get_action
from ckan import logic

from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
from ckanext.spatial.harvesters.csw import CSWHarvester

from ckanext.dcat.processors import RDFParserException, RDFParser

from ckanext.schemingdcat.harvesters.base import (
    SchemingDCATHarvester,
    RemoteSchemaError,
    ReadError,
)
from ckanext.schemingdcat.lib.csw.processor import SchemingDCATCatalogueServiceWeb
from ckanext.schemingdcat.lib.csw.csw_metadata_extractor import CSWMetadataExtractor
from ckanext.schemingdcat.lib.csw.csw_harvester_utils import (
    is_valid_url,
    get_organization_slug_for_harvest_source,
    check_existing_package_by_identifier
)
from ckanext.schemingdcat.config import (
    OGC2CKAN_HARVESTER_MD_CONFIG,
    XLST_MAPPINGS_DIR,
    DEFAULT_XSLT_FILE,
    CQL_QUERY_DEFAULT,
    INSPIRE_HVD_CATEGORY,
    INSPIRE_HVD_APPLICABLE_LEGISLATION,
    PROTOCOL_MAPPING,
    FORMAT_STANDARDIZATION
)
from ckanext.schemingdcat.lib.csw_mapper.xslt_transformer import XSLTTransformer
from ckanext.schemingdcat.lib.field_mapping import FieldMappingValidator
from ckanext.schemingdcat.interfaces import ISchemingDCATHarvester
from ckanext.schemingdcat.helpers import schemingdcat_get_dataset_schema_required_field_names,  schemingdcat_get_dataset_schema_field_names, schemingdcat_get_ckan_site_url

log = logging.getLogger(__name__)

CSW_HARVESTER_TYPES = ['xsl', 'owslib']
DEFAULT_CSW_HARVESTER_TYPE = 'owslib'
DEFAULT_RDF_PROFILES = ['eu_geodcat_ap_3']
DEBUG_MODE = p.toolkit.asbool(p.toolkit.config.get('debug', False))

class SchemingDCATCSWHarvester(CSWHarvester, SchemingDCATHarvester):
    '''
    An expanded Harvester for CSW servers using XLST mapping ([ISO19139 to DCAT-AP](https://raw.githubusercontent.com/mjanez/iso-19139-to-dcat-ap/refs/heads/main/iso-19139-to-dcat-ap.xsl)) to transform the metadata to RDF (DCAT-AP) and import it into CKAN.
    '''
    
    def info(self):
        return {
            'name': 'schemingdcat_csw',
            'title': 'CSW INSPIRE ISO-19139 endpoint',
            'description': 'Harvester for CSW INSPIRE-GeoDCAT-AP dataset descriptions ' +
                           'serialized as XML metadata according to the INSPIRE ISO 19139 standard.',
            'about_url': 'https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#csw-inspire-iso-19139-endpoint'
        }
        
    csw = None
    existing_dataset_identifiers = []
    _names_taken = []
    _schema_required_fields = []

    def validate_config(self, config):
        config_obj = self.get_harvester_basic_info(config)

        # Check basic validation config
        self._set_basic_validate_config(config)

        # Instance field_mapping validator
        field_mapping_validator = FieldMappingValidator()

        # Check SSL verification configuration
        if "ssl_verify" in config_obj:
            if not isinstance(config_obj["ssl_verify"], bool):
                config = json.dumps({**config_obj, "ssl_verify": True})
        else:
            config = json.dumps({**config_obj, "ssl_verify": True})

        # Add private_datasets validation
        if 'private_datasets' in config_obj:
            if not isinstance(config_obj['private_datasets'], bool):
                raise ValueError('private_datasets must be "True" or "False"')
        else:
            config_obj['private_datasets'] = True

        if 'cql_query' in config_obj:
            cql_query = config_obj['cql_query']
            if cql_query is not None:
                if not isinstance(cql_query, str):
                    raise ValueError('cql_query must be a string or null')
        else:
            log.debug('No cql_query provided. Using default: %s', CQL_QUERY_DEFAULT)
            config_obj['cql_query'] = CQL_QUERY_DEFAULT

        if 'cql_search_term' in config_obj:
            if config_obj['cql_search_term'] is not None and not isinstance(config_obj['cql_search_term'], str):
                raise ValueError('cql_search_term must be a string or null')

        if 'cql_use_like' in config_obj:
            if not isinstance(config_obj['cql_use_like'], bool):
                raise ValueError('cql_use_like must be boolean')
        
        if 'legal_basis_url' in config_obj:
            if config_obj['legal_basis_url'] is not None and not is_valid_url(config_obj['legal_basis_url']):
                raise ValueError('legal_basis_url must be a valid URL or null')

        #TODO: Add `xsl` csw_harvest_type when becomes available
        if 'csw_harvest_type' in config_obj:
            if config_obj['csw_harvest_type'] not in CSW_HARVESTER_TYPES:
                raise ValueError('csw_harvest_type must be one of the following: %s' % ', '.join(CSW_HARVESTER_TYPES))
            elif config_obj['csw_harvest_type'] == 'xsl':
                raise NotImplementedError(
                    "XSLT-based harvesting is currently disabled. This functionality will remain disabled until the official ISO19139 to DCAT-AP XSLT (https://github.com/SEMICeu/iso-19139-to-dcat-ap) becomes available."
                )
        else:
            # Default to owslib if not specified
            config_obj['csw_harvest_type'] = DEFAULT_CSW_HARVESTER_TYPE

        if 'csw_mapping_file' in config_obj:
            csw_mapping_file = config_obj['csw_mapping_file']
            if csw_mapping_file is not None:
                if not isinstance(csw_mapping_file, str):
                    raise ValueError('csw_mapping_file must be a string or null')
                if not is_valid_url(csw_mapping_file) and not csw_mapping_file.endswith('.xsl'):
                    raise ValueError('csw_mapping_file must be a valid URL or a filename ending with .xsl')
        else:
            log.debug('No csw_mapping_file provided. Using default: %s', DEFAULT_XSLT_FILE)
            config_obj['csw_mapping_file'] = DEFAULT_XSLT_FILE

        if 'delete_missing_datasets' in config_obj:
            if not isinstance(config_obj['delete_missing_datasets'], bool):
                raise ValueError('delete_missing_dataset must be boolean')

        if 'override_local_datasets' in config_obj:
            if not isinstance(config_obj['override_local_datasets'], bool):
                raise ValueError('override_local_datasets must be boolean')

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

        # Check if 'field_mapping_schema_version' exists in the config
        field_mapping_schema_version_error_message = f'Insert the schema version: "field_mapping_schema_version: <version>", one of: {", ".join(map(str, self._field_mapping_validator_versions))} . More info: https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#remote-google-sheetonedrive-excel-metadata-upload-harvester'
        if 'field_mapping_schema_version' not in config_obj and 'dataset_field_mapping' in config_obj:
            raise ValueError(field_mapping_schema_version_error_message)
        else:
            # Check if is an integer and if it is in the versions
            if not isinstance(config_obj['field_mapping_schema_version'], int) or config_obj['field_mapping_schema_version'] not in self._field_mapping_validator_versions:
                raise ValueError(field_mapping_schema_version_error_message)

        # Check for field_name/field_position in dataset and distribution mappings and show warnings
        field_mapping_types = ['dataset_field_mapping', 'distribution_field_mapping']
        for mapping_type in field_mapping_types:
            if mapping_type in config_obj and isinstance(config_obj[mapping_type], dict):
                has_field_name_or_position = False
                
                # Function to check for field_name/field_position in a mapping dict
                def check_for_field_name_or_position(mapping):
                    if isinstance(mapping, dict):
                        if 'field_name' in mapping or 'field_position' in mapping:
                            return True
                        if 'languages' in mapping and isinstance(mapping['languages'], dict):
                            for lang_config in mapping['languages'].values():
                                if isinstance(lang_config, dict) and ('field_name' in lang_config or 'field_position' in lang_config):
                                    return True
                    return False
                
                # Check all fields in the mapping
                for field, field_config in config_obj[mapping_type].items():
                    if check_for_field_name_or_position(field_config):
                        has_field_name_or_position = True
                        break
                
                # Show warning if field_name or field_position are found
                if has_field_name_or_position:
                    raise ValueError(
                        f"Warning: '{mapping_type}' contains 'field_name' or 'field_position' properties. "
                        "Note that only 'field_value' properties will be used as default values in CSW harvester. "
                        "The 'field_name' and 'field_position' properties will be ignored. More info about Field mapping structure: https://github.com/mjanez/ckanext-schemingdcat#field-mapping-structure-sheets-harvester"
                    )

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

        if 'private_datasets' in config_obj:
            if not isinstance(config_obj['private_datasets'], bool):
                raise ValueError('private_datasets must be boolean')
        else:
            config_obj['private_datasets'] = True  # default value

        return config
    
    def _set_config(self, config_str, harvest_source_id):
        """
        Set the harvester configuration and extract default values from field mappings.
        Ensures safe default values even if errors occur during processing.
        
        Args:
            config_str (str): JSON configuration string
            harvest_source_id (str): Harvest source identifier
            
        Returns:
            None
        """
        # Initialize empty config with safe defaults
        self.config = {}
        self.config['config_default_values'] = {
            'dataset': {},
            'distribution': {}
        }
    
        # Parse config if provided
        if config_str:
            try:
                self.config = json.loads(config_str)
            except json.JSONDecodeError as e:
                log.error('Invalid JSON configuration: %s', str(e))
                return
    
        # Set organization
        try:
            organization_slug = get_organization_slug_for_harvest_source(harvest_source_id)
            self.config['organization'] = organization_slug
        except Exception as e:
            log.error('Error getting organization: %s', str(e))
       
        # Generate field mappings from config
        if not any(key in self.config for key in ['dataset_field_mapping', 'distribution_field_mapping']):
            log.debug('No field mappings found in configuration')
            return
            
        try:
            # Standardize the field_mapping           
            field_mappings = {
                'dataset_field_mapping': self._standardize_field_mapping(
                    self.config.get("dataset_field_mapping", {})
                ),
                'distribution_field_mapping': self._standardize_field_mapping(
                    self.config.get("distribution_field_mapping", {})
                ),
                'datadictionary_field_mapping': None
            }
            
            # Extract default values from field mappings
            extracted_defaults = {
                "dataset": self._field_mapping_extract_default_values(
                    field_mappings.get('dataset_field_mapping', {})
                ),
                "distribution": self._field_mapping_extract_default_values(
                    field_mappings.get('distribution_field_mapping', {})
                )
            }
            
            # Only update if we successfully extracted values
            if extracted_defaults['dataset'] or extracted_defaults['distribution']:
                self.config['config_default_values'] = extracted_defaults
                log.debug('Generated default values from field mappings: %s', 
                         self.config['config_default_values'])
    
        except RemoteSchemaError as e:
            log.error('Error standardizing field mapping: %s', str(e))
    
        except ReadError as e:
            log.error('Error generating default values from field mappings: %s', str(e))
    
        except Exception as e:
            log.error('Unexpected error processing field mappings: %s', str(e))
        
        log.debug('Using final config: %r', self.config)
    
    def modify_package_dict(self, package_dict, harvest_object):
        '''
        Allows custom harvesters to modify the package dict before
        creating or updating the actual package.
        '''
        log.debug('In SchemingDCATCSWHarvester modify_package_dict')
    
        # Assign HVD category
        package_dict = self.normalize_inspire_hvd_category(package_dict)
    
        # Standarize resources (dcat:Distribution)
        for resource in package_dict.get("resources", []):
            format_value = resource.get('format')
            
            if format_value:
                format_name, mimetype = self._clean_format(format_value)
                if format_name:
                    resource['format'] = format_name
                    if mimetype:
                        resource['mimetype'] = mimetype
                else:
                    resource.pop('format', None)
                    resource.pop('mimetype', None)
    
        # First apply field_mapping default values (higher priority)
        package_dict = self._apply_field_mapping_default_values(package_dict)
        
        # Then apply general default values for required fields that are still empty
        self._apply_default_values(package_dict)
        
        package_dict['private'] = self.config.get('private_datasets', True)
    
        return package_dict

    def gather_stage(self, harvest_job):
        """Harvests CSW records using specified method"""
        self._set_config(harvest_job.source.config, harvest_job.source.id)
        
        harvest_type = self.config.get('csw_harvest_type', 'owslib')
        
        if harvest_type == 'xsl':
            log.warning(
                "XSLT-based harvesting is currently disabled. This functionality will remain disabled until the official ISO19139 to DCAT-AP XSLT (https://github.com/SEMICeu/iso-19139-to-dcat-ap) becomes available."
            )
            raise NotImplementedError(
                "XSLT-based harvesting is currently disabled. This functionality will remain disabled until the official ISO19139 to DCAT-AP XSLT (https://github.com/SEMICeu/iso-19139-to-dcat-ap) becomes available."
            )
        else:
            return self._gather_with_owslib(harvest_job)

    def _gather_with_owslib(self, harvest_job):
        """
        Performs the gather stage of the SchemingDCATCSWHarvester. This method is responsible for accesing the CSW Catalog and reading its contents. The contents are then processed, cleaned, and added to the database.

        Args:
            harvest_job (HarvestJob): The harvest job object.

        Returns:
            list: A list of object IDs for the harvested datasets.
        """
        # Get file contents of source url
        harvest_source_title = harvest_job.source.title
        csw_url = harvest_job.source.url.rstrip("/")

        log.debug('In SchemingDCATCSWHarvester OWSLib-gather_stage with harvest source: %s and URL: %s', harvest_source_title, csw_url)
        self._set_config(harvest_job.source.config, harvest_job.source.id)

        try:
            # Get SSL verification setting from config (default to True)
            ssl_verify = self.config.get("ssl_verify", True)
            if not ssl_verify:
                log.warning('SSL Verify is set to False. SSL certificate verification is disabled.')

            csw_client = SchemingDCATCatalogueServiceWeb(url=csw_url, ssl_verify=ssl_verify)
            csw_extractor = CSWMetadataExtractor(debug=DEBUG_MODE)
            gathered_identifiers = csw_client.get_csw_records(
                cql=self.config.get('cql', None),
                cql_query=self.config.get('cql_query', None),
                cql_search_term=self.config.get('cql_search_term', None),
                cql_use_like=self.config.get('cql_use_like', False)
            )

            # Limit to first 25 records for testing
            if DEBUG_MODE:
                gathered_identifiers = gathered_identifiers[:25]
                log.debug('Limited to first 25 records for testing')

        except KeyError as e:
            # Handling the case of a missing key in self.config
            missing_key = e.args[0]
            self._save_gather_error(
                'Configuration error: Missing required configuration key "{}"'.format(missing_key),
                harvest_job
            )
            return []
        except Exception as e:
            self._save_gather_error(
                'Unable to get content for URL: {}: {} / {}'.format(csw_url, str(e), traceback.format_exc()),
                harvest_job
            )
            return []

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

        log.debug('Extract CSW XML records using OWSLib')
        
        parser_datasets = []
        
        # Extract CSW XML records using OWSLib
        for id in gathered_identifiers:
            try:
                log.debug("Fetching CSW record for ID: %s", id)
                csw_metadata, csw_record_xml = csw_client.get_metadata_record(id)
                
                # Extract all metadata
                complete_metadata = csw_extractor.extract_from_csw(csw_metadata, csw_record_xml)
                
                for harvester in p.PluginImplementations(SchemingDCATHarvester):
                    complete_metadata, after_parsing_errors = harvester.after_parsing(complete_metadata, harvest_job)

                    for error_msg in after_parsing_errors:
                        self._save_gather_error(error_msg, harvest_job)
                

                parser_datasets.append(complete_metadata)
                log.debug('Append record: %s', complete_metadata.get('title'))

                if not complete_metadata:
                    return None

            except Exception as e:
                self._save_gather_error(f'Error processing record {id}: {str(e)}', harvest_job)
                continue

        dataset_titles = [dataset['title'] for dataset in parser_datasets]

        # Log the length of datasets after parser
        if DEBUG_MODE:
            log.debug('parser_datasets: %s', dataset_titles)
        log.debug(f"Length of parser after_cleaning ISQLHarvester: {len(parser_datasets)}")

        # Add datasets to the database
        try:
            log.debug('Adding datasets to DB')
            datasets_to_harvest = {}
            source_dataset = model.Package.get(harvest_job.source.id)
            skipped_datasets = 0  # Counter for omitted datasets
            identifier_counts = {}  # To track the frequency of identifiers

            for dataset in parser_datasets:
                #log.debug('dataset: %s', dataset['title'])

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
                        
                    else:
                        dataset['identifier'] = self._clean_identifier(dataset['identifier'])
        
                except Exception as e:
                    skipped_datasets += 1
                    self._save_gather_error('Error for the dataset identifier %s [%r]' % (dataset.get('identifier'), e), harvest_job)
                    continue
                
                if not dataset.get('identifier'):
                    skipped_datasets += 1
                    self._save_gather_error('Missing identifier for dataset with title: %s' % dataset.get('title'), harvest_job)
                    continue
                
                # If exists identifier, add Metadata URL to references
                if dataset.get('identifier'):
                    # Build GetRecordById URL
                    getrecord_params = {
                        'service': 'CSW',
                        'version': '2.0.2',
                        'request': 'GetRecordById',
                        'id': dataset['identifier'],
                        'elementSetName': 'full',
                        'outputSchema': 'http://www.isotc211.org/2005/gmd',
                        'OutputFormat': 'application/xml'
                    }
                    
                    # Convert params to URL query string
                    query_string = '&'.join([f"{k}={v}" for k, v in getrecord_params.items()])
                    csw_url_reference = f"{csw_url}?{query_string}"
                    
                    # Append as first element
                    dataset['reference'].insert(0, csw_url_reference)            
                
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
        
        log.debug('Number of elements in parser_datasets: %s and object_ids: %s', len(parser_datasets), len(ids))
        
        # Log parser_datasets/ ids
        #self._log_export_parser_datasets_and_ids(harvest_source_title, parser_datasets, ids)

        return [id_dict['id'] for id_dict in ids]

    #TODO: Disable until https://github.com/SEMICeu/iso-19139-to-dcat-ap
    def _gather_with_xsl(self, harvest_job):
        """
        Performs the gather stage of the SchemingDCATCSWHarvester. This method is responsible for accessing the CSW Catalog and reading its contents. The contents are then processed, cleaned, and added to the database.
  
        The method performs the following steps:
        1. Retrieves the CSW URL and configuration settings.
        2. Connects to the CSW service and gathers record identifiers.
        3. Transforms the CSW records using XSLT mappings.
        4. Parses the transformed records into RDF datasets.
        5. Adds the datasets to the database, handling new, changed, and deleted records.
        6. Logs relevant information and errors throughout the process.

        Args:
            harvest_job (HarvestJob): The harvest job object.

        Raises:
            KeyError: If a required configuration key is missing.
            Exception: If there is an error during the gathering or processing of the CSW records.

        Returns:
            list: A list of object IDs for the harvested datasets.
        """
        # Get file contents of source url
        harvest_source_title = harvest_job.source.title
        csw_url = harvest_job.source.url.rstrip("/")

        log.debug('In SchemingDCATCSWHarvester XSLT-gather_stage with harvest source: %s and URL: %s', harvest_source_title, csw_url)
        self._set_config(harvest_job.source.config, harvest_job.source.id)
        
        try:
            # Obtain required configuration values
            ssl_verify = self.config['ssl_verify']
            csw_mapping_file = self.config.get('csw_mapping_file', None)
            if not ssl_verify:
                log.warning('SSL Verify is set to False. SSL certificate verification is disabled.')

            csw_client = SchemingDCATCatalogueServiceWeb(url=csw_url, ssl_verify=ssl_verify)
            gathered_identifiers = csw_client.get_csw_records(
                cql=self.config.get('cql', None),
                cql_query=self.config.get('cql_query', None),
                cql_search_term=self.config.get('cql_search_term', None),
                cql_use_like=self.config.get('cql_use_like', False)
            )

            # Limit to first 20 records for testing
            if DEBUG_MODE:
                gathered_identifiers = gathered_identifiers[:20]
                log.debug('Limited to first 20 records for testing')

        except KeyError as e:
            # Handling the case of a missing key in self.config
            missing_key = e.args[0]
            self._save_gather_error(
                'Configuration error: Missing required configuration key "{}"'.format(missing_key),
                harvest_job
            )
            return []
        except Exception as e:
            self._save_gather_error(
                'Unable to get content for URL: {}: {} / {}'.format(csw_url, str(e), traceback.format_exc()),
                harvest_job
            )
            return []

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

        # Transform the CSW records RDF datasets based on the XSLT mappings
        try:
            transformer = XSLTTransformer(csw_mapping_file, DEBUG_MODE)
        except FileNotFoundError as e:
            self._save_gather_error(
                f'Configuration error: The file "{csw_mapping_file}" does not exist in the XLST mappings directory "{XLST_MAPPINGS_DIR}". {str(e)}',
                harvest_job
            )
            return []
        except Exception as e:
            self._save_gather_error(
                'Unable transform the XSLT: {}: {} / {}'.format(csw_mapping_file, str(e), traceback.format_exc()),
                harvest_job
            )
            return []

        self._names_taken = []
        
        parser = RDFParser()
        log.debug('Load profiles TO RDFParser: %s', DEFAULT_RDF_PROFILES)
        parser._profiles = parser._load_profiles(DEFAULT_RDF_PROFILES)

        # Transform CSW XML records to RDF
        for id in gathered_identifiers:
            try:
                csw_record_xml = csw_client.get_record_by_id(id)
                transformed_xml = transformer.transform(csw_record_xml)
                try:
                    parser.parse(transformed_xml, _format='xml')
                except RDFParserException as e:
                    self._save_gather_error('Error parsing the RDF file: {0}'.format(e), harvest_job)
                    return []

                for harvester in p.PluginImplementations(SchemingDCATHarvester):
                    parser, after_parsing_errors = harvester.after_parsing(parser, harvest_job)

                    for error_msg in after_parsing_errors:
                        self._save_gather_error(error_msg, harvest_job)

                if not parser:
                    return []

            except Exception as e:
                self._save_gather_error(f'Error processing record {id}: {str(e)}', harvest_job)
                continue

        parser_datasets = list(parser.datasets())
        dataset_titles = [dataset['title'] for dataset in parser_datasets]

        # Log the length of datasets after parser
        if DEBUG_MODE:
            log.debug('parser.datasets: %s', dataset_titles)
        log.debug(f"Length of parser after_cleaning ISQLHarvester: {len(parser_datasets)}")

        # Add datasets to the database
        try:
            log.debug('Adding datasets to DB')
            datasets_to_harvest = {}
            source_dataset = model.Package.get(harvest_job.source.id)
            skipped_datasets = 0  # Counter for omitted datasets
            identifier_counts = {}  # To track the frequency of identifiers

            for dataset in parser_datasets:
                #log.debug('dataset: %s', dataset['title'])

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
                        
                    else:
                        dataset['identifier'] = self._clean_identifier(dataset['identifier'])
        
                except Exception as e:
                    skipped_datasets += 1
                    self._save_gather_error('Error for the dataset identifier %s [%r]' % (dataset.get('identifier'), e), harvest_job)
                    continue
                
                if not dataset.get('identifier'):
                    skipped_datasets += 1
                    self._save_gather_error('Missing identifier for dataset with title: %s' % dataset.get('title'), harvest_job)
                    continue
                
                if not dataset.get('reference') and dataset.get('identifier'):
                    # Build GetRecordById URL
                    getrecord_params = {
                        'service': 'CSW',
                        'version': '2.0.2',
                        'request': 'GetRecordById',
                        'id': dataset['identifier'],
                        'elementSetName': 'full',
                        'outputSchema': 'http://www.isotc211.org/2005/gmd',
                        'OutputFormat': 'application/xml'
                    }
                    
                    # Convert params to URL query string
                    query_string = '&'.join([f"{k}={v}" for k, v in getrecord_params.items()])
                    dataset['reference'] = f"{csw_url}?{query_string}"
                    log.debug(f"Added CSW reference URL: {dataset['reference']}")
                    
                
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
        
        log.debug('Number of elements in parser_datasets: %s and object_ids: %s', len(parser_datasets), len(ids))
        
        # Log parser_datasets/ ids
        #self._log_export_parser_datasets_and_ids(harvest_source_title, parser_datasets, ids)

        return [id_dict['id'] for id_dict in ids]
  
    def fetch_stage(self, harvest_object):
        # Nothing to do here - we got the package dict in the search in the gather stage
        return True

    def import_stage(self, harvest_object):
        """
        Performs the import stage of the SchemingDCATCSWHarvester.

        Args:
            harvest_object (HarvestObject): The harvest object to import.

        Returns:
            bool or str: Returns True if the import is successful, 'unchanged' if the package is unchanged,
                        or False if there is an error during the import.

        Raises:
            None
        """
        log.debug('In SchemingDCATCSWHarvester import_stage')

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
        
        self._set_config(harvest_object.source.config, harvest_object.source.id)
        
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

        self._schema_required_fields = schemingdcat_get_dataset_schema_required_field_names()
        
        if DEBUG_MODE:
            log.debug('Schema required fields: %s', self._schema_required_fields)

        # before_modify_package_dict interface
        for harvester in p.PluginImplementations(ISchemingDCATHarvester):
            if hasattr(harvester, 'before_modify_package_dict'):
                dataset, before_modify_package_dict_errors = harvester.before_modify_package_dict(dataset)

                for err in before_modify_package_dict_errors:
                    self._save_object_error(f'before_modify_package_dict error: {err}', harvest_object, 'Import')
                    return False

        # Improve the package_dict from GeoDCAT-AP to CKAN
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
        
        if DEBUG_MODE:
            log.debug('import_stage result package_dict: %s', package_dict)
        
        return result

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

    # Aux methods
    def _get_existing_datasets(self, gathered_identifiers):
        """Check if datasets with the given identifiers exist and add them to existing_dataset_identifiers.
    
        Args:
            gathered_identifiers (list): List of dataset identifiers to check.
    
        Returns:
            None
    
        This method iterates over the gathered identifiers, checks if a dataset with the same identifier
        exists in the CKAN instance, and if it does, adds it to the existing_dataset_identifiers list.
    
        Example:
            self._get_existing_datasets(['dataset-identifier-1', 'dataset-identifier-2'])
    
        """
        for dataset in gathered_identifiers:
            exists = check_existing_package_by_identifier(dataset)
            if exists:
                log.warning('Dataset exists: %s', dataset)
                self.existing_dataset_identifiers.append(dataset)
            
    def _apply_default_values(self, package_dict):
        """
        Apply default values from OGC2CKAN_HARVESTER_MD_CONFIG to package_dict
        for required fields that are missing or None.
        """
        
        for field_group in self._schema_required_fields:
            for group_name, fields in field_group.items():
                if group_name == 'dataset_fields':
                    for field in fields:
                        if field not in package_dict or package_dict[field] is None:
                            default_value = OGC2CKAN_HARVESTER_MD_CONFIG.get(field)
                            package_dict[field] = self.substitute_ckan_site_url(default_value)
                elif group_name == 'resource_fields':
                    for resource in package_dict.get('resources', []):
                        for field in fields:
                            if field not in resource or resource[field] is None:
                                default_value = OGC2CKAN_HARVESTER_MD_CONFIG['resources'].get(field)
                                resource[field] = self.substitute_ckan_site_url(default_value)
   
    def substitute_ckan_site_url(self, value, ckan_site_url=None):
        if not ckan_site_url:
            ckan_site_url = schemingdcat_get_ckan_site_url()
        if isinstance(value, str) and '{ckan_site_url}' in value:
            return value.format(ckan_site_url=ckan_site_url)
        return value
    
    def normalize_inspire_hvd_category(self, package_dict):
        """Normalize the INSPIRE HVD category and applicable legislation in the package dictionary.
        
        Args:
            package_dict (dict): The package dictionary to normalize.
    
        Returns:
            dict: The normalized package dictionary.
    
        Raises:
            ValueError: If there is an error updating the package dictionary.
        """
        try:
            package_dict['hvd_category'] = [INSPIRE_HVD_CATEGORY]
            if 'applicable_legislation' not in package_dict:
                package_dict['applicable_legislation'] = [INSPIRE_HVD_APPLICABLE_LEGISLATION]
            elif INSPIRE_HVD_APPLICABLE_LEGISLATION not in package_dict['applicable_legislation']:
                package_dict['applicable_legislation'].append(INSPIRE_HVD_APPLICABLE_LEGISLATION)
            
            return package_dict
            
        except Exception as e:
            raise ValueError(f'Error updating the package dictionary: {e}') from e
        
    def _clean_identifier(self, identifier):
        """
        Cleans identifier by removing or replacing reserved characters.
        
        Args:
            identifier (str): The identifier to clean

        Returns:
            str: The cleaned identifier
        """
        if not identifier:
            return identifier
            
        # Define characters to replace with underscore
        chars_to_replace = ['/', ':', '\\', ' ', '?', '#', '[', ']', '@', '!', '$', '&', "'", 
                        '(', ')', '*', '+', ',', ';', '=']
        
        clean_id = identifier
        for char in chars_to_replace:
            clean_id = clean_id.replace(char, '_')
            
        # Remove multiple consecutive underscores
        while '__' in clean_id:
            clean_id = clean_id.replace('__', '_')
            
        # Remove leading/trailing underscores
        clean_id = clean_id.strip('_')
        
        return clean_id

    def _clean_format(self, format_value):
        """
        Clean and standardize format values.

        This method takes a format value, cleans it by converting it to lowercase,
        removing unnecessary description text, and then attempts to match it against
        known format patterns and protocol mappings to standardize it.

        Args:
            format_value (str): The format value to be cleaned and standardized.

        Returns:
            tuple: A tuple containing the standardized format and its corresponding
               MIME type. If no match is found, returns (None, None).
        """
        if not format_value:
            return None, None
    
        # Convert to lowercase and strip whitespace
        format_lower = format_value.lower().strip()
    
        # Remove IANA URL prefix if present
        if 'www.iana.org/assignments/media-types/' in format_lower:
            format_lower = format_lower.split('media-types/')[-1]
            if format_lower.startswith('application/'):
                format_lower = format_lower[12:]
    
        # Split by common separators
        parts = format_lower.replace('-', ' ').replace('/', ' ').replace('_', ' ').split()
        
        # Try to find a valid format in any of the parts
        for part in parts:
            # First try direct match in format_patterns
            if part in FORMAT_STANDARDIZATION['format_patterns']:
                std_format = FORMAT_STANDARDIZATION['format_patterns'][part]
                return std_format, FORMAT_STANDARDIZATION['mimetype_mapping'].get(std_format)
    
        # If no direct match found, try with the complete string
        for pattern, std_format in FORMAT_STANDARDIZATION['format_patterns'].items():
            if pattern in format_lower:
                return std_format, FORMAT_STANDARDIZATION['mimetype_mapping'].get(std_format)
    
        # Check in protocol mapping as last resort
        if format_lower in PROTOCOL_MAPPING:
            protocol = PROTOCOL_MAPPING[format_lower]
            if protocol in FORMAT_STANDARDIZATION['mimetype_mapping']:
                return protocol, FORMAT_STANDARDIZATION['mimetype_mapping'][protocol]
    
        # If still no match but contains service keywords
        for service_type in ['wms', 'wfs', 'wmts', 'wcs']:
            if service_type in format_lower:
                std_format = service_type.upper()
                return std_format, FORMAT_STANDARDIZATION['mimetype_mapping'].get(std_format)

        return None, None