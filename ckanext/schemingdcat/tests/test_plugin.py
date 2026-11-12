import pytest
from ckan.plugins import toolkit
from ckan.tests import helpers, factories
import ckanext.schemingdcat.plugin as plugin


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestSchemingDCATPlugin:

    def test_update_config(self):
        config = {}
        plugin_instance = plugin.SchemingDCATPlugin()
        plugin_instance.update_config(config)
        assert "plugin_template_paths" in config
        assert "plugin_public_paths" in config

    def test_get_helpers(self):
        plugin_instance = plugin.SchemingDCATPlugin()
        helpers = plugin_instance.get_helpers()
        assert isinstance(helpers, dict)
        assert "get_schemingdcat_get_catalog_endpoints" in helpers

    def test_get_validators(self):
        plugin_instance = plugin.SchemingDCATPlugin()
        validators = plugin_instance.get_validators()
        assert isinstance(validators, dict)
        assert "schemingdcat_valid_json_object" in validators

    def test_get_blueprint(self):
        plugin_instance = plugin.SchemingDCATPlugin()
        blueprints = plugin_instance.get_blueprint()
        assert isinstance(blueprints, list)
        assert len(blueprints) > 0

    def test_get_commands(self):
        plugin_instance = plugin.SchemingDCATPlugin()
        commands = plugin_instance.get_commands()
        assert isinstance(commands, list)
        assert len(commands) > 0

    def test_get_signal_subscriptions(self):
        plugin_instance = plugin.SchemingDCATPlugin()
        subscriptions = plugin_instance.get_signal_subscriptions()
        assert isinstance(subscriptions, list)
        assert len(subscriptions) > 0


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestSchemingDCATDatasetsPlugin:

    def test_get_actions(self):
        plugin_instance = plugin.SchemingDCATDatasetsPlugin()
        actions = plugin_instance.get_actions()
        assert isinstance(actions, dict)
        assert "schemingdcat_dataset_schema_name" in actions

    def test_validate(self):
        plugin_instance = plugin.SchemingDCATDatasetsPlugin()
        context = {}
        data_dict = {"type": "dataset"}
        schema = {}
        action = "package_create"
        result, errors = plugin_instance.validate(context, data_dict, schema, action)
        assert isinstance(result, dict)
        assert isinstance(errors, dict)


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestSchemingDCATGroupsPlugin:

    def test_about_template(self):
        plugin_instance = plugin.SchemingDCATGroupsPlugin()
        template = plugin_instance.about_template()
        assert template == "schemingdcat/group/about.html"


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestSchemingDCATOrganizationsPlugin:

    def test_about_template(self):
        plugin_instance = plugin.SchemingDCATOrganizationsPlugin()
        template = plugin_instance.about_template()
        assert template == "schemingdcat/organization/about.html"