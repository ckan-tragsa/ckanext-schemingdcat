# -*- coding: utf-8 -*-
import pytest
from flask import url_for
from ckan.plugins.toolkit import config
from ckan.tests import factories

@pytest.mark.usefixtures('with_plugins', 'clean_db', 'clean_index')
class TestSchemingDCATBlueprints:

    def test_endpoints(self, app):
        with app.flask_app.test_request_context():
            url = url_for('schemingdcat.endpoint_index')
            response = app.get(url)
            assert response.status_code == 200
            assert 'endpoints' in response.body

    def test_metadata_templates(self, app):
        with app.flask_app.test_request_context():
            url = url_for('schemingdcat.metadata_templates')
            response = app.get(url)
            assert response.status_code == 200
            assert 'metadata_templates' in response.body

    def test_linked_data(self, app):
        dataset = factories.Dataset()
        with app.flask_app.test_request_context():
            url = url_for('schemingdcat.index', id=dataset['id'])
            response = app.get(url)
            assert response.status_code == 200
            assert 'pkg_dict' in response.body
            assert 'data_list' in response.body

    def test_geospatial_metadata(self, app):
        dataset = factories.Dataset()
        with app.flask_app.test_request_context():
            url = url_for('schemingdcat.geospatial_metadata', id=dataset['id'])
            response = app.get(url)
            assert response.status_code == 200
            assert 'pkg_dict' in response.body
            assert 'data_list' in response.body

    def test_linked_data_not_found(self, app):
        url = url_for('schemingdcat.index', id='nonexistent-id')
        response = app.get(url, status=404)
        assert response.status_code == 404

    def test_geospatial_metadata_not_found(self, app):
        with app.flask_app.test_request_context():
            url = url_for('schemingdcat.geospatial_metadata', id='nonexistent-id')
            response = app.get(url, status=404)
            assert response.status_code == 404