import sys
import logging
import typing
import importlib
import inspect

from ckan.common import json
from ckan.lib.plugins import DefaultTranslation
import ckan.plugins as p
from ckan.lib.navl.dictization_functions import unflatten

from ckanext.dcat import processors

from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin,
    SchemingGroupsPlugin,
    SchemingOrganizationsPlugin,
    _field_validators,
    _field_output_validators,
    _field_create_validators,
    expand_form_composite,
)
from ckanext.scheming import logic as scheming_logic
from ckanext.scheming import validation as scheming_validation

import ckanext.schemingdcat.cli as sdct_cli
import ckanext.schemingdcat.config as sdct_config
import ckanext.schemingdcat.statistics.model as sdct_model
from ckanext.schemingdcat.faceted import Faceted
from ckanext.schemingdcat.utils import init_config
from ckanext.schemingdcat.package_controller import PackageController
from ckanext.schemingdcat import helpers, validators, blueprint, subscriptions
import ckanext.schemingdcat.logic.auth.ckan as ckan_auth
import ckanext.schemingdcat.logic.dcat.schemingdcat as schemingdcat_dcat
from ckanext.schemingdcat.processors import SchemingDCATRDFSerializer

try:
    config_declarations = p.toolkit.blanket.config_declarations
except AttributeError:
    # CKAN 2.9 does not have config_declarations.
    # Remove when dropping support.
    def config_declarations(cls):
        return cls

log = logging.getLogger(__name__)


convert_to_extras = p.toolkit.get_converter('convert_to_extras')

@config_declarations
class SchemingDCATPlugin(
    p.SingletonPlugin, Faceted, PackageController, DefaultTranslation
):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IFacets)
    # Custom PackageController, also remove private keys from the package dict
    p.implements(p.IPackageController)
    p.implements(p.ITranslation)
    p.implements(p.IValidators)
    p.implements(p.IBlueprint)
    p.implements(p.IClick)
    p.implements(p.ISignal)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions, inherit=True)
    p.implements(p.IAuthFunctions)

    # IConfigurer
    def update_config(self, config_):
        p.toolkit.add_template_directory(config_, "templates")
        p.toolkit.add_public_directory(config_, "public")

        p.toolkit.add_resource('fanstatic',
                            'schemingdcat')

        p.toolkit.add_resource("assets", "ckanext-schemingdcat")

        # Load yamls config files
        init_config()

        # configure Faceted class (parent of this)
        self.facet_load_config(config_.get("ckanext.schemingdcat.facet_list", "").split())

    def get_helpers(self):
        return dict(helpers.all_helpers)

    def get_validators(self):
        return dict(validators.all_validators)

    # IBlueprint
    def get_blueprint(self):
        return [blueprint.schemingdcat]

    # IClick
    def get_commands(self):
        return sdct_cli.get_commands()

    # ISignal
    def get_signal_subscriptions(self):
        return subscriptions.get_subscriptions()
    
    #IActions
    def get_actions(self):
        # Obtain standard actions
        actions = _get_logic_functions('ckanext.schemingdcat.logic.action')
        
        # Overwrite ckanext-dcat actions
        log.info('Add chained_actions for: dcat_dataset_show and dcat_catalog_show')
        actions.update({
            'dcat_dataset_show': schemingdcat_dcat.dcat_dataset_show,
            'dcat_catalog_show': schemingdcat_dcat.dcat_catalog_show
        })
        
        return actions

    # Auth functions
    def get_auth_functions(self) -> typing.Dict[str, typing.Callable]:
        return {
            #TODO: Implement package_publish
            "package_publish": ckan_auth.authorize_package_publish,
            "package_update": ckan_auth.package_update,
            "package_patch": ckan_auth.package_patch
        }

