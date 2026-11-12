from ckan.common import request
import json
import ckan.plugins as p

from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin
)

import ckanext.schemingdcat.helpers as sdct_helpers
from ckanext.schemingdcat.utils import remove_private_keys

import logging
import sys
import ast

FACET_OPERATOR_PARAM_NAME = '_facet_operator'
FACET_SORT_PARAM_NAME = '_%s_sort'

log = logging.getLogger(__name__)


class PackageController():

    p.implements(p.IPackageController, inherit=True)

    default_facet_operator = sdct_helpers.schemingdcat_default_facet_search_operator()

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass


    # CKAN < 2.10
    def before_search(self, search_params):
        return self.before_dataset_search(search_params)

    def before_dataset_search(self, search_params):
        """
        Modifies search parameters before executing a search.
    
        This method adjusts the 'fq' (filter query) parameter based on the 'facet.field' value in the search parameters.
        It also removes private fields from 'fl' parameters.
    
        Args:
            search_params (dict): The search parameters to be modified. Expected to contain 'facet.field' and 'fq'.
    
        Returns:
            dict: The modified search parameters.
    
        Raises:
            Exception: Captures and logs any exception that occurs during the modification of search parameters.
        """
        try:            
            private_fields = p.toolkit.config.get('ckanext.schemingdcat.api.private_fields', [])
            
            # Ensure private_fields is a list of strings
            if not isinstance(private_fields, list) or not all(isinstance(field, str) for field in private_fields):
                private_fields = []

            # Clean 'fl' parameter
            if 'fl' in search_params and search_params['fl'] is not None:
                fl_fields = search_params['fl']
                fl_fields = [field for field in fl_fields if field not in private_fields and not any(field.startswith(f'extras_{pf}') for pf in private_fields)]
                search_params.update({'fl': fl_fields})
        
            facet_field = search_params.get('facet.field', '')
            #log.debug("facet.field: %s", facet_field)
            
            if not facet_field:
                return search_params
            elif isinstance(facet_field, list):
                for field in facet_field:
                    new_fq = self._facet_search_operator(search_params.get('fq', ''), field)
                    if new_fq and isinstance(new_fq, str):
                        search_params.update({'fq': new_fq})
            elif isinstance(facet_field, str):
                new_fq = self._facet_search_operator(search_params.get('fq', ''), facet_field)
                if new_fq and isinstance(new_fq, str):
                    search_params.update({'fq': new_fq})
        except Exception as e:
            log.error("[before_dataset_search] Error: %s", e)
        return search_params

    # CKAN < 2.10
    def after_search(self, search_results, search_params):
        return self.after_dataset_search(search_results, search_params)

    def after_dataset_search(self, search_results, search_params):
        """
        Process the search results after a search, efficiently removing private keys.
    
        Args:
            search_results (dict): The search results dictionary to be processed.
            search_params (dict): The search parameters used for the search.
    
        Returns:
            dict: The processed search results dictionary with private keys removed from each result.
        """
        try:
            private_fields = p.toolkit.config.get('ckanext.schemingdcat.api.private_fields', [])
            
            # Ensure private_fields is a list of strings
            if not isinstance(private_fields, list) or not all(isinstance(field, str) for field in private_fields):
                private_fields = []
    
            # Precompute the set of fields to remove, including 'extras_' prefixed fields
            fields_to_remove = set(private_fields + [f"extras_{field}" for field in private_fields])
    
            # Process each result in the search results
            for result in search_results.get('results', []):
                for field in fields_to_remove:
                    result.pop(field, None)  # Removes the field if it exists
    
        except Exception as e:
            log.error("[after_dataset_search] Error: %s", e)
    
        return search_results

    # CKAN < 2.10
    def before_index(self, data_dict):
        return self.before_dataset_index(data_dict)
    
    def before_dataset_index(self, data_dict):
        """
        Processes the data dictionary before dataset indexing.
    
        Args:
            data_dict (dict): The data dictionary to be processed.
    
        Returns:
            dict: The processed data dictionary.
        """
        # Remove empty extras keys
        data_dict = self.remove_empty_extras_keys(data_dict)

        # Convert stringified lists to actual lists
        data_dict = self.convert_stringified_lists(data_dict)

        # Flatten repeating subfields
        data_dict = self.flatten_repeating_subfields(data_dict)

        # Convert dict fields to JSON strings to avoid errors in Solr 9
        data_dict = self._before_index_dump_dicts(data_dict)

        return data_dict

    # CKAN < 2.10
    def before_view(self, pkg_dict):
        return self.before_dataset_view(pkg_dict)

    def before_dataset_view(self, pkg_dict):
        return pkg_dict

    # CKAN < 2.10
    def after_create(self, context, data_dict):
        return self.after_dataset_create(context, data_dict)

    def after_dataset_create(self, context, data_dict):
        return data_dict

    # CKAN < 2.10
    def after_update(self, context, data_dict):
        return self.after_dataset_update(context, data_dict)

    def after_dataset_update(self, context, data_dict):
        return data_dict

    # CKAN < 2.10
    def after_delete(self, context, data_dict):
        return self.after_dataset_delete(context, data_dict)

    def after_dataset_delete(self, context, data_dict):
        return data_dict

    # CKAN < 2.10 hooks
    def after_show(self, context, data_dict):
        return self.after_dataset_show(context, data_dict)
    
    def after_dataset_show(self, context, data_dict):
        """
        Process the dataset after it is shown, removing private keys if necessary.
    
        Args:
            context (dict): The context dictionary containing user and other information.
            data_dict (dict): The dataset dictionary to be processed.
    
        Returns:
            dict: The processed dataset dictionary with private keys removed if necessary.
        """
        data_dict = self._clean_private_fields(context, data_dict)

        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles

    # Additional methods
    def convert_stringified_lists(self, data_dict):
        """
        Converts stringified lists in the data dictionary to actual lists.
    
        Args:
            data_dict (dict): The data dictionary to be processed.
    
        Returns:
            dict: The processed data dictionary with actual lists.
    
        This function iterates over the items in the data dictionary and converts
        any stringified lists (strings that start with '[' and end with ']') into
        actual lists. Keys that start with 'extras_', 'res_', or are 'validated_data_dict'
        are excluded from this conversion.
        """
        # Excluded items
        excluded_keys = [
            key for key in data_dict 
            if key.startswith('extras_') or key.startswith('res_') or key == 'validated_data_dict'
        ]
    
        # Filter data dictionary
        filter_data_dict = {
            key: value for key, value in data_dict.items()
            if key not in excluded_keys
        }
    
        for key, value in filter_data_dict.items():
            if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                try:
                    data_dict[key] = ast.literal_eval(value)
                except (ValueError, SyntaxError) as e:
                    log.error("Error converting stringified list for key '%s': %s", key, e)
    
        return data_dict
    
    def remove_empty_extras_keys(self, data_dict):
        """
        Remove extra_* and res_extras_* keys that contain empty lists or lists of empty strings.

        Args:
            data_dict (dict): The data dictionary to be processed.

        Returns:
            dict: The processed data dictionary with empty extras keys removed.
        """
        keys_to_remove = []
        for key, value in data_dict.items():
            if (key.startswith('extras_') or key.startswith('res_extras_')) and isinstance(value, list):
                if all(not item.strip() for item in value if isinstance(item, str)):
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            data_dict.pop(key, None)

        return data_dict
    
    def flatten_repeating_subfields(self, data_dict):
        """
        Based on https://github.com/ckan/ckanext-scheming/pull/414
        
        Notes:
            Index suitable repeating dataset fields in before_dataset_index to prevent failures
            on unmodified solr schema. This will allow hitting results in most text and list
            subfields. Ideally you probably want to select the relevant subfields that will get
            indexed and modify the Solr schema if necessary.
            This implementation will group the values of the same subfields into an
            `extras_{field_name}__{key}`,a text Solr field that will allow free-text search on
            its value. Again, if you require more precise handling of a particular subfield,
            you will need to customize the Solr schema to add particular fields needed.
    
        Args:
            data_dict (dict): The data dictionary to be processed.
    
        Returns:
            dict: The processed data dictionary with flattened repeating subfields.
        """
        schemas = SchemingDatasetsPlugin.instance._expanded_schemas
        if data_dict['type'] not in schemas:
            return data_dict
    
        schema = schemas[data_dict['type']]
    
        for field in schema['dataset_fields']:
            if field['field_name'] in data_dict and 'repeating_subfields' in field:
                flattened_values = {}
                for item in data_dict[field['field_name']]:
                    for key, value in item.items():
                        if isinstance(value, dict):
                            continue
                        if isinstance(value, list):
                            value = ' '.join(value)
                        new_key = 'extras_{field_name}__{key}'.format(
                            field_name=field["field_name"], key=key
                        )
                        if new_key not in flattened_values:
                            flattened_values[new_key] =  str(value)
                        else:
                            flattened_values[new_key] += ' ' + str(value)
    
                data_dict.update(flattened_values)
                data_dict.pop(field['field_name'], None)
    
        return data_dict

    def _before_index_dump_dicts(self, data_dict):
        """
        Converts dict fields in the data dictionary to JSON strings.
    
        This function is necessary to ensure that all fields in the data dictionary
        can be indexed by Solr. Solr cannot directly index fields of type dict, 
        which can lead to errors such as "missing required field" even when the 
        field is present in the data dictionary. By converting dict fields to JSON 
        strings, we ensure that the data is in a format that Solr can handle.
    
        This issue (https://github.com/ckan/ckan/issues/8423) has been observed in CKAN versions 2.10.4 and Solr 9, where 
        attempts to upload resources to the Datastore resulted in errors due to 
        the presence of dict fields in the data dictionary. The solution involves 
        transforming these fields into strings before indexing, as discussed in 
        the following issues:
        - CKAN - Custom plugin/theme error datastore using fluent presets https://github.com/ckan/ckan/issues/7750
        - Solr error: missing required field https://github.com/ckan/ckan/issues/7730
    
        Args:
            data_dict (dict): The data dictionary to be processed.
    
        Returns:
            dict: The processed data dictionary with dict fields as JSON strings.
        """
        for key, value in data_dict.items():
            if isinstance(value, dict):
                data_dict[key] = json.dumps(value)
        return data_dict

    def package_controller_config(self, default_facet_operator):
        self.default_facet_operator = default_facet_operator

    def _facet_search_operator(self, fq, facet_field):
        """Modifies the query filter (fq) to use the OR operator among the specified facet filters.

        Args:
            fq (str): The current query filter.
            facet_field (list): List of facet fields to consider for the OR operation.

        Returns:
            str: The modified query filter.
        """
        new_fq = fq
        try:
            facet_operator = self.default_facet_operator
            # Determine the facet operator based on request parameters
            if request.args.get(FACET_OPERATOR_PARAM_NAME) == 'OR':
                facet_operator = 'OR'
            elif request.args.get(FACET_OPERATOR_PARAM_NAME) == 'AND':
                facet_operator = 'AND'

            if facet_operator == 'OR' and facet_field:
                # Split the original fq into conditions, assuming they are separated by " AND "
                conditions = fq.split(' AND ')
                # Filter and group conditions that correspond to facet fields
                facet_conditions = [cond for cond in conditions if any(fld in cond for fld in facet_field)]
                non_facet_conditions = [cond for cond in conditions if not any(fld in cond for fld in facet_field)]
                # Reconstruct fq using " OR " to join facet conditions and " AND " for the rest
                if facet_conditions:
                    new_fq = ' OR '.join(facet_conditions)
                    if non_facet_conditions:
                        new_fq = f"({new_fq}) AND {' AND '.join(non_facet_conditions)}"
                else:
                    new_fq = ' AND '.join(non_facet_conditions)

        except Exception as e:
            log.error("[_facet_search_operator] Error modifying the query filter: %s", e)
            # In case of error, return the original fq
            new_fq = fq

        return new_fq
    
    def _clean_private_fields(self, context, data_dict):
        """
        Process the dataset after it is shown, removing private keys if necessary.
    
        Args:
            context (dict): The context dictionary containing user and other information.
            data_dict (dict): The dataset dictionary to be processed.
    
        Returns:
            dict: The processed dataset dictionary with private keys removed if necessary.
        """
        private_fields_roles = p.toolkit.config.get('ckanext.schemingdcat.api.private_fields_roles') 

        # Ensure private_fields_roles is a list of strings
        if not isinstance(private_fields_roles, list) or not all(isinstance(role, str) for role in private_fields_roles):
            private_fields_roles = ['admin']

        try:
            user = context.get("auth_user_obj")
            if user is None or user.is_anonymous:
                data_dict = remove_private_keys(data_dict)
                return data_dict
    
            if hasattr(user, 'sysadmin') and user.sysadmin:
                return data_dict
    
            if data_dict is not None:
                org_id = data_dict.get("owner_org")
                if org_id is not None:
                    members = p.toolkit.get_action("schemingdcat_member_list")(
                        data_dict={"id": org_id, "object_type": "user"}
                    )
                    for member_id, _, role in members:
                        if member_id == user.id and role.lower() in private_fields_roles:
                            return data_dict
                    data_dict = remove_private_keys(data_dict)
                else:
                    data_dict = remove_private_keys(data_dict)
        except Exception as e:
            log.error('Error in after_dataset_show: %s', e)
            data_dict = remove_private_keys(data_dict)
        
        return data_dict