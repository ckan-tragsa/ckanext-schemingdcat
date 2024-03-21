import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.schemingdcat.helpers as helpers
import ckanext.schemingdcat.validators as validators
import ckanext.schemingdcat.config as sd_config
from ckanext.scheming.plugins import SchemingDatasetsPlugin, SchemingGroupsPlugin, SchemingOrganizationsPlugin
from ckanext.schemingdcat.faceted import Faceted
from ckanext.schemingdcat.utils import init_config
from ckanext.schemingdcat import blueprint
from ckanext.schemingdcat.package_controller import PackageController
from ckan.lib.plugins import DefaultTranslation

import logging

log = logging.getLogger(__name__)


class FacetSchemingDcatPlugin(plugins.SingletonPlugin,
                           Faceted, 
                           PackageController, 
                           DefaultTranslation):

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IBlueprint)


    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')

        #toolkit.add_resource('fanstatic',
        #                     'schemingdcat')

        toolkit.add_resource('assets',
                             'ckanext-schemingdcat')

        sd_config.default_locale = config_.get('ckan.locale_default',
                                               sd_config.default_locale
                                               )

        sd_config.default_facet_operator = config_.get(
            'schemingdcat.default_facet_operator',
            sd_config.default_facet_operator
            )

        sd_config.icons_dir = config_.get(
            'schemingdcat.icons_dir',
            sd_config.icons_dir
            )

        sd_config.organization_custom_facets = toolkit.asbool(
            config_.get('schemingdcat.organization_custom_facets',
                        sd_config.organization_custom_facets)
            )

        sd_config.group_custom_facets = toolkit.asbool(
            config_.get('schemingdcat.group_custom_facets',
                        sd_config.group_custom_facets
                        )
            )
        
        sd_config.debug = toolkit.asbool(
            config_.get('debug',
                        sd_config.debug
                        )
            )

        # Default value use local ckan instance with /csw
        sd_config.geometadata_base_uri = config_.get(
            'schemingdcat.geometadata_base_uri',
            '/csw'
            )

        # Load yamls config files, if not in debug mode
        if not sd_config.debug:
            init_config()

        # configure Faceted class (parent of this)
        self.facet_load_config(config_.get(
            'schemingdcat.facet_list',
            '').split())
        
        
    def get_helpers(self):
        respuesta = dict(helpers.all_helpers)
        return respuesta
    
    def get_validators(self):
        return dict(validators.all_validators)

    #IBlueprint
    def get_blueprint(self):
        return blueprint.schemingdcat


class SchemingDcatDatasetsPlugin(SchemingDatasetsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)

    def read_template(self):
        return 'schemingdcat/package/read.html'
    
    def resource_template(self):
        return 'schemingdcat/package/resource_read.html'

class SchemingDcatGroupsPlugin(SchemingGroupsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IGroupForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)

    def about_template(self):
        return 'schemingdcat/group/about.html'

class SchemingDcatOrganizationsPlugin(SchemingOrganizationsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IGroupForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)
    
    def about_template(self):
        return 'schemingdcat/organization/about.html'

    