class SchemingDCATDatasetsPlugin(SchemingDatasetsPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IConfigurable)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)

    def read_template(self):
        return "package/read.html"

    def resource_template(self):
        return "package/resource_read.html"

    def package_form(self):
        return "schemingdcat/package/snippets/package_form.html"

    def resource_form(self):
        return "schemingdcat/package/snippets/resource_form.html"

    def get_actions(self):
        return {
            "scheming_dataset_schema_list": scheming_logic.scheming_dataset_schema_list,
            "scheming_dataset_schema_show": scheming_logic.scheming_dataset_schema_show,
        }

    # Override Scheming plugin to avoid errors when not extras are present in datastore resource (for ex in data_dict['extras'] KeyError: 'extras')
    def validate(self, context, data_dict, schema, action):
        """
        Validate and convert for package_create, package_update and
        package_show actions.
        """
        thing, action_type = action.split('_')
        t = data_dict.get('type')
        if not t or t not in self._schemas:
            return data_dict, {'type': [
                "Unsupported dataset type: {t}".format(t=t)]}

        scheming_schema = self._expanded_schemas[t]

        before = scheming_schema.get('before_validators')
        after = scheming_schema.get('after_validators')
        if action_type == 'show':
            get_validators = _field_output_validators
            before = after = None
        elif action_type == 'create':
            get_validators = _field_create_validators
        else:
            get_validators = _field_validators

        if before:
            schema['__before'] = scheming_validation.validators_from_string(
                before, None, scheming_schema)
        if after:
            schema['__after'] = scheming_validation.validators_from_string(
                after, None, scheming_schema)
        fg = (
            (scheming_schema['dataset_fields'], schema, True),
            (scheming_schema['resource_fields'], schema['resources'], False)
        )

        composite_convert_fields = []
        for field_list, destination, is_dataset in fg:
            for f in field_list:
                convert_this = is_dataset and f['field_name'] not in schema
                destination[f['field_name']] = get_validators(
                    f,
                    scheming_schema,
                    convert_this
                )
                if convert_this and 'repeating_subfields' in f:
                    composite_convert_fields.append(f['field_name'])

        def composite_convert_to(key, data, errors, context):
            unflat = unflatten(data)
            for f in composite_convert_fields:
                if f not in unflat:
                    continue
                data[(f,)] = json.dumps(unflat[f], default=lambda x:None if x == p.toolkit.missing else x)
                convert_to_extras((f,), data, errors, context)
                del data[(f,)]

        if action_type == 'show':
            if composite_convert_fields and 'extras' in data_dict:
                for ex in data_dict['extras']:
                    if ex['key'] in composite_convert_fields:
                        data_dict[ex['key']] = json.loads(ex['value'])
                data_dict['extras'] = [
                    ex for ex in data_dict['extras']
                    if ex['key'] not in composite_convert_fields
                ]
        else:
            dataset_composite = {
                f['field_name']
                for f in scheming_schema['dataset_fields']
                if 'repeating_subfields' in f
            }
            if dataset_composite:
                expand_form_composite(data_dict, dataset_composite)
            resource_composite = {
                f['field_name']
                for f in scheming_schema['resource_fields']
                if 'repeating_subfields' in f
            }
            if resource_composite and 'resources' in data_dict:
                for res in data_dict['resources']:
                    expand_form_composite(res, resource_composite.copy())
            # convert composite package fields to extras so they are stored
            if composite_convert_fields:
                schema = dict(
                    schema,
                    __after=schema.get('__after', []) + [composite_convert_to])

        return p.toolkit.navl_validate(data_dict, schema, context)


class SchemingDCATGroupsPlugin(SchemingGroupsPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)

    def about_template(self):
        return "schemingdcat/group/about.html"


class SchemingDCATOrganizationsPlugin(SchemingOrganizationsPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)

    def about_template(self):
        return "schemingdcat/organization/about.html"


class SchemingDCATOpenDataStatisticsPlugin(p.SingletonPlugin):
    p.implements(p.IActions)
    p.implements(p.IConfigurable)

    #IConfigurable
    def configure(self, config):
        args = sys.argv
        if 'db' in args and ('init' in args or 'upgrade' in args):
            log.warning('Skipping Open Data site stats update due to db init or upgrade.')
        else:
            sdct_model.clean()
            sdct_model.update_table()
            log.info('Initialized Open Data site statistics')

    #IActions
    def get_actions(self):
        return _get_logic_functions('ckanext.schemingdcat.statistics.logic.action')

def _get_logic_functions(module_root, logic_functions=None, decorator=None):
    """
    Retrieves and aggregates logic functions from specified submodules, filtering by decorator.

    This function dynamically imports submodules ('get', 'create', 'update', 'patch', 'delete')
    from the given `module_root`. It then extracts callable functions from these submodules
    that do not start with an underscore, belong to the submodule's namespace, and are decorated
    with the specified decorator. These functions are added to the `logic_functions` dictionary.

    Args:
        module_root (str): The root module path from which to import submodules.
        logic_functions (dict, optional): A dictionary to store the aggregated logic functions.
            Defaults to None, which initializes an empty dictionary.
        decorator (callable, optional): A decorator function to filter the logic functions.
            Only functions decorated with this decorator will be imported. Defaults to None.

    Returns:
        dict: A dictionary containing the aggregated and filtered logic functions.
    """
    if logic_functions is None:
        logic_functions = {}

    for module_name in ['get', 'create', 'update', 'patch', 'delete']:
        module_path = f"{module_root}.{module_name}"

        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            log.error(f"Error importing module {module_path}: {e}")
            continue

        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith('_'):
                if decorator is None or getattr(obj, 'is_decorated_with_action', False):
                    logic_functions[name] = obj

    return logic_functions