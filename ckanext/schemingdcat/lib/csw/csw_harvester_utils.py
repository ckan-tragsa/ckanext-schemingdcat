import re
from collections import namedtuple
from urllib.parse import urlparse
from dateutil.parser import parse as dateutil_parse, ParserError
from dateutil.tz import tz

import ckan.plugins as p
from ckan import model
from ckan.model import Session
from ckan.logic import get_action
from ckan.lib.search.common import SearchError

import logging


log = logging.getLogger(__name__)

NOTIFICATION_USER = 'harvest-notification'
DEFAULT_TIMEZONE = tz.gettz(p.toolkit.config.get('ckan.display_timezone', 'UTC'))

CSWDatasetInfo = namedtuple('CSWDatasetInfo',
                              ['name', 'belongs_to_harvester', 'package_id'])

def get_organization_slug_for_harvest_source(harvest_source_id):
    """Retrieve the organization slug for a given harvest source.

    Args:
        harvest_source_id (str): The ID of the harvest source.

    Returns:
        str: The slug (name) of the organization associated with the harvest source.

    Raises:
        p.toolkit.ObjectNotFound: If the harvest source or organization is not found.
    """
    context = get_default_context()
    try:
        source_dataset = p.toolkit.get_action('package_show')(context, {'id': harvest_source_id})
        return source_dataset.get('organization').get('name')
    except (KeyError, IndexError, TypeError):
        raise p.toolkit.ObjectNotFound
    
def get_default_context():
    return {
        'model': model,
        'session': Session,
        'ignore_auth': True
    }
    
def get_packages_to_delete(existing_dataset_identifiers, gathered_identifiers):
    """
    Determine which packages should be deleted based on the existing and gathered identifiers.

    Args:
        existing_dataset_identifiers (list): List of existing dataset identifiers.
        gathered_identifiers (list): List of gathered dataset identifiers.

    Returns:
        list: List of identifiers to be deleted.
    """
    existing_set = set(existing_dataset_identifiers)
    gathered_set = set(gathered_identifiers)
    to_delete = existing_set - gathered_set
    return list(to_delete)

def check_existing_package_by_identifier(identifier, return_fields=None):
    """Check if an existing package exists by its identifier.

    Args:
        identifier (str): The dataset identifier to check.
        return_fields (list, optional): List of fields to return. Defaults to None.

    Returns:
        bool: True if the package exists, False otherwise.

    This method searches for an existing package in the CKAN instance based on its identifier.
    It takes an identifier and an optional list of fields to return. The method returns True if
    a matching package is found, or False if no matching package is found.

    Example:
        exists = check_existing_package_by_identifier('dataset-identifier')

    Raises:
        p.toolkit.ObjectNotFound: If the package is not found.
    """
    escaped_identifier = escape_solr_query(identifier)
    data_dict = {
        "fq": f"identifier:{escaped_identifier}",
        "include_private": True,
    }

    if return_fields and isinstance(return_fields, list):
        data_dict["fl"] = ",".join(
            field
            if isinstance(field, str) and field == field.strip()
            else str(field).strip()
            for field in return_fields
        )

    package_search_context = {
        "model": model,
        "session": Session,
        "ignore_auth": True,
    }

    try:
        search_results = get_action("package_search")(package_search_context, data_dict)
        return search_results['count'] > 0
    except SearchError as e:
        log.error(f"SOLR returned an error running query: {data_dict} Error: {e}")
        return False
    except p.toolkit.ObjectNotFound:
        return False
    
def escape_solr_query(query):
    """Escape special characters in a Solr query.

    Args:
        query (str): The query string to escape.

    Returns:
        str: The escaped query string.

    This function escapes special characters in a Solr query string to prevent
    syntax errors in Solr queries.

    Example:
        escaped_query = escape_solr_query('identifier:{309e871c-e108-426d-ab0f-f8aa46117574}_200001_es')
    """
    # List of special characters in Solr that need to be escaped
    special_chars = r'[\+\-\!\(\)\{\}\[\]\^"~\*\?:\\]'
    # Escape each special character with a backslash
    escaped_query = re.sub(special_chars, r'\\\g<0>', query)
    return escaped_query

def get_value_from_object_extra(harvest_object_extras, key):
    """
    Retrieve the value associated with a given key from a list of harvest object extras.

    Args:
        harvest_object_extras (list): A list of objects containing extra metadata.
        key (str): The key to search for in the extras.

    Returns:
        str: The value associated with the given key, or None if the key is not found.
    """
    for extra in harvest_object_extras:
        if extra.key == key:
            return extra.value
    return None

