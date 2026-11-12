from __future__ import annotations
import logging
from typing import Any

import ckan.plugins as p
from ckan import types
from ckan.logic import NotFound
from ckan.lib import helpers as ckan_helpers

import ckanext.schemingdcat.statistics.model as sdct_model
from ckanext.schemingdcat.config import (
    DCAT_AP_DATASTORE_DATASERVICE
)
from ckanext.schemingdcat.helpers import schemingdcat_get_ckan_site_url

log = logging.getLogger(__name__)

def get_subscriptions():
    return {
        p.toolkit.signals.action_succeeded: [
            {"sender": "bulk_update_public", "receiver": schemingdcat_stats_changed},
            {"sender": "bulk_update_private", "receiver": schemingdcat_stats_changed},
            {"sender": "bulk_update_delete", "receiver": schemingdcat_stats_changed},
            {"sender": "schemingdcat_harvest_package_updated", "receiver": schemingdcat_stats_changed},
            {"sender": "schemingdcat_harvest_package_created", "receiver": schemingdcat_stats_changed},
            {"sender": "package_create", "receiver": schemingdcat_stats_changed},
            {"sender": "package_create_rest", "receiver": schemingdcat_stats_changed},
            {"sender": "package_update", "receiver": schemingdcat_stats_changed},
            {"sender": "package_update_rest", "receiver": schemingdcat_stats_changed},
            {"sender": "package_delete", "receiver": schemingdcat_stats_changed},
            {"sender": "group_create", "receiver": schemingdcat_stats_changed},
            {"sender": "group_update", "receiver": schemingdcat_stats_changed},
            {"sender": "group_delete", "receiver": schemingdcat_stats_changed},
            {"sender": "organization_create", "receiver": schemingdcat_stats_changed},
            {"sender": "organization_update", "receiver": schemingdcat_stats_changed},
            {"sender": "organization_delete", "receiver": schemingdcat_stats_changed},
            {"sender": "datastore_create", "receiver": schemingdcat_update_dcat_dataservice},
        ]
    }
    
def schemingdcat_stats_changed(sender: str, **kwargs: Any):
    """
    Handles the event when certain actions are performed and updates site statistics.

    Args:
        sender (str): The name of the sender that triggered the event.
        **kwargs (Any): Additional keyword arguments passed to the function.

    Raises:
        Exception: If updating site statistics fails, an error is logged.
    """
    try:
        log.debug(f"[{sender}] -> Update Open Data site statistics")
        sdct_model.update_table()
    except Exception as e:
        log.error(f"Failed to Update Open Data site statistics: {e}")

def schemingdcat_update_dcat_dataservice(sender: str, **kwargs: Any):
    """
    Handles the event when a datastore is created and updates the DCAT dataservice.

    Args:
        sender (str): The name of the sender that triggered the event.
        **kwargs (Any): Additional keyword arguments passed to the function.

    Raises:
        Exception: If updating the DCAT dataservice fails, an error is logged.
    """
    try:
        log.debug(f"[{sender}] -> Update DCAT dataservice")
        data_dict = kwargs["data_dict"]
        ckan_site_url = schemingdcat_get_ckan_site_url()
        resource_id = data_dict['resource_id']
        context = {
                "ignore_auth": True
            }
        
        try:
            res = p.toolkit.get_action('resource_show')(context, {'id': resource_id})
            dataset_id = res['package_id']
            endpoint_description = p.toolkit.config.get(
                "ckanext.schemingdcat.dcat_ap.datastore_dataservice.endpoint_description",
                DCAT_AP_DATASTORE_DATASERVICE['endpoint_description']
            ).format(ckan_site_url=ckan_site_url)
            
            # Ensure the endpoint_description ends with a slash
            if not endpoint_description.endswith('/'):
                endpoint_description += '/'
            
            log.debug('ckan_site_url:%s and ckan_catalog_uri: %s', ckan_site_url, p.toolkit.config.get('ckanext.dcat.base_uri').rstrip('/'))

            access_services = [
                {
                    "uri": DCAT_AP_DATASTORE_DATASERVICE['uri'].format(ckan_site_url=ckan_site_url),
                    "title": p.toolkit.config.get("ckanext.schemingdcat.dcat_ap.datastore_dataservice.title", DCAT_AP_DATASTORE_DATASERVICE['title']),
                    "description": p.toolkit.config.get("ckanext.schemingdcat.dcat_ap.datastore_dataservice.description", DCAT_AP_DATASTORE_DATASERVICE['description']),
                    "endpoint_description": endpoint_description,
                    "endpoint_url": [url.format(ckan_site_url=ckan_site_url) for url in DCAT_AP_DATASTORE_DATASERVICE['endpoint_url']],
                    "serves_dataset": [url.format(ckan_site_url=ckan_site_url, dataset_id=dataset_id) for url in DCAT_AP_DATASTORE_DATASERVICE['serves_dataset']]
                }
            ]
            patch_data = {
                "id": resource_id,
                "access_url": ckan_helpers.url_for('resource.read', id=dataset_id, resource_id=resource_id, _external=True),
                "download_url": ckan_helpers.url_for('resource.download', id=dataset_id, resource_id=resource_id, _external=True),
                "access_services": access_services
            }

            p.toolkit.get_action('resource_patch')(context, patch_data)
            log.debug(f"dcat:accessService successful patched for Datastore resource_id: {resource_id}")
            
        except NotFound:
            pass
        except Exception as e:
            log.error(f"Failed to show resource: {e}")
            
    except Exception as e:
        log.error(f"Failed to Update DCAT dataservice: {e}")