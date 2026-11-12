from builtins import str
import json
import logging
from functools import lru_cache
import re
from urllib.parse import urlencode
from ckanext.harvest.model import HarvestObject
import datetime
import ckan.plugins as p
import requests
from requests.exceptions import HTTPError, RequestException

import ckan.model as model
import ckan.logic as logic
import uuid

from ckanext.schemingdcat.harvesters.base import (
    SchemingDCATHarvester,
    RemoteSchemaError,
    ReadError,
    ContentFetchError,
    SearchError,
    RemoteResourceError
)
from ckanext.schemingdcat.lib.field_mapping import FieldMappingValidator
from ckanext.schemingdcat.interfaces import ISchemingDCATHarvester
from ckanext.schemingdcat.helpers import schemingdcat_get_dataset_schema_field_names

log = logging.getLogger(__name__)


class SchemingDCATCKANHarvester(SchemingDCATHarvester):
    """
    A custom CKAN harvester for Scheming DCAT datasets.
    """

    def info(self):
        return {
            "name": "schemingdcat_ckan",
            "title": "Scheming DCAT CKAN endpoint",
            "description": "Harvester for dataset with custom schema defined in ckanext-schemingdcat extension.",
            "about_url": "https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#schemingdcat-ckan-harvester",
        }

    _names_taken = []

    def _get_action_api_offset(self):
        return "/api/%d/action" % self.action_api_version

    def _get_search_api_offset(self):
        return "%s/package_search" % self._get_action_api_offset()

    def _get_schema_api_offset(self, schema_type="dataset"):
        return f"{self._get_action_api_offset()}/scheming_dataset_schema_show?type={schema_type}"

    def _get_content(self, url):
        headers = {}
        api_key = self.config.get("api_key")
        if api_key:
            headers["Authorization"] = api_key

        try:
            http_request = requests.get(url, headers=headers)
        except HTTPError as e:
            raise ContentFetchError(
                "HTTP error: %s %s" % (e.response.status_code, e.request.url)
            )
        except RequestException as e:
            raise ContentFetchError("Request error: %s" % e)
        except Exception as e:
            raise ContentFetchError("HTTP general exception: %s" % e)
        return http_request.text

    def validate_config(self, config):
        """
        Validates the configuration for the SchemingDCATCKANHarvester.

        Args:
            config (str): The configuration JSON string.

        Returns:
            str: The validated configuration JSON string.

        Raises:
            ValueError: If the schema is not specified or is not supported.
            ValueError: If 'allow_harvest_datasets' is not a boolean.
        """
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

        # Check if the schema is specified
        if "schema" in config_obj:
            schema = config_obj["schema"]
            if not isinstance(schema, str):
                raise ValueError("schema must be a string")

            # Check if the specified schema is supported
            if schema.lower().strip() not in self._supported_schemas:
                if len(self._supported_schemas) > 1:
                    raise ValueError(
                        f'schema should be one of: {", ".join(self._supported_schemas)}. Current dataset schema: {self._local_schema_name}'
                    )
                else:
                    if self._local_schema_name.lower().strip() != schema.lower().strip():
                        raise ValueError(
                            f"Config 'schema': {schema} should match the local schema: '{self._local_schema_name}'. "
                            f"Check the remote schema with CKAN API: {{ckan_site_url}}/api/3/action/scheming_dataset_schema_show?type=dataset, "
                            f"or specify the local schema '{self._local_schema_name}', and the harvester will try to map the fields."
                        )

            config = json.dumps({**config_obj, "schema": schema.lower().strip()})

        # If no schema is specified, use the local schema
        else:
            config = json.dumps({**config_obj, "schema": self._local_schema_name})

        # Check if 'allow_harvest_datasets' is not in the config_obj or is not a boolean
        if "allow_harvest_datasets" not in config_obj or not isinstance(
            config_obj["allow_harvest_datasets"], bool
        ):
            config = json.dumps({**config_obj, "allow_harvest_datasets": False})

        # Check if 'allow_private_datasets' is not in the config_obj or is not a boolean
        if "allow_private_datasets" in config_obj:
            if "api_key" in config_obj:
                if not isinstance(config_obj["allow_private_datasets"], bool):
                    config = json.dumps({**config_obj, "allow_private_datasets": False})
            else:
                raise ValueError(
                    "'api_key' is needed to using 'allow_private_datasets'"
                )
        else:
            config = json.dumps({**config_obj, "allow_private_datasets": False})

        # Check remote_orgs and remote_groups == only_local, if not, put
        # remote_orgs and remote_groups to only_local
        if (
            "remote_groups" not in config_obj
            or config_obj.get("remote_groups") != "only_local"
        ):
            config = json.dumps({**config_obj, "remote_groups": "only_local"})

        if (
            "remote_orgs" not in config_obj
            or config_obj.get("remote_orgs") != "only_local"
        ):
            config = json.dumps({**config_obj, "remote_orgs": "only_local"})

        # Check if 'field_mapping_schema_version' exists in the config
        field_mapping_schema_version_error_message = f'Insert the schema version: "field_mapping_schema_version: <version>", one of: {", ".join(map(str, self._field_mapping_validator_versions))} . More info: https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#remote-google-sheetonedrive-excel-metadata-upload-harvester'
        if 'field_mapping_schema_version' not in config_obj and 'dataset_field_mapping' in config_obj:
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

        return config

    def gather_stage(self, harvest_job):
        """
        Performs the gather stage of the SchemingDCATCKANHarvester. This method is responsible for accesing the CKAN API and reading its contents. The contents are then processed, cleaned, and added to the database.

        Args:
            harvest_job (HarvestJob): The harvest job object.

        Returns:
            list: A list of object IDs for the harvested datasets.
        """
        # Get file contents of source url
        harvest_source_title = harvest_job.source.title
        remote_ckan_base_url = harvest_job.source.url.rstrip("/")

        log.debug('In SchemingDCATCKANHarvester gather_stage with harvest source: %s and URL: %s', harvest_source_title, remote_ckan_base_url)

        # Get config options
        p.toolkit.requires_ckan_version(min_version="2.0")
        get_all_packages = True
        self._set_config(harvest_job.source.config)

        # Filter in/out datasets from particular organizations
        fq_terms = []
        org_filter_include = self.config.get("organizations_filter_include", [])
        org_filter_exclude = self.config.get("organizations_filter_exclude", [])
        if org_filter_include:
            fq_terms.append(
                " OR ".join(
                    "organization:%s" % org_name for org_name in org_filter_include
                )
            )
        elif org_filter_exclude:
            fq_terms.extend(
                "-organization:%s" % org_name for org_name in org_filter_exclude
            )

        groups_filter_include = self.config.get("groups_filter_include", [])
        groups_filter_exclude = self.config.get("groups_filter_exclude", [])
        if groups_filter_include:
            fq_terms.append(
                " OR ".join(
                    "groups:%s" % group_name for group_name in groups_filter_include
                )
            )
        elif groups_filter_exclude:
            fq_terms.extend(
                "-groups:%s" % group_name for group_name in groups_filter_exclude
            )

        # Ideally we can request from the remote CKAN only those datasets
        # modified since the last completely successful harvest.
        last_error_free_job = self.last_error_free_job(harvest_job)
        log.debug("Last error-free job: %r", last_error_free_job)
        if last_error_free_job and not self.config.get("force_all", False):
            get_all_packages = False

            # Request only the datasets modified since
            last_time = last_error_free_job.gather_started
            # Note: SOLR works in UTC, and gather_started is also UTC, so
            # this should work as long as local and remote clocks are
            # relatively accurate. Going back a little earlier, just in case.
            get_changes_since = (last_time - datetime.timedelta(hours=1)).isoformat()
            log.info("Searching for datasets modified since: %s UTC", get_changes_since)

            fq_since_last_time = "metadata_modified:[{since}Z TO *]".format(
                since=get_changes_since
            )

            try:
                pkg_dicts = self._search_for_datasets(
                    remote_ckan_base_url, fq_terms + [fq_since_last_time]
                )
            except SearchError as e:
                log.info(
                    "Searching for datasets changed since last time "
                    "gave an error: %s",
                    e,
                )
                get_all_packages = True

            if not get_all_packages and not pkg_dicts:
                log.info(
                    "No datasets have been updated on the remote "
                    "CKAN instance since the last harvest job %s",
                    last_time,
                )
                return []

        # Fall-back option - request all the datasets from the remote CKAN
        if get_all_packages:
            # Request all remote packages
            try:
                pkg_dicts = self._search_for_datasets(remote_ckan_base_url, fq_terms)
            except SearchError as e:
                log.info("Searching for all datasets gave an error: %s", e)
                self._save_gather_error(
                    "Unable to search remote CKAN for datasets:%s url:%s"
                    "terms:%s" % (e, remote_ckan_base_url, fq_terms),
                    harvest_job,
                )
                return None
        if not pkg_dicts:
            self._save_gather_error(
                "No datasets found at CKAN: %s" % remote_ckan_base_url, harvest_job
            )
            return []


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
    
        except ReadError as e:
            self._save_gather_error('Error generating default values for dataset/distribution config field mappings: {0}'.format(e), harvest_job)

        # Create harvest objects for each dataset
        try:
            package_ids = set()
            object_ids = []

            # Check if the content_dict colnames correspond to the local schema
            try:
                if self.config.get("dataset_field_mapping") is None and self.config.get("distribution_field_mapping") is None:
                    log.warning('If no *_field_mapping is provided in the configuration for validation, fields are automatically mapped to the local schema.')
                else:
                    # Standardizes the field_mapping                    
                    log.debug('remote_dataset_field_mapping: %s', field_mappings.get('dataset_field_mapping'))
                    log.debug('remote_distribution_field_mapping: %s', field_mappings.get('distribution_field_mapping'))
                    self._validate_remote_schema(
                        remote_dataset_field_names=None,
                        remote_ckan_base_url=remote_ckan_base_url,
                        remote_resource_field_names=None,
                        remote_dataset_field_mapping=field_mappings.get('dataset_field_mapping'),
                        remote_distribution_field_mapping=field_mappings.get('distribution_field_mapping'),
                    )
            except RemoteSchemaError as e:
                self._save_gather_error(
                    "Error validating remote schema: {0}".format(e), harvest_job
                )
                return []

            for pkg_dict in pkg_dicts:
                if pkg_dict["id"] in package_ids:
                    log.info(
                        "Discarding duplicate dataset %s - probably due "
                        "to datasets being changed at the same time as "
                        "when the harvester was paging through",
                        pkg_dict["id"],
                    )
                    continue
                
                # Check if the content_dicts colnames correspond to the local schema
                try:
                    
                    #log.debug('RAW package_dict: %s', pkg_dict)
                    
                    #log.debug('content_dicts: %s', content_dicts)
                    # Standardizes the field names
                    pkg_dict = self._standardize_ckan_dict_from_field_mapping(pkg_dict, field_mappings)
                    
                    #log.debug('Standardized package dict: %s', pkg_dict)
                except RemoteSchemaError as e:
                    self._save_gather_error('Error standarize remote dataset: {0}'.format(e), harvest_job)
                    return []
                                        
                package_ids.add(pkg_dict["id"])

                obj = HarvestObject(
                    guid=pkg_dict["id"], job=harvest_job, content=json.dumps(pkg_dict)
                )
                obj.save()
                object_ids.append(obj.id)

            return object_ids
        except Exception as e:
            self._save_gather_error("%r" % e, harvest_job)

    def _get_content(self, url):
            headers = {}
            api_key = self.config.get("api_key")
            if api_key:
                headers["Authorization"] = api_key

            # Get SSL verification setting from config (default to True)
            ssl_verify = self.config.get("ssl_verify", True)
            if not ssl_verify:
                log.warning('SSL Verify is set to False. SSL certificate verification is disabled.')

            try:
                http_request = requests.get(url, headers=headers, verify=ssl_verify)
            except HTTPError as e:
                raise ContentFetchError(
                    "HTTP error: %s %s" % (e.response.status_code, e.request.url)
                )
            except RequestException as e:
                raise ContentFetchError("Request error: %s" % e)
            except Exception as e:
                raise ContentFetchError("HTTP general exception: %s" % e)
            return http_request.text

    def _search_for_datasets(self, remote_ckan_base_url, fq_terms=None):
        """Does a dataset search on a remote CKAN and returns the results.

        Deals with paging to return all the results, not just the first page.
        """
        base_search_url = remote_ckan_base_url + self._get_search_api_offset()
        params = {"rows": "100", "start": "0"}
        # There is the worry that datasets will be changed whilst we are paging
        # through them.
        # * In SOLR 4.7 there is a cursor, but not using that yet
        #   because few CKANs are running that version yet.
        # * However we sort, then new names added or removed before the current
        #   page would cause existing names on the next page to be missed or
        #   double counted.
        # * Another approach might be to sort by metadata_modified and always
        #   ask for changes since (and including) the date of the last item of
        #   the day before. However if the entire page is of the exact same
        #   time, then you end up in an infinite loop asking for the same page.
        # * We choose a balanced approach of sorting by ID, which means
        #   datasets are only missed if some are removed, which is far less
        #   likely than any being added. If some are missed then it is assumed
        #   they will harvested the next time anyway. When datasets are added,
        #   we are at risk of seeing datasets twice in the paging, so we detect
        #   and remove any duplicates.
        params["include_private"] = False
        params["sort"] = "id asc"
        
        if self.config.get("allow_private_datasets", False):
            params["include_private"] = True   
        
        if fq_terms:
            params["fq"] = " ".join(fq_terms)

        pkg_dicts = []
        pkg_ids = set()
        previous_content = None

        while True:
            url = base_search_url + "?" + urlencode(params)
            log.debug("Searching for CKAN datasets: %s", url)

            try:
                content = self._get_content(url)
            except ContentFetchError as e:
                raise SearchError(
                    "Error sending request to search remote "
                    "CKAN instance %s using URL %r. Error: %s"
                    % (remote_ckan_base_url, url, e)
                )

            if previous_content and content == previous_content:
                raise SearchError("The paging doesn't seem to work. URL: %s" % url)
            try:
                response_dict = json.loads(content)
            except ValueError:
                raise SearchError(
                    "Response from remote CKAN was not JSON: %r" % content
                )
            try:
                pkg_dicts_page = response_dict.get("result", {}).get("results", [])
            except ValueError:
                raise SearchError(
                    "Response JSON did not contain "
                    "result/results: %r" % response_dict
                )

            # Weed out any datasets found on previous pages (should datasets be
            # changing while we page)
            ids_in_page = set(p["id"] for p in pkg_dicts_page)
            duplicate_ids = ids_in_page & pkg_ids
            if duplicate_ids:
                pkg_dicts_page = [
                    p for p in pkg_dicts_page if p["id"] not in duplicate_ids
                ]
            pkg_ids |= ids_in_page

            pkg_dicts.extend(pkg_dicts_page)

            if len(pkg_dicts_page) == 0:
                break

            params["start"] = str(int(params["start"]) + int(params["rows"]))

        log.debug('Number of elements in remote CKAN: %s', len(pkg_dicts))

        return pkg_dicts

    def fetch_stage(self, harvest_object):
        # Nothing to do here - we got the package dict in the search in the
        # gather stage
        return True

    def modify_package_dict(self, package_dict, harvest_object):
        """
        Allows custom harvesters to modify the package dict before
        creating or updating the actual package.

        Args:
            package_dict (dict): The package dictionary to be modified.
            harvest_object (HarvestObject): The harvest object associated with the package.

        Returns:
            dict: The modified package dictionary.
        """
        # Clean up any existing extras already in package_dict
        package_dict = self._remove_duplicate_keys_in_extras(package_dict)

        # Set translated fields
        package_dict = self._set_translated_fields(package_dict)

        # Check basic fields without translations
        package_dict = self._fill_translated_properties(package_dict)

        # Using self._dataset_default_values and self._distribution_default_values based on config mappings
        package_dict = self._update_package_dict_with_config_mapping_default_values(package_dict)

        return package_dict

    def import_stage(self, harvest_object):
        """
        Imports the harvested data into CKAN.

        Args:
            harvest_object (HarvestObject): The harvested object to import.

        Returns:
            bool: True if the import is successful, False otherwise.
        """
        log.debug("In SchemingDCATCKANHarvester import_stage")

        base_context = {
            "model": model,
            "session": model.Session,
            "user": self._get_user_name(),
        }
        if not harvest_object:
            log.error("No harvest object received")
            return False

        if harvest_object.content is None:
            self._save_object_error(
                "Empty content for object %s" % harvest_object.id,
                harvest_object,
                "Import",
            )
            return False

        self._set_config(harvest_object.job.source.config)

        try:
            package_dict = json.loads(harvest_object.content)
            
            # Add default values: tags, groups, etc.
            package_dict = self._set_package_dict_default_values(
                package_dict, harvest_object, base_context
            )

            log.debug("Go to source_dataset")

            # Local harvest source organization
            source_dataset = logic.get_action("package_show")(
                base_context.copy(), {"id": harvest_object.source.id}
            )
            local_org = source_dataset.get("owner_org")

            remote_orgs = self.config.get("remote_orgs", None)

            if remote_orgs not in ("only_local", "create"):
                # Assign dataset to the source organization
                package_dict["owner_org"] = local_org
            else:
                if "owner_org" not in package_dict:
                    package_dict["owner_org"] = None

                # check if remote org exist locally, otherwise remove
                validated_org = None
                remote_org = package_dict["owner_org"]

                if remote_org:
                    try:
                        data_dict = {"id": remote_org}
                        org = logic.get_action("organization_show")(
                            base_context.copy(), data_dict
                        )
                        validated_org = org["id"]
                    except logic.NotFound:
                        log.info("Organization %s is not available", remote_org)
                        if remote_orgs == "create":
                            try:
                                try:
                                    org = self._get_organization(
                                        harvest_object.source.url, remote_org
                                    )
                                except RemoteResourceError:
                                    # fallback if remote CKAN exposes organizations as groups
                                    # this especially targets older versions of CKAN
                                    org = self._get_group(
                                        harvest_object.source.url, remote_org
                                    )

                                for key in [
                                    "packages",
                                    "created",
                                    "users",
                                    "groups",
                                    "tags",
                                    "extras",
                                    "display_name",
                                    "type",
                                ]:
                                    org.pop(key, None)
                                logic.get_action("organization_create")(
                                    base_context.copy(), org
                                )
                                log.info(
                                    "Organization %s has been newly created", remote_org
                                )
                                validated_org = org["id"]
                            except (RemoteResourceError, logic.ValidationError):
                                log.error("Could not get remote org %s", remote_org)

                package_dict["owner_org"] = validated_org or local_org

            # log.debug('Package groups: %s', package_dict['groups'])

            for resource in package_dict.get("resources", []):
                # Clear remote url_type for resources (eg datastore, upload) as
                # we are only creating normal resources with links to the
                # remote ones
                resource.pop("url_type", None)

                # Clear revision_id as the revision won't exist on this CKAN
                # and saving it will cause an IntegrityError with the foreign
                # key.
                resource.pop("revision_id", None)

            # before_modify_package_dict interface
            for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                if hasattr(harvester, 'before_modify_package_dict'):
                    package_dict, before_modify_package_dict_errors = harvester.before_modify_package_dict(package_dict)

                    for err in before_modify_package_dict_errors:
                        self._save_object_error(f'before_modify_package_dict error: {err}', harvest_object, 'Import')
                        return False

            package_dict = self.modify_package_dict(package_dict, harvest_object)
            result = self._create_or_update_package(
                package_dict, harvest_object, package_dict_form="package_show"
            )

            # after_modify_package_dict interface
            for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                if hasattr(harvester, 'after_modify_package_dict'):
                    package_dict, after_modify_package_dict_errors = harvester.after_modify_package_dict(package_dict)

                    for err in after_modify_package_dict_errors:
                        self._save_object_error(f'after_modify_package_dict error: {err}', harvest_object, 'Import')
                        return False

            # Log package_dict, package dict is a dict
            log.debug("Package create or update: %s", result)

            return result

        except logic.ValidationError as e:
            self._save_object_error(
                "Invalid package with GUID: %s: %r"
                % (harvest_object.guid, e.error_dict),
                harvest_object,
                "Import",
            )
        except Exception as e:
            self._save_object_error("%s" % e, harvest_object, "Import")

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
        # Update unique ids
        for resource in package_dict['resources']:
            resource['alternate_identifier'] = resource['id']
            resource['id'] = str(uuid.uuid4())
            resource.pop('dataset_id', None)

        return package_dict
    
