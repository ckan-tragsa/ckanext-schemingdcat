# encoding: utf-8
import ckan.model as model
import ckan.lib.base as base
import ckan.logic as logic
from flask import Blueprint

import ckan.plugins.toolkit as toolkit

import ckanext.schemingdcat.utils as sdct_utils
from ckanext.schemingdcat.utils import deprecated
import ckanext.schemingdcat.helpers as sdct_helpers

from logging import getLogger

logger = getLogger(__name__)
get_action = logic.get_action
_ = toolkit._

schemingdcat = Blueprint(u'schemingdcat', __name__)

def endpoints():
    return toolkit.render('schemingdcat/endpoints/index.html',extra_vars={
            u'endpoints': sdct_helpers.get_schemingdcat_get_catalog_endpoints(),
        })
    
def metadata_templates():
    return toolkit.render('schemingdcat/metadata_templates/index.html',extra_vars={
            u'metadata_templates': sdct_helpers.get_schemingdcat_get_catalog_endpoints(),
        })

schemingdcat.add_url_rule("/endpoints/", view_func=endpoints, endpoint="endpoint_index", strict_slashes=False)
schemingdcat.add_url_rule("/metadata-templates/", view_func=metadata_templates, endpoint="metadata_templates", strict_slashes=False)

@schemingdcat.route(u'/dataset/linked_data/<id>')
@deprecated
def index(id):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': toolkit.g.user,
        u'for_view': True,
        u'auth_user_obj': toolkit.g.userobj
    }
    data_dict = {u'id': id, u'include_tracking': True}

    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
        schema = get_action(u'package_show')(context, data_dict)
    except (logic.NotFound, logic.NotAuthorized):
        return base.abort(404, _(u'Dataset {dataset} not found').format(dataset=id))

    return toolkit.render('schemingdcat/custom_data/index.html',extra_vars={
            u'pkg_dict': pkg_dict,
            u'endpoint': 'dcat.read_dataset',
            u'data_list': sdct_utils.get_linked_data(id),
        })

@schemingdcat.route(u'/dataset/geospatial_metadata/<id>')
@deprecated
def geospatial_metadata(id):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': toolkit.g.user,
        u'for_view': True,
        u'auth_user_obj': toolkit.g.userobj
    }
    data_dict = {u'id': id, u'include_tracking': True}

    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
    except (logic.NotFound, logic.NotAuthorized):
        return base.abort(404, _(u'Dataset {dataset} not found').format(dataset=id))

    return toolkit.render('schemingdcat/custom_data/index.html', extra_vars={
        u'pkg_dict': pkg_dict,
        u'id': id,
        u'data_list': sdct_utils.get_geospatial_metadata(),
    })