def find_package_for_identifier(identifier):
    """
    Find a package in CKAN for a given identifier.

    Args:
        identifier (str): The identifier to search for.

    Returns:
        CSWDatasetInfo: A named tuple containing the dataset information if found, or None if not found.

    Raises:
        Exception: If an error occurs while searching for the package.
    """
    context = get_default_context()
    fq = "identifier:({})".format(identifier)
    try:
        result = p.toolkit.get_action('package_search')(context,
                                                        {'fq': fq,
                                                         'include_private': True})
        if result.get('count') > 0:
            pkg = result['results'][0]
            return CSWDatasetInfo(name=pkg['name'],
                                  package_id=pkg['id'],
                                  belongs_to_harvester=True)
        else:
            return None
    except Exception as e:
        print("Error occurred while searching for packages with fq: {}, error: {}"
              .format(fq, e))
        return None
    
def map_resources_to_ids(pkg_dict, package_id):
    existing_package = \
        p.toolkit.get_action('package_show')({}, {'id': package_id})
    existing_resources = existing_package.get('resources')
    existing_resources_mapping = \
        {r['id']: _get_resource_id_string(r) for r in existing_resources}
    for resource in pkg_dict.get('resources'):
        resource_id_dict = _get_resource_id_string(resource)
        id_to_reuse = [k for k, v in existing_resources_mapping.items()
                       if v == resource_id_dict]
        if id_to_reuse:
            id_to_reuse = id_to_reuse[0]
            resource['id'] = id_to_reuse
            del existing_resources_mapping[id_to_reuse]
    return existing_package

def _get_resource_id_string(resource):
    return resource.get('url')

def check_package_change(existing_pkg, dataset_dict):
    # Ensure to clear the key values if they are not
    # in the new dataset_dict
    for key in existing_pkg.keys():
        if key not in dataset_dict or not dataset_dict[key]:
            existing_pkg[key] = ''
    if _changes_in_date(
            existing_pkg.get('modified'), dataset_dict.get('modified')):
        msg = "dataset modified date changed: {}" \
            .format(dataset_dict.get('modified'))
        return True, msg
    resources = dataset_dict.get('resources', [])
    existing_resources = existing_pkg.get('resources', [])
    resource_count_changed = len(existing_resources) != len(resources)
    if resource_count_changed:
        msg = "resource count changed: {}".format(len(resources))
        return True, msg
    for resource in resources:
        matching_existing_resource_with_same_url = [
            existing_resource
            for existing_resource in existing_resources
            if existing_resource.get('url') == resource.get('url')
        ]
        if not matching_existing_resource_with_same_url:
            msg = "resource access url changed: {}".format(resource.get('url'))
            return True, msg
        matching_existing_resource = \
            matching_existing_resource_with_same_url[0]
        download_url_changed = \
            matching_existing_resource.get('download_url') != \
            resource.get('download_url')
        if download_url_changed:
            msg = "resource download url changed: {}" \
                .format(resource.get('download_url'))
            return True, msg
        if _changes_in_date(matching_existing_resource.get('modified'),
                            resource.get('modified')):
            msg = "resource modified date changed: {}" \
                .format(resource.get('modified'))
            return True, msg
    return False, None

def _changes_in_date(existing_datetime, new_datetime):
    if not existing_datetime and not new_datetime:
        return False
    if not existing_datetime or not new_datetime:
        return True

    try:
        existing = dateutil_parse(existing_datetime)
        if existing.tzinfo is None:
            existing = existing.replace(tzinfo=DEFAULT_TIMEZONE)
            log.debug(
                "Datetime %s has no time zone info: assuming %s" %
                existing_datetime,
                DEFAULT_TIMEZONE
            )
        new = dateutil_parse(new_datetime)
        if new.tzinfo is None:
            new = new.replace(tzinfo=DEFAULT_TIMEZONE)
            log.debug(
                "Datetime %s has no time zone info: assuming %s" %
                new_datetime,
                DEFAULT_TIMEZONE
            )
    except (ParserError, OverflowError) as e:
        log.info(
            "Error when parsing dates {}, {}: {}".format(
                existing_datetime, new_datetime, e
            )
        )
        return False

    if new == existing:
        return False
    return True

def is_valid_url(url):
    parsed_url = urlparse(url)
    try:
        if parsed_url.scheme and parsed_url.netloc:
            return url
    except Exception:
        log.warning(
            "provided URL {} for conforms_to field is not valid".format(url)
        )
        return ''