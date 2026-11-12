import six
import re
import yaml
from collections import defaultdict
import json
from typing import Dict, List, Union
from yaml.loader import SafeLoader
from pathlib import Path
from functools import lru_cache
import datetime
from urllib.parse import urlparse, unquote, urljoin, urlunparse
from urllib.error import URLError
from six.moves.urllib.parse import urlencode
import typing

from ckan.common import json, c, request
from ckan.lib import helpers as ckan_helpers
import ckan.logic as logic
from ckan import model
from ckan.lib.i18n import get_available_locales, get_lang
import ckan.plugins as p
import ckan.authz as authz

from ckanext.scheming.helpers import (
    scheming_choices_label,
    scheming_language_text,
    scheming_dataset_schemas,
    scheming_get_schema
)

from ckanext.harvest.helpers import (
    get_harvest_source
)
from ckanext.harvest.utils import (
    DATASET_TYPE_NAME
)

import ckanext.schemingdcat.config as sdct_config
from ckanext.schemingdcat.utils import (
    get_facets_dict,
    public_file_exists,
    public_dir_exists,
    schemingdcat_catalog_endpoints,
    schemingdcat_get_geospatial_metadata
)
from ckanext.dcat.utils import CONTENT_TYPES
from ckanext.fluent.validators import LANG_SUFFIX
import logging

log = logging.getLogger(__name__)

all_helpers = {}
prettify_cache = {}
DEFAULT_LANG = None
_open_data_statistics = {}
trans = authz.roles_trans()

def translated_capacity(capacity: str) -> str:
    """
    Translate a given capacity string to its corresponding translated value.

    This function attempts to translate the input `capacity` string using a predefined
    translation dictionary `trans`. If the `capacity` string is not found in the 
    dictionary, it returns the original `capacity` string.

    Args:
        capacity (str): The capacity string to be translated.

    Returns:
        str: The translated capacity string if found in the translation dictionary,
             otherwise the original capacity string.

    Example:
        >>> trans = {'admin': 'Administrador', 'editor': 'Editor'}
        >>> translated_capacity('admin')
        'Administrador'
        >>> translated_capacity('viewer')
        'viewer'
    """
    try:
        return trans[capacity]
    except KeyError:
        return capacity

@lru_cache(maxsize=16)
def get_scheming_dataset_schemas():
    """
    Fetches the dataset schemas using the scheming_dataset_schemas function.

    This function attempts to retrieve the dataset schemas. If a KeyError is encountered,
    it logs the error and returns an empty dictionary.

    Returns:
        dict: The dataset schemas if successfully retrieved, otherwise an empty dictionary.

    Raises:
        KeyError: If there is an issue accessing the dataset schemas.
    """
    try:
        return scheming_dataset_schemas()
    except KeyError as e:
        log.error('KeyError encountered while fetching dataset schemas: %s', e)
        return {}

def helper(fn):
    """Collect helper functions into the ckanext.schemingdcat.all_helpers dictionary.

    Args:
        fn (function): The helper function to add to the dictionary.

    Returns:
        function: The helper function.
    """
    all_helpers[fn.__name__] = fn
    return fn


@helper
def schemingdcat_get_schema_names():
    """
    Get the `schema_name` of all the schemas loaded.

    Returns:
        list: A list of schema names.
    """
    return [schema["schema_name"] for schema in sdct_config.schemas.values()]

@helper
def schemingdcat_get_schema_dataset_types():
    """
    Get the `dataset_type` of all the schemas loaded.

    Returns:
        list: A list of schema names.
    """
    return [schema["dataset_type"] for schema in sdct_config.schemas.values()]


@helper
def get_facet_items_with_deserialized_names(facet_items):
    import json
    for item in facet_items:
        try:
            # Verificar si las cadenas no están vacías antes de deserializar
            if item['name'] and item['display_name']:
                names = json.loads(item['name'])
                display_names = json.loads(item['display_name'])
                
                # Combinar las listas
                item['combined'] = list(zip(names, display_names))
            else:
                item['combined'] = []
        except json.JSONDecodeError:
            item['combined'] = []
        
    return facet_items

@lru_cache(maxsize=8)
@helper
def schemingdcat_default_facet_search_operator():
    """Return the default facet search operator: AND or OR.

    Returns:
        str: The default facet search operator ('AND' or 'OR').
    """
    allowed_operators = {'AND', 'OR'}
    facet_operator = p.toolkit.config.get('ckanext.schemingdcat.default_facet_operator', 'OR').upper()

    return facet_operator if facet_operator in allowed_operators else 'OR'

@helper
def schemingdcat_decode_json(json_text):
    """Convert a JSON string to a Python object.

    Args:
        json_text (str): The JSON string to convert.

    Returns:
        object: A Python object representing the JSON data.
    """
    return json.loads(json_text)


@helper
def schemingdcat_organization_name(org_id):
    """Return the name of the organization from its ID.

    Args:
        org_id (dict): A dictionary containing the ID of the organization.

    Returns:
        str: The name of the organization, or None if the organization cannot be found.
    """
    org_name = None
    try:
        org_dic = ckan_helpers.get_organization(org_id["display_name"])
        if org_dic is not None:
            org_name = org_dic["display_name"]
        else:
            log.warning(
                "Could not find the name of the organization with ID {0}".format(
                    org_id["display_name"]
                )
            )
    except Exception as e:
        log.error(
            "Exception while trying to find the name of the organization: {0}".format(e)
        )
    return org_name

@helper
def schemingdcat_default_organization_name():
    """Return the name of the first available organization as a default.

    Returns:
        str: The name of the first available organization, or None if no organizations are available.
    """
    default_org_name = None
    try:
        organizations = ckan_helpers.organizations_available()
        if organizations:
            default_org_name = organizations[0]["name"]
        else:
            log.warning("No organizations available to set as default.")
    except Exception as e:
        log.error(
            "Exception while trying to find the default organization name: {0}".format(e)
        )
    return default_org_name

@helper
def schemingdcat_get_facet_label(facet):
    """Return the label for a given facet.

    Args:
        facet (str): The name of the facet.

    Returns:
        str: The label for the given facet.
    """
    return get_facets_dict[facet]


@helper
def schemingdcat_get_facet_items_dict(
    facet, search_facets=None, limit=None, exclude_active=False, scheming_choices=None
):
    """Return the list of unselected facet items for the given facet, sorted
    by count.

    Returns the list of unselected facet contraints or facet items (e.g. tag
    names like "russian" or "tolstoy") for the given search facet (e.g.
    "tags"), sorted by facet item count (i.e. the number of search results that
    match each facet item).

    Reads the complete list of facet items for the given facet from
    search_facets, and filters out the facet items that the user has already
    selected.

    List of facet items are ordered acording the faccet_sort parameter

    Arguments:
    facet -- the name of the facet to filter.
    search_facets -- dict with search facets in Flask (c.search_facets in Pylons)
    limit -- the max. number of facet items to return.
    exclude_active -- only return unselected facets.
    scheming_choices -- scheming choices to use to get label from value.

    """

    #log.debug("Returning facets for: {0}".format(facet))

    order = "default"
    items = []
    seen_items = set()

    search_facets = search_facets or getattr(c, "search_facets", None)
    #log.debug("search_facets RAW: {0}".format(search_facets))
    
    if (
            search_facets
            and isinstance(search_facets, dict)
            and search_facets.get(facet, {}).get("items")
        ):
            for facet_item in search_facets.get(facet)["items"]:
                try:
                    names = [facet_item["name"]]
                    display_names = [facet_item["display_name"]]
                    labels =  [facet_item.get("label", facet_item["display_name"])]
                except (ValueError, SyntaxError) as e:
                    log.error("Error parsing facet_item: {0}".format(e))
                    continue
        
                # Make sure labels are the same size as names and display_names.
                if len(labels) != len(names):
                    labels = display_names
    
                for name, display_name, label in zip(names, display_names, labels):
                    item = {
                        "name": name,
                        "display_name": display_name,
                        "count": facet_item["count"],
                        "label": label
                    }
    
                    if scheming_choices:
                        item["label"] = scheming_choices_label(
                            scheming_choices, item["name"]
                        )
                    else:
                        item["label"] = item["display_name"]
    
                    if not len(item["name"].strip()):
                        log.debug("Skipping facet_item with empty name")
                        continue
    
                    # Avoid duplicates
                    item_key = (item["name"], item["display_name"], item["label"])
                    if item_key in seen_items:
                        continue
                    seen_items.add(item_key)
    
                    params_items = request.args.items(multi=True)
    
                    if (facet, item["name"]) not in params_items:
                        items.append(dict(active=False, **item))
                    elif not exclude_active:
                        items.append(dict(active=True, **item))
    
                    order_lst = request.args.getlist("_%s_sort" % facet)
                    if len(order_lst):
                        order = order_lst[0]
                        log.debug("order: {0}".format(order))
    
            # Sort descending by count and ascending by case-sensitive display name
            sorts = {
                "name": ("label", False),
                "name_r": ("label", True),
                "count": ("count", False),
                "count_r": ("count", True),
            }
            if sorts.get(order):
                items.sort(
                    key=lambda it: (it[sorts.get(order)[0]]), reverse=sorts.get(order)[1]
                )
            else:
                items.sort(key=lambda it: (-it["count"], it["label"].lower()))
    
            if hasattr(c, "search_facets_limits"):
                if c.search_facets_limits and limit is None:
                    limit = c.search_facets_limits.get(facet)
    
            # zero treated as infinite for hysterical raisins
            if limit is not None and limit > 0:
                return items[:limit]

    return items

@helper
def schemingdcat_new_order_url(facet_name, order_concept, extras=None):
    """Return a URL with the order parameter for the given facet and concept to use.

    Based on the actual order, it rotates cyclically from no order -> direct order -> inverse order over the given concept.

    Args:
        facet_name (str): The name of the facet to order.
        order_concept (str): The concept (name or count) that will be used to order.
        extras (dict, optional): Extra parameters to include in the URL.

    Returns:
        str: The URL with the order parameter for the given facet and concept.
    """
    old_order = None
    order_param = "_%s_sort" % facet_name
    order_lst = request.args.getlist(order_param)
    if not extras:
        extras = {}

    controller = getattr(c, "controller", False) or request.blueprint
    action = getattr(c, "action", False) or p.toolkit.get_endpoint()[1]
    url = ckan_helpers.url_for(controller=controller, action=action, **extras)

    if len(order_lst):
        old_order = order_lst[0]

    order_mapping = {
        "name": {"name": "name_r", "name_r": None, None: "name"},
        "count": {"count": "count_r", "count_r": None, None: "count"},
    }

    new_order = order_mapping.get(order_concept, {}).get(old_order)

    params_items = request.args.items(multi=True)

    params_nopage = [(k, v) for k, v in params_items if k != order_param]

    if new_order:
        params_nopage.append((order_param, new_order))

    if params_nopage:
        url = url + "?" + urlencode(params_nopage)

    return url

@helper
def schemingdcat_get_open_data_statistics(stat_type=None):
    """
    Retrieves Open Data portal statistics including counts of datasets, distributions, groups, organizations, tags, spatial datasets, and endpoints.

    Args:
        stat_type (str, optional): The type of statistics to filter by. If None, all statistics are returned.

    Returns:
        dict: A dictionary containing the counts of various site elements, with keys as the 'id' and values as dictionaries containing 'value', 'label', 'icon', 'stat_count', and 'stat_type'.
    """
    global _open_data_statistics

    # Retrieve the statistics list from the action
    stats_list = logic.get_action("schemingdcat_statistics_list")({}, {})
    
    # Convert the list of dictionaries to a summarized dictionary
    for stat in stats_list:
        stat_id = stat['id']
        if stat_id in _open_data_statistics:
            # Update only the stat_count if the entry already exists in the cache
            _open_data_statistics[stat_id]['stat_count'] = stat['stat_count']
        else:
            # Add new entry to the cache
            _open_data_statistics[stat_id] = {
                'value': stat['value'],
                'label': stat['label'],
                'icon': stat['icon'],
                'stat_count': stat['stat_count'],
                'stat_type': stat['stat_type']
            }
    
    # Filter the statistics by stat_type if provided
    if stat_type is not None:
        filtered_statistics = {k: v for k, v in _open_data_statistics.items() if v['stat_type'] == stat_type}
        return filtered_statistics

    return _open_data_statistics

@helper
def schemingdcat_get_social_links(platform=None):
    """
    Retrieves social media links for GitHub, LinkedIn, and X from the configuration.
    
    Args:
        platform (str, optional): The specific platform to retrieve the link for. 
                                  Can be 'github', 'linkedin', or 'x'. 
                                  If None, returns a dictionary with all links.
    
    Returns:
        dict or str: A dictionary containing the social media links for GitHub, LinkedIn, and X,
                     or a single link if a platform is specified.
    """
    if not sdct_config.social_links:
        sdct_config.social_links = {
            'github': p.toolkit.config.get('ckanext.schemingdcat.social_github'),
            'linkedin': p.toolkit.config.get('ckanext.schemingdcat.social_linkedin'),
            'x': p.toolkit.config.get('ckanext.schemingdcat.social_x')
        }
    
    if platform:
        return sdct_config.social_links.get(platform.lower(), None)
    
    return sdct_config.social_links

@lru_cache(maxsize=16)
@helper
def schemingdcat_get_icons_dir(field_tuple=None, field_name=None):
    """
    Returns the defined icons directory for a given scheming field definition or field name.

    This function is used to retrieve the icons directory associated with a 
    specific field in a scheming dataset or directly by field name. If no icons directory is defined, 
    the function will return None.

    Args:
        field (dict, optional): A dictionary representing the scheming field definition. 
                                This should include all the properties of the field, 
                                including the icons directory if one is defined.
        field_name (str, optional): The name of the field. If provided, the function will 
                                     look for an icons directory with this name.

    Returns:
        str: A string representing the icons directory for the field or field name. 
             If no icons directory is defined or found, the function will return None.
    """
    if field_tuple:
        field = dict(field_tuple)
        if "icons_dir" in field:
            return field["icons_dir"]

        if "field_name" in field:
            dir = p.toolkit.config.get('ckanext.schemingdcat.icons_dir') + "/" + field["field_name"]
            if public_dir_exists(dir):
                return dir

    elif field_name:
        dir = p.toolkit.config.get('ckanext.schemingdcat.icons_dir') + "/" + field_name
        if public_dir_exists(dir):
            return dir    

    return None

@helper
def schemingdcat_get_default_icon(field):
    """Return the defined default icon for a scheming field definition.

    Args:
        field (dict): The scheming field definition.

    Returns:
        str: The defined default icon, or None if not found.
    """
    if "default_icon" in field:
        return field["default_icon"]

@helper
def schemingdcat_get_open_data_intro_enabled():
    return p.toolkit.config.get('ckanext.schemingdcat.open_data_intro_enabled')

@helper
def schemingdcat_get_inspire_dcat_types():
    """
    Returns the configuration value for INSPIRE DCAT types.

    This function retrieves the configuration value that specifies the INSPIRE 
    DCAT types. These types are used to categorize datasets according to the 
    INSPIRE directive. The function returns the value of the configuration 
    setting `INSPIRE_DCAT_TYPES`.

    Returns:
        list: A list of strings representing the INSPIRE DCAT types.
    """
    return sdct_config.INSPIRE_DCAT_TYPES

@helper
def schemingdcat_get_dataset_custom_facets():
    """
    Returns the custom facets for datasets from the configuration.

    This function retrieves the custom facets for datasets as specified in the 
    configuration. These custom facets are used to categorize datasets according 
    to specific criteria defined in the configuration. The function returns the 
    value of the configuration setting `dataset_custom_facets`.

    Returns:
        list: A list of strings representing the custom facets for datasets.
    """
    return sdct_config.dataset_custom_facets

@helper
def schemingdcat_get_default_package_item_icon():
    """
    Returns the default icon defined for a given scheming field definition.

    This function is used to retrieve the default icon associated with a 
    specific field in a scheming dataset. If no default icon is defined, 
    the function will return None.

    Args:
        field (dict): A dictionary representing the scheming field definition. 
                      This should include all the properties of the field, 
                      including the default icon if one is defined.

    Returns:
        str: A string representing the default icon for the field. This could 
             be a URL, a data URI, or any other string format used to represent 
             images. If no default icon is defined for the field, the function 
             will return None.
    """
    return p.toolkit.config.get('ckanext.schemingdcat.default_package_item_icon')

@helper
def schemingdcat_get_default_package_item_show_spatial():
    """
    Returns the configuration value for showing spatial information in the default package item.

    This function is used to retrieve the configuration value that determines 
    whether the spatial information should be shown in the default package item. 
    If no value is defined in the configuration, the function will return None.

    Returns:
        bool: A boolean value representing whether the spatial information should 
              be shown in the default package item. If no value is defined in the 
              configuration, the function will return None.
    """
    return p.toolkit.config.get('ckanext.schemingdcat.default_package_item_show_spatial')

@helper
def schemingdcat_get_show_metadata_templates_toolbar():
    """
    Returns the configuration value for showing the metadata templates toolbar.

    This function is used to retrieve the configuration value that determines 
    whether the metadata templates toolbar should be shown or not. If the configuration 
    value is not set, the function will return False.

    Returns:
        bool: A boolean value representing whether the metadata templates toolbar 
              should be shown. If the configuration value is not set, the function 
              will return False.
    """
    return p.toolkit.config.get('ckanext.schemingdcat.show_metadata_templates_toolbar')

@helper
def schemingdcat_get_metadata_templates_search_identifier():
    """
    Returns the identifier of catalog metadata templates.

    This function is used to retrieve the default value to retrieve metadata templates. If no default value is defined, 
    the function will return None.


    Returns:
        str: A string representing the default icon identifier of catalog metadata templates.

    """
    return p.toolkit.config.get('ckanext.schemingdcat.metadata_templates_search_identifier')

@helper
def schemingdcat_get_schemingdcat_xls_harvest_templates(search_identifier=p.toolkit.config.get('ckanext.schemingdcat.metadata_templates_search_identifier'), count=10):
    """
    This helper function retrieves the schemingdcat_xls templates from the CKAN instance. 
    It uses the 'package_search' action of the CKAN logic layer to perform a search with specific parameters.
    
    Parameters:
    search_identifier (str): The text to search in the identifier. Default is sdct_config.metadata_templates_search_identifier.
    count (int): The number of featured datasets to retrieve. Default is 10.

    Returns:
    list: A list of dictionaries, each representing a featured dataset. If no results are found, returns None.
    """
    fq = f'+extras_schemingdcat_xls_metadata_template:{True}'
    search_dict = {
        'fq': fq, 
        'fl': 'name,extras_identifier,title,notes,metadata_modified,extras_title_translated,extras_notes_translated',
        'rows': count
    }
    context = {'model': model, 'session': model.Session}
    result = logic.get_action('package_search')(context, search_dict)
    
    if not result['results']:
        fq = f'+extras_schemingdcat_xls_metadata_template:*{search_identifier}*'
        search_dict['fq'] = fq
        result = logic.get_action('package_search')(context, search_dict)

    return result['results'] if result['results'] else None

@helper
def schemingdcat_get_icon(
    choice=None, icons_dir=None, default="/images/default/no_icon.svg", choice_value=None
):
    """Return the relative URL to the icon for the item.

    Args:
        choice (dict, optional): The choice selected for the field.
        icons_dir (str, optional): The path to search for the icon. Usually the common path for icons for this field.
        default (str, optional): The default value to return if no icon is found.
        choice_value (str, optional): The value of the choice selected for the field. If provided, it will be used instead of choice['value'].

    Returns:
        str: The relative URL to the icon, or the default value if not found.
    """
    extensions = [".svg", ".png", ".jpg", ".jpeg", ".gif"]
    icon_name = None

    if choice_value is None and choice:
        choice_value = choice.get("icon") or choice.get("value")

    if choice_value:
        if ckan_helpers.is_url(choice_value):
            url_parts = choice_value.split("/")

            if len(url_parts) == 1:
                icon_name = url_parts[-1].lower()
            else:
                icon_name = url_parts[-2].lower() + "/" + url_parts[-1].lower()
        else:
            icon_name = choice_value

        url_path = (icons_dir + "/" if icons_dir else "") + icon_name

        for extension in extensions:
            if public_file_exists(url_path + extension):
                return url_path + extension

    return default

@helper
def schemingdcat_get_choice_item(field, value):
    """Return the whole choice item for the given value in the scheming field.

    Args:
        field (dict): The scheming field to look for the choice item in.
        value (str): The option item value.

    Returns:
        dict: The whole option item in scheming, or None if not found.
    """
    if field and ("choices" in field):
        #log.debug("Searching: {0} en {1}".format(value,field['choices']))
        for choice in field["choices"]:
            if choice["value"] == value:
                return choice

    return None

@helper
def schemingdcat_get_choice_property(choices, value, property):
    """
    Retrieve a specific property from a choice dictionary based on the given value.

    Args:
        choices (list): List of dictionaries containing "label" and "value" keys.
        value (str): The value to match against the choices.
        property (str): The property to retrieve from the matching choice dictionary.

    Returns:
        str or None: The property value from the matching choice dictionary, or None if not found.
    """
    for c in choices:
        if c['value'] == value:
            return c.get(property, None)
    return None


@helper
def scheming_display_json_list(value):
    """Return the object passed serialized as a JSON list.

    Args:
        value (any): The object to serialize.

    Returns:
        str: The serialized object as a JSON list, or the original value if it cannot be serialized.
    """
    if isinstance(value, six.string_types):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value

@helper
def scheming_clean_json_value(value):
    """Clean a JSON list value to avoid errors with: '"' and spaces.

    Args:
        value (str): The object to serialize.

    Returns:
        str: The cleaned value, or the original value if it cannot be cleaned.
    """
    try:
        value = value.strip(" ").replace('\\"', "%%%@#")
        value = value.replace('"', "")
        value = value.replace("%%%@#", '"')
        return value
    except (TypeError, ValueError):
        return value

def format_eli_label(parsed_url):
    """
    Formats the label for a parsed URL with 'eli' segment.

    Args:
        parsed_url (ParseResult): The parsed URL.

    Returns:
        str: The formatted label.
    """
    segments = parsed_url.path.split('/')
    eli_index = next(i for i, segment in enumerate(segments) if segment == 'eli')
    return '/'.join(segments[eli_index + 1:]).upper()

@helper
def schemingdcat_prettify_url(url):
    """
    Prettifies a URL by removing the protocol and trailing slash.

    Args:
        url (str): The URL to prettify.

    Returns:
        str: The prettified URL, or the original URL if an error occurred.
    """
    if url in prettify_cache:
        return prettify_cache[url]

    try:
        prettified_url = re.sub(r"^https?://(?:www\.)?", "", url).rstrip("/")
        prettify_cache[url] = prettified_url
        return prettified_url
    except (TypeError, AttributeError):
        return url

@helper
def schemingdcat_url_unquote(url):
    """
    Decodes a URL, replacing %xx escapes with their single-character equivalent.

    Args:
        url (str): The URL to decode.

    Returns:
        str: The decoded URL.
    """
    return unquote(url)

@helper
def schemingdcat_prettify_url_name(url):
    """
    Prettifies a URL name by extracting the last segment and cleaning it.

    Args:
        url (str): The URL to extract the name from.

    Returns:
        str: The prettified URL name, or the original URL if an error occurred.
    """
    if url is None:
        return url

    # Convert url to str if it is bytes
    if isinstance(url, bytes):
        url = url.decode('utf-8')

    if url in prettify_cache:
        return prettify_cache[url]

    try:
        parsed_url = urlparse(url)
        
        if '/eli/' in url:
            prettified_url_name = format_eli_label(parsed_url)
        else:
            url_name = parsed_url.path.split("/")[-1].split('.')[0].replace('_', '-')
            prettified_url_name = ' '.join(url_name.split(' ')[:4])

        prettify_cache[url] = prettified_url_name
        return prettified_url_name

    except (URLError, ValueError) as e:
        print(f"Error while prettifying URL: {e}")
        return url

@helper
def schemingdcat_listify_str(values):
    """Converts a string or list/tuple of strings to a list of strings.

    If `values` is already a list or tuple, it is returned as is. If `values` is a string,
    it is split into a list of strings using commas as the delimiter. Each string in the
    resulting list is stripped of leading/trailing whitespace and quotes.

    Args:
        values (str or list or tuple): The value(s) to convert to a list of strings.

    Returns:
        list: A list of strings.
    """
    if isinstance(values, str):
        values = values.strip("][").split(",")
        values = [item.strip().strip('"') for item in values]
    elif not isinstance(values, (list, tuple)):
        log.debug("Not a list or string: {0}".format(values))
        values = [""]

    return values

@helper
def schemingdcat_load_yaml(file, folder="codelists"):
    """Load a YAML file from the folder, by default 'codelists' directory.

    Args:
        file (str): The name of the YAML file to load.

    Returns:
        dict: A dictionary containing the data from the YAML file.
    """
    source_path = Path(__file__).resolve(True)
    yaml_data = {}
    try:
        p = source_path.parent.joinpath(folder, file)
        with open(p, "r") as f:
            yaml_data = yaml.load(f, Loader=SafeLoader)
    except FileNotFoundError:
        log.error("The file {0} does not exist".format(file))
    except Exception as e:
        log.error("Could not read configuration from {0}: {1}".format(file, e))

    return yaml_data

@helper
def schemingdcat_get_linked_data(id):
    """Get linked data for a given identifier.

    Args:
        id (str): The identifier to get linked data for.

    Returns:
        list: A list of dictionaries containing linked data for the identifier.
    """
    return [
        {
            "name": name,
            "display_name": sdct_config.linkeddata_links.get(name, {"display_name": content_type})[
                "display_name"
            ],
            "format": sdct_config.linkeddata_links.get(name, {}).get("format"),
            "image_display_url": sdct_config.linkeddata_links.get(name, {}).get(
                "image_display_url"
            ),
            "endpoint_icon": sdct_config.linkeddata_links.get(name, {}).get(
                "endpoint_icon"
            ),
            "description": sdct_config.linkeddata_links.get(name, {}).get("description")
            or f"Formats {content_type}",
            "description_url": sdct_config.linkeddata_links.get(name, {}).get("description_url"),
            "endpoint": "dcat.read_dataset",
            "endpoint_data": {
                "_id": id,
                "_format": name,
            },
        }
        for name, content_type in CONTENT_TYPES.items()
    ]

@helper
def get_schemingdcat_get_catalog_endpoints():
    """Get the catalog endpoints.

    Returns:
        list: A list of dictionaries containing linked data for the identifier.
    """    
    return schemingdcat_catalog_endpoints()

@helper
def schemingdcat_get_geospatial_endpoint(type="dataset"):
    """Get geospatial base URI for CSW Endpoint.

    Args:
        type (str): The type of endpoint to return. Can be 'catalog' or 'dataset'.

    Returns:
        str: The base URI of the CSW Endpoint with the appropriate format.
    """
    geometadata_base_uri = p.toolkit.config.get('ckanext.schemingdcat.geometadata_base_uri')
    
    try:
        if geometadata_base_uri:
            csw_uri = geometadata_base_uri

        if (
            geometadata_base_uri
            and "/csw" not in geometadata_base_uri
        ):
            csw_uri = geometadata_base_uri.rstrip("/") + "/csw"
        elif geometadata_base_uri == "":
            csw_uri = "/csw"
        else:
            csw_uri = geometadata_base_uri.rstrip("/")
    except:
        csw_uri = "/csw"

    if type == "catalog":
        return csw_uri + "?service=CSW&version={version}&request=GetCapabilities"
    else:
        return (
            csw_uri
            + "?service=CSW&version={version}&request=GetRecordById&id={id}&elementSetName={element_set_name}&outputSchema={output_schema}&OutputFormat={output_format}"
        )

@helper
def schemingdcat_get_all_metadata(id):
    """Get linked data and geospatial metadata for a given identifier.

    Args:
        id (str): The identifier to get linked data and geospatial metadata for.

    Returns:
        list: A list of dictionaries containing linked data and geospatial metadata for the identifier.
    """
    geospatial_metadata = schemingdcat_get_geospatial_metadata()
    linked_data = schemingdcat_get_linked_data(id)

    for metadata in geospatial_metadata:
        metadata["endpoint_type"] = "csw"

    for data in linked_data:
        data["endpoint_type"] = "dcat"

    return geospatial_metadata + linked_data

@helper
def fluent_form_languages(field=None, entity_type=None, object_type=None, schema=None):
    """
    Return a list of language codes for this form (or form field)

    1. return field['form_languages'] if it is defined
    2. return schema['form_languages'] if it is defined
    3. get schema from entity_type + object_type then
       return schema['form_languages'] if they are defined
    4. return languages from site configuration
    """
    if field and "form_languages" in field:
        return field["form_languages"]
    if schema and "form_languages" in schema:
        return schema["form_languages"]
    if entity_type and object_type:
        # late import for compatibility with older ckanext-scheming
        from ckanext.scheming.helpers import scheming_get_schema

        schema = scheming_get_schema(entity_type, object_type)
        if schema and "form_languages" in schema:
            return schema["form_languages"]

    langs = []
    for l in get_available_locales():
        if l.language not in langs:
            langs.append(l.language)
    return langs

@helper
def schemingdcat_fluent_form_label(field, lang):
    """Returns a label for the input field in the specified language.

    If the field has a `fluent_form_label` defined, the label will be taken from there.
    If a matching label cannot be found, this helper will return the standard label
    with the language code in uppercase.

    Args:
        field (dict): A dictionary representing the input field.
        lang (str): A string representing the language code.

    Returns:
        str: A string representing the label for the input field in the specified language.
    """
    form_label = field.get("fluent_form_label", {})
    label = scheming_language_text(form_label.get(lang, field["label"]))
    return f"{label} ({lang.upper()})"

@helper
def schemingdcat_multiple_field_required(field, lang):
    """
    Returns whether a field is required or not based on the field definition and language.

    Args:
        field (dict): The field definition.
        lang (str): The language to check for required fields.

    Returns:
        bool: True if the field is required, False otherwise.
    """
    if "required" in field:
        return field["required"]
    if "required_language" in field and field["required_language"] == lang:
        return True
    return "not_empty" in field.get("validators", "").split()

def parse_json(value, default_value=None):
    try:
        return json.loads(value)
    except (ValueError, TypeError, AttributeError):
        if default_value is not None:
            return default_value
        return value

@helper
def schemingdcat_get_ckan_site_url():
    """
    Get the CKAN site URL from config. First checks for explicit ckan_url,
    if not found constructs URL from site_url and root_path.
    
    Returns:
        str: The site URL without trailing slash
    """
    # Get base site URL first as fallback
    site_url = p.toolkit.config.get('ckan.site_url', '').rstrip('/')
    
    # Try to get explicit ckan_url, use site_url if not found
    ckan_url = p.toolkit.config.get('ckan_url', site_url)
    
    # If using site_url, check for root_path
    if ckan_url == site_url:
        root_path = get_not_lang_root_path()
        if root_path:
            ckan_url = f"{site_url}/{root_path.strip('/')}"
    
    return ckan_url.rstrip('/')

@helper
def get_not_lang_root_path():
    """
    Retrieve the root path from the CKAN configuration, removing the '{{LANG}}' placeholder if present.

    This function fetches the 'ckan.root_path' configuration setting and removes the '/{{LANG}}' 
    placeholder if it exists in the path.

    Returns:
        str: The root path with the '{{LANG}}' placeholder removed if it was present.
    """
    root_path = p.toolkit.config.get('ckan.root_path')
    
    # Removes the '{{LANG}}' part if present in the root_path
    if root_path and '{{LANG}}' in root_path:
        root_path = root_path.replace('/{{LANG}}', '')
    
    return root_path

@helper
def get_langs():
    """
    Retrieve the list of language priorities from the CKAN configuration.

    This function fetches the 'ckan.locales_offered' configuration setting,
    splits it by spaces if it's a string, and returns the resulting list of language codes.

    Returns:
        list: A list of language codes as strings.
    """
    language_priorities = p.toolkit.config.get('ckan.locales_offered', '')
    if isinstance(language_priorities, str):
        language_priorities = language_priorities.split()
    return language_priorities

@lru_cache(maxsize=4)
@helper
def schemingdcat_get_default_lang():
    """
    Retrieve the default language for the CKAN instance.

    This function checks if the global variable `DEFAULT_LANG` is set. If not,
    it fetches the default language from the CKAN configuration using the 
    'ckan.locale_default' setting. If the setting is not found, it defaults to 'en'.

    Returns:
        str: The default language code.
    """
    global DEFAULT_LANG
    if DEFAULT_LANG is None:
        DEFAULT_LANG = p.toolkit.config.get("ckan.locale_default", "en")
    return DEFAULT_LANG

@helper
def schemingdcat_get_current_lang():
    """
    Returns the current language of the CKAN instance.

    Returns:
        str: The current language of the CKAN instance. If the language cannot be determined, the default language 'en' is returned.
    """
    try:
        return get_lang()
    except TypeError:
        return p.toolkit.config.get("ckan.locale_default", "en")

@helper
def schemingdcat_extract_lang_text(text, current_lang):
    """
    Extracts the text content for a specified language from a string.

    Args:
        text (str): The string to extract the language content from.
            Example: "[#en#]Welcome to the CKAN Open Data Portal.[#es#]Bienvenido al portal de datos abiertos CKAN."
        current_lang (str): The language code to extract the content for.
            Example: "es"

    Returns:
        str: The extracted language content, or the original string if no content is found.
            Example: "Bienvenido al portal de datos abiertos CKAN."

    """

    @lru_cache(maxsize=30)
    def process_language_content(language_label, text):
        """Helper function to process the content for a specific language label.

        Args:
            language_label (str): The language label to process.
            text (str): The text to process.

        Returns:
            str: The text corresponding to the specified language label.

        """
        pattern = re.compile(r'\[#(.*?)#\](.*?)(?=\[#|$)', re.DOTALL)
        matches = pattern.findall(text)

        for lang, content in matches:
            if lang == language_label.replace('[#', '').replace('#]', ''):
                return content.strip()

        return ''

    lang_label = f"[#{current_lang}#]"
    default_lang = schemingdcat_get_default_lang()
    default_lang_label = f"[#{default_lang}#]"

    lang_text = process_language_content(lang_label, text)

    if not lang_text and lang_label != default_lang_label:
        lang_text = process_language_content(default_lang_label, text)

    if not lang_text:
        return text

    return lang_text

@helper
def dataset_display_name(package_or_package_dict):
    """
    Returns the localized value of the dataset name by extracting the correct translation.

    Args:
    - package_or_package_dict: A dictionary containing the package information.

    Returns:
    - The localized value of the dataset name.
    """
    field_name = "title" if "title" in package_or_package_dict else "name"

    return schemingdcat_get_localized_value_from_dict(
        package_or_package_dict, field_name
    )


@helper
def dataset_display_field_value(package_or_package_dict, field_name):
    """
    Extracts the correct translation of the dataset field.

    Args:
        package_or_package_dict (dict): The package or package dictionary to extract the value from.
        field_name (str): The name of the field to extract the value for.

    Returns:
        str: The localized value for the given field name.
    """
    return schemingdcat_get_localized_value_from_dict(
        package_or_package_dict, field_name
    )

@helper
def schemingdcat_get_localized_value_from_dict(
    package_or_package_dict, field_name, default=""
):
    """
    Get the localized value from a dictionary.

    This function tries to get the value of a field in a specific language.
    If the value is not available in the specific language, it tries to get it in the default language.
    If the value is not available in the default language, it tries to get the untranslated value.
    If the untranslated value is not available, it returns a default value.

    Args:
        package_or_package_dict (dict or str): The package or dictionary to get the value from.
            If it's a string, it tries to convert it to a dictionary using json.loads.
        field_name (str): The name of the field to get the value from.
        default (str, optional): The default value to return if the value is not available. Defaults to "".

    Returns:
        str: The localized value, or the default value if the localized value is not available.
    """
    if isinstance(package_or_package_dict, str):
        try:
            package_or_package_dict = json.loads(package_or_package_dict)
        except ValueError:
            return default

    lang_code = schemingdcat_get_current_lang().split("_")[0]
    schemingdcat_get_default_lang()

    translated_field = package_or_package_dict.get(field_name + "_translated", {})
    if isinstance(translated_field, str):
        try:
            translated_field = json.loads(translated_field)
        except ValueError:
            translated_field = {}

    # Check the lang_code, if not check the default_lang, if not check the field without translation
    return translated_field.get(lang_code) or translated_field.get(DEFAULT_LANG) or package_or_package_dict.get(field_name, default)

@helper
def schemingdcat_get_readable_file_size(num, suffix="B"):
    if not num:
        return False
    try:
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            num = float(num)
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, "Y", suffix)
    except ValueError:
        return False

@helper
def schemingdcat_get_group_or_org(id, type="group"):
    """
    Retrieve information about a group or organization in CKAN.

    Args:
        id (str): The ID of the group or organization.
        type (str, optional): The type of the entity to retrieve. Defaults to 'group'.

    Returns:
        dict: A dictionary containing information about the group or organization.
    """
    return logic.get_action(f"{type}_show")({}, {"id": id})

@helper
def schemingdcat_package_list_for_source(source_id):
    '''
    Creates a dataset list with the ones belonging to a particular harvest
    source.

    It calls the package_list snippet and the pager.
    '''
    limit = 20
    page = int(request.args.get('page', 1))
    fq = '+harvest_source_id:"{0}"'.format(source_id)
    search_dict = {
        'fq': fq,
        'rows': limit,
        'sort': 'metadata_modified desc',
        'start': (page - 1) * limit,
        'include_private': True
    }

    context = {'model': model, 'session': model.Session}
    harvest_source = get_harvest_source(source_id)
    owner_org = harvest_source.get('owner_org', '')
    if owner_org:
        user_member_of_orgs = [org['id'] for org
                               in ckan_helpers.organizations_available('read')]
        if (harvest_source and owner_org in user_member_of_orgs):
            context['ignore_capacity_check'] = True

    query = logic.get_action('package_search')(context, search_dict)

    base_url = ckan_helpers.url_for(
        '{0}.read'.format(DATASET_TYPE_NAME),
        id=harvest_source['name']
    )

    def pager_url(q=None, page=None):
        url = base_url
        if page:
            url += '?page={0}'.format(page)
        return url

    pager = ckan_helpers.Page(
        collection=query['results'],
        page=page,
        url=pager_url,
        item_count=query['count'],
        items_per_page=limit
    )
    pager.items = query['results']

    if query['results']:
        out = ckan_helpers.snippet('schemingdcat/snippets/package_list.html', packages=query['results'])
        out += pager.pager()
    else:
        out = ckan_helpers.snippet('snippets/package_list_empty.html')

    return out
@helper
def schemingdcat_package_count_for_source(source_id):
    '''
    Returns the current package count for datasets associated with the given
    source id
    '''
    fq = '+harvest_source_id:"{0}"'.format(source_id)
    search_dict = {'fq': fq, 'include_private': True}
    context = {'model': model, 'session': model.Session}
    result = logic.get_action('package_search')(context, search_dict)
    return result.get('count', 0)

@helper
def schemingdcat_parse_localised_date(date_=None):
    '''Parse a datetime object or timestamp string as a localised date.
    If timestamp is badly formatted, then None is returned.

    :param date_: the date
    :type date_: datetime or date or ISO string format
    :rtype: date
    '''
    if not date_:
        return None
    if isinstance(date_, str):
        try:
            date_ = ckan_helpers.date_str_to_datetime(date_)
        except (TypeError, ValueError):
            return None
    # check we are now a datetime or date
    if isinstance(date_, datetime.datetime):
        date_ = date_.date()
    elif not isinstance(date_, datetime.date):
        return None

    # Format date based on locale
    locale = schemingdcat_get_current_lang()
    if locale == 'es':
        return date_.strftime('%d-%m-%Y')
    else:
        return date_.strftime('%Y-%m-%d')

@lru_cache(maxsize=8)
@helper
def schemingdcat_get_dataset_schema(schema_type="dataset"):
    """
    Retrieves the schema for the dataset instance and caches it using the LRU cache decorator for efficient retrieval.

    Args:
        schema_type (str, optional): The type of schema to retrieve. Defaults to 'dataset'.

    Returns:
        dict: The schema of the dataset instance.
    """
    return logic.get_action("scheming_dataset_schema_show")(
        {}, {"type": schema_type}
    )   

@lru_cache(maxsize=16)
@helper
def schemingdcat_get_cached_schema(dataset_type='dataset'):
    """
    Retrieve the cached schema for a given dataset type.

    Args:
        dataset_type (str, optional): The type of schema to retrieve. Defaults to 'dataset'.

    Returns:
        dict: The schema of the dataset instance.
    """
    if sdct_config.schemas is None:
        sdct_config.schemas = schemingdcat_get_dataset_schema()
    
    return sdct_config.schemas.get(dataset_type, {})

@lru_cache(maxsize=2)
@helper
def schemingdcat_get_dataset_schema_field_names(schema_type="dataset", schema=None):
    """
    Return a list of field names that are in the dataset_fields
    and resource_fields of the schema.

    Args:
        dataset_type (str): The dataset_type.

    Returns:
        list: A list of field names from dataset_fields and resource_fields.
    """
    
    if schema is None:
        schema = schemingdcat_get_dataset_schema(schema_type)
        
    field_names = []

    # Helper function to extract field names
    def extract_field_names(fields):
        return [field['field_name'] for field in fields]

    # Extract field names from dataset_fields
    dataset_fields = schema.get('dataset_fields', [])
    dataset_fields_field_names = extract_field_names(dataset_fields)
    
    # Extract field names from resource_fields
    resource_fields = schema.get('resource_fields', [])
    resource_fields_field_names = extract_field_names(resource_fields)
    
    # Combine results into a list of dictionaries
    field_names.append({'dataset_fields': dataset_fields_field_names})
    field_names.append({'resource_fields': resource_fields_field_names})
    
    return field_names

@lru_cache(maxsize=2)
@helper
def schemingdcat_get_dataset_schema_required_field_names(schema_type="dataset", schema=None):
    """
    Return a list of field names that are required in the dataset_fields
    and resource_fields of the schema.

    Args:
        dataset_type (str): The dataset_type.

    Returns:
        list: A list of required field names from dataset_fields and resource_fields.
    """
    
    if schema is None:
        schema = schemingdcat_get_dataset_schema(schema_type)
    
    required_field_names = []

    # Helper function to extract required field names
    def extract_required_field_names(fields):
        return [field['field_name'] for field in fields if field.get('required', False)]

    # Extract required field names from dataset_fields
    dataset_fields = schema.get('dataset_fields', [])
    required_dataset_fields = extract_required_field_names(dataset_fields)
    
    # Extract required field names from resource_fields
    resource_fields = schema.get('resource_fields', [])
    required_resource_fields = extract_required_field_names(resource_fields)
    
    # Combine results into a list of dictionaries
    required_field_names.append({'dataset_fields': required_dataset_fields})
    required_field_names.append({'resource_fields': required_resource_fields})
    
    return required_field_names

@helper
def schemingdcat_get_schema_form_groups(entity_type=None, object_type=None, schema=None):
    """
    Return a list of schema metadata groups for this form.

    1. return schema['schema_form_groups'] if it is defined
    2. get schema from entity_type + object_type then
       return schema['schema_form_groups'] if they are defined
    """
    if schema and "schema_form_groups" in schema:
        return schema["schema_form_groups"]
    elif entity_type and object_type:
        schema = scheming_get_schema(entity_type, object_type)
        return schema["schema_form_groups"] if schema and "schema_form_groups" in schema else None
    else:
        return None

# Vocabs
@helper
def get_inspire_themes(*args, **kwargs) -> List[Dict[str, str]]:
    log.debug(f"inside get_inspire_themes {args=} {kwargs=}")
    try:
        inspire_themes = p.toolkit.get_action("tag_list")(
            data_dict={"vocabulary_id": sdct_config.SCHEMINGDCAT_INSPIRE_THEMES_VOCAB}
        )
    except p.toolkit.ObjectNotFound:
        inspire_themes = []
    return [{"value": t, "label": t} for t in inspire_themes] 

@helper
def get_ckan_cleaned_name(name):
    """
    Cleans a name by removing accents, special characters, and spaces.

    Args:
        name (str): The name to clean.

    Returns:
        str: The cleaned name.
    """
    MAX_TAG_LENGTH = 100
    MIN_TAG_LENGTH = 2
    # Define a dictionary to map accented characters to their unaccented equivalents except ñ
    accent_map = {
        "á": "a", "à": "a", "ä": "a", "â": "a", "ã": "a",
        "é": "e", "è": "e", "ë": "e", "ê": "e",
        "í": "i", "ì": "i", "ï": "i", "î": "i",
        "ó": "o", "ò": "o", "ö": "o", "ô": "o", "õ": "o",
        "ú": "u", "ù": "u", "ü": "u", "û": "u",
        "ñ": "ñ",
    }

    # Convert the name to lowercase
    name = name.lower()

    # Replace accented and special characters with their unaccented equivalents or -
    name = "".join(accent_map.get(c, c) for c in name)
    name = re.sub(r"[^a-zñ0-9_.-]", "-", name.strip())

    # Truncate the name to MAX_TAG_LENGTH characters
    name = name[:MAX_TAG_LENGTH]

    # If the name is shorter than MIN_TAG_LENGTH, pad it with underscores
    if len(name) < MIN_TAG_LENGTH:
        name = name.ljust(MIN_TAG_LENGTH, '_')

    return name

@helper
def get_featured_datasets(count=1):
    """
    This helper function retrieves a specified number of featured datasets from the CKAN instance. 
    It uses the 'package_search' action of the CKAN logic layer to perform a search with specific parameters.
    
    Parameters:
    count (int): The number of featured datasets to retrieve. Default is 1.

    Returns:
    list: A list of dictionaries, each representing a featured dataset.
    """
    fq = '+featured:true'
    search_dict = {
        'fq': fq, 
        'sort': 'metadata_modified desc',
        'fl': 'id,name,title,notes,state,metadata_modified,type,extras_featured,extras_graphic_overview',
        'rows': count
    }
    context = {'model': model, 'session': model.Session}
    result = logic.get_action('package_search')(context, search_dict)
    
    return result['results']

@helper
def get_spatial_datasets(count=10, return_count=False):
    """
    This helper function retrieves a specified number of featured datasets from the CKAN instance. 
    It uses the 'package_search' action of the CKAN logic layer to perform a search with specific parameters.
    
    Parameters:
    count (int): The number of featured datasets to retrieve. Default is 10.
    return_count (bool): If True, returns the count of featured datasets. If False, returns the detailed information. Default is False.

    Returns:
    int or list: If return_count is True, returns the count of featured datasets. Otherwise, returns a list of dictionaries, each representing a featured dataset.
    """
    fq = '+dcat_type:*inspire*'
    search_dict = {
        'fq': fq, 
        'fl': 'extras_dcat_type',
        'rows': count
    }
    context = {'model': model, 'session': model.Session}
    result = logic.get_action('package_search')(context, search_dict)
    
    if return_count:
        return result['count']
    else:
        return result['results']

@helper
def get_theme_datasets(field='theme'):
    """
    Retrieves all datasets with the specified field efficiently using pagination.
    
    Parameters:
    field (str): The field to search for in the dataset extras. Default is 'theme'.

    Returns:
    list: A list of unique values from the specified field in the featured datasets.
    """
    search_dict = {
        'fl': 'extras_' + field,
        'rows': 100,  # Number of datasets per batch
        'start': 0
    }
    context = {'model': model, 'session': model.Session}
    results = []

    while True:
        result = logic.get_action('package_search')(context, search_dict)
        results.extend(result['results'])
        if len(result['results']) < search_dict['rows']:
            break
        search_dict['start'] += search_dict['rows']

    return results

@helper
def get_unique_themes():
    """
    Retrieves unique themes from the dataset extras field specified by the default package item icon.

    This helper function uses the `get_theme_datasets` function to fetch datasets and then extracts
    unique values from the specified field. The results are cached to improve performance.

    Returns:
        list: A list of unique themes extracted from the specified field in the dataset extras.
    """
    field_name = schemingdcat_get_default_package_item_icon()
    themes = get_theme_datasets(field_name)
    
    # Use a set to store unique values
    unique_values = set()
    for dataset in themes:
        value = dataset.get(field_name)
        if value:
            # Parse the JSON string and add each value to the set
            unique_values.update(json.loads(value))
    
    # Return the unique values as a list
    return list(unique_values)

@lru_cache(maxsize=16)
@helper
def get_header_endpoint_url(endpoint, site_protocol_and_host):
    url_for = ckan_helpers.url_for
    endpoint_type = endpoint['type']
    endpoint_value = endpoint['endpoint']

    if endpoint_type == 'ogc':
        if ckan_helpers.is_url(endpoint_value):
            return ckan_helpers.url_for_static_or_external(endpoint_value)
        else:
            protocol, host = site_protocol_and_host
            return f"{protocol}://{host}/{endpoint_value}"
    elif endpoint_type == 'ckan':
        return url_for('api.action', ver=3, logic_function='package_list', qualified=True)
    elif endpoint_type == 'lod':
        return url_for(endpoint_value, **endpoint['endpoint_data'])
    elif endpoint_type == 'sparql':
        return url_for('/sparql')
    
@helper
def schemingdcat_check_valid_url(url):
    """
    Check if a string is a valid URL.

    Args:
        url (str): The string to check.

    Returns:
        bool: True if the string is a valid URL, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

# schemingdcat form tabs
@helper
def schemingdcat_get_form_tabs():
    """
    """
    return sdct_config.form_tabs

@helper
def schemingdcat_get_form_groups():
    """
    """
    return sdct_config.form_groups

@helper
def schemingdcat_get_dataset_type_form_tabs(dataset_type='dataset'):
    """
    """    
    if sdct_config.form_tabs:
        form_tabs = sdct_config.form_tabs[dataset_type]
    else:
        log.warning('sdct_config.form_tabs is None')
        form_tabs = []
    return form_tabs

@helper
def schemingdcat_get_dataset_type_form_groups(dataset_type='dataset'):
    """
    """
    if sdct_config.form_groups:
        form_groups = sdct_config.form_groups[dataset_type]
    else:
        log.warning('sdct_config.form_groups is None')
        form_groups = []
    return form_groups

@helper
def schemingdcat_form_tabs_allowed():
    """
    Returns a boolean value indicating whether form tabs are allowed in the current configuration.

    Returns:
        bool: True if form tabs are allowed, False otherwise.
    """
    return p.toolkit.config.get('ckanext.schemingdcat.form_tabs_allowed')

@helper
def schemingdcat_get_required_form_groups(schema, tab_type='dataset_fields'):
    required_form_groups = {}
    fields = schema.get(tab_type, {})
    
    for field in fields:
        if field.get('required'):
            form_group_id = field.get('form_group_id')
            if form_group_id:
                required_form_groups[form_group_id] = True
    
    return required_form_groups

@helper
def schemingdcat_form_tabs_grouping(schema, tab_type='dataset_fields', schema_tabs_prop='schema_form_tabs', dataset_type='dataset'):
    """
    Generates a list of dictionaries containing information about form tabs, including their labels and fields.
    Ensures that form_tab names are unique and that each tab has at least one label.

    Args:
        schema (dict): A dictionary containing the schema definition with a key 'schema_form_tabs'.
        tab_type (str): The type of tabs to filter by. Defaults to 'dataset_fields'.
        dataset_type (str): The type of dataset to filter by. Defaults to 'dataset'.

    Returns:
        list: A list of dictionaries with tab information, including labels and fields, filtered by the specified type.
    """
    if sdct_config.form_tabs_grouping is not None and tab_type in sdct_config.form_tabs_grouping:
        return sdct_config.form_tabs_grouping[tab_type]
    else:
        form_groups = {}
        for category in sdct_config.form_groups.values():
            form_groups.update({group['form_group_id']: group for group in category})
                
        tabs = [
            tab for tab in schema.get(schema_tabs_prop, [])
            if tab.get('tab_type') == tab_type
        ]
        
        required_form_groups = schemingdcat_get_required_form_groups(schema, tab_type)
        
        for tab in tabs:
            form_group_ids = tab.get('form_group_id')
            if isinstance(form_group_ids, list):
                tab['form_group_id'] = [form_groups[form_group_id] for form_group_id in form_group_ids if form_group_id in form_groups]
                tab['required_form_group_id'] = [form_group_id for form_group_id in form_group_ids if form_group_id in required_form_groups]
            else:
                if form_group_ids in form_groups:
                    tab['form_group_id'] = form_groups[form_group_ids]
                if form_group_ids in required_form_groups:
                    tab['required_form_group_id'] = form_group_ids
            
        if sdct_config.form_tabs_grouping is None:
            sdct_config.form_tabs_grouping = {}
        
        sdct_config.form_tabs_grouping[tab_type] = tabs
        return tabs

@helper
def schemingdcat_slugify(s):
    """
    Removes all non-alphanumeric characters from the input string.

    Args:
        s (str): The input string to be slugified.

    Returns:
        str: The slugified string with only alphanumeric characters.
    """
    return sdct_config.slugify_pat.sub('', s)

@helper
def schemingdcat_open_data_statistics_enabled():
    """
    Checks if open data statistics are enabled for the portal and themes.

    Retrieves the configuration settings to determine whether open data statistics
    are enabled for the portal and for themes within the Scheming DCAT extension.

    Returns:
        dict: A dictionary with the keys:
            - 'portal' (bool): Indicates if portal-level statistics are enabled.
            - 'themes' (bool): Indicates if theme-level statistics are enabled.
    """
    return {'portal': p.toolkit.config.get('ckanext.schemingdcat.open_data_statistics'), 'themes': p.toolkit.config.get('ckanext.schemingdcat.open_data_statistics_themes')}

@helper
def schemingdcat_get_theme_statistics(theme_field=None, icons_dir=None) -> List[Dict]:
    """
    Retrieve statistics for each unique theme in the provided list.

    Args:
        theme_field (str, optional): The key where the theme data is stored in each dictionary.
        icons_dir (str, optional): Directory where the icons are stored.

    Returns:
        list[dict]: A list of dictionaries containing the count, icon, theme, and label for each unique theme.
    """

    if theme_field is None:
        theme_field = schemingdcat_get_default_package_item_icon()
    try:
        themes = get_theme_datasets(theme_field)
    except Exception as e:
        log.error("Error aggregating theme statistics: %s", e)
        raise

    if icons_dir is None:
        icons_dir = schemingdcat_get_icons_dir(field_name=theme_field)
    
    # Use a defaultdict to store unique themes and their counts
    theme_counts = defaultdict(int)

    # Iterate over the themes and count occurrences
    for theme_dict in themes:
        theme_value = theme_dict.get(theme_field)  # Access 'theme' using the provided field name
        if theme_value:
            try:
                parsed_values = json.loads(theme_value)  # Parse the JSON only once per theme
            except json.JSONDecodeError:
                continue  # Skip if theme_value is not valid JSON
            for val in parsed_values:
                theme_counts[val] += 1

    # Generate the final list of dictionaries
    stats = [
        {
            'count': count,
            'icon': schemingdcat_get_icon(icons_dir=icons_dir, choice_value=theme),
            'value': theme,
            'label': theme.split('/')[-1],  # Use split only once
            'field_name': theme_field,
        }
        for theme, count in theme_counts.items()  # Process items directly without separate for loop
    ]

    return stats

@helper
def schemingdcat_format_number(value):
    """Formats a number with thousands separators using dots.

    Converts the input value to a float and formats it with thousands separators.
    Commas are replaced with dots to match certain localization standards. If the
    input cannot be converted to a float, the original value is returned unchanged.

    Args:
        value (int, float, str): The value to format. This can be an integer, float, or string
            representing a numerical value.

    Returns:
        str or original type: A string representing the formatted number with dots as
        thousands separators. If the input is not a valid number, the original value is returned.

    Examples:
        >>> schemingdcat_format_number(1000)
        '1.000'
        
        >>> schemingdcat_format_number("2500000")
        '2.500.000'
        
        >>> schemingdcat_format_number("invalid")
        'invalid'
    """
    try:
        value = float(value)
        return "{:,.0f}".format(value).replace(",", ".")
    except (ValueError, TypeError):
        return value
    
@helper
def schemingdcat_validate_float(value=None):
    """
    Validates if the value is a float. If the value is a string or an integer, tries to convert it to float.
    If the value is None, assigns a default value of 0.001.
    Returns the float value if valid, otherwise raises a ValueError.

    Args:
        value: The value to be validated.

    Returns:
        float: The validated float value.

    Raises:
        ValueError: If the value cannot be converted to float.
    """
    if value is None:
        return sdct_config.geojson_tolerance
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Cannot convert string '{value}' to float.")
    raise ValueError(f"Value '{value}' is not a float, integer, or a string that can be converted to float.")

# Bibliographics
@lru_cache(maxsize=24)
@helper
def schemingdcat_is_bibliographic_dcat_type(dcat_type):
    """
    Check if a dcat_type corresponds to a bibliographic element.

    Args:
        dcat_type (str): The dcat_type to check.

    Returns:
        bool: True if the dcat_type is a bibliographic element, False otherwise.
    """
    return 'marcgt' in dcat_type or dcat_type == 'http://purl.org/dc/dcmitype/Text'

@helper
def schemingdcat_get_doi_from_identifier(pkg_identifier):
    """
    Retrieves the DOI of a dataset from an identifier value.

    Args:
        pkg_identifier (str): The identifier string of the dataset.

    Returns:
        str: The DOI if found, None otherwise.
    """
    doi_pattern = re.compile(r'doi:(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', re.IGNORECASE)
    match = doi_pattern.search(pkg_identifier)
    
    if match:
        return match.group(1)
    return None

@helper
def schemingdcat_get_current_datetime():
    """
    Devuelve la fecha y hora actual.

    Returns:
        datetime: La fecha y hora actual.
    """
    return datetime.datetime.now()

@helper
def schemingdcat_get_doi_from_alternate_identifier(pkg_identifier):
    """
    Gets the DOI of a dataset from the alternate_identifier field.

    Args:
        pkg_identifier (str): The dataset dictionary.

    Returns:
        str: The DOI if found, None otherwise.
    """
    # Remove all whitespace characters and trim leading/trailing spaces
    cleaned_identifier = pkg_identifier.strip().replace(" ", "")
    
    doi_pattern = re.compile(r'doi:(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', re.IGNORECASE)
    match = doi_pattern.search(cleaned_identifier)
    
    if match:
        return match.group(1)
    return None

@helper
def schemingdcat_get_isbn_from_alternate_identifier(pkg_identifier):
    """
    Extracts and validates the ISBN from 'pkg_identifier' after removing the 'isbn:' prefix if present.
    An ISBN consists of five sequential parts:
    1. Prefix (978 or 979, 3 digits)
    2. Registration group (1 to 5 digits)
    3. Registrant (1 to 7 characters)
    4. Publication element (up to 6 digits)
    5. Checksum digit (1 digit)

    Args:
        pkg_identifier (str): The package identifier that may include the 'isbn:' prefix.

    Returns:
        str or None: The extracted ISBN if valid, otherwise None.
    """
    # Remove all whitespace characters and trim leading/trailing spaces
    cleaned_identifier = pkg_identifier.strip().replace(" ", "")
    
    # Remove the 'isbn:' prefix if present
    if cleaned_identifier.lower().startswith('isbn:'):
        cleaned_identifier = cleaned_identifier[5:]
    
    isbn_pattern = re.compile(r'^(978|979)-\d{1,5}-\d{1,7}-\d{1,6}-\d$', re.IGNORECASE)
    match = isbn_pattern.fullmatch(cleaned_identifier)
    
    if match:
        return match.group(0)
    return None


# Publisher permissions
@helper
def schemingdcat_user_is_org_member(
    org_id: str, user=None, role: typing.Optional[str] = "admin"
) -> bool:
    """
    Check if a user has a specific role in the input organization.

    This function checks if the given user has the specified role in the organization
    identified by `org_id`. By default, it checks if the user has the "admin" role.

    Args:
        org_id (str): The ID of the organization.
        user: The user object to check. If None, the function will return False.
        role (str, optional): The role to check for. Defaults to "admin".

    Returns:
        bool: True if the user has the specified role in the organization, False otherwise.

    Example:
        >>> schemingdcat_user_is_org_member("org_id", user, "editor")
        True
    """
    if not user or not hasattr(user, 'id'):
        return False

    result = False
    if org_id is not None:
        member_list_action = p.toolkit.get_action("schemingdcat_member_list")
        org_members = member_list_action(
            data_dict={"id": org_id, "object_type": "user"}
        )
        for member_id, _, member_role in org_members:
            if user.id == member_id:
                #log.debug('member_role: %s and role: %s', member_role, role)
                
                # Check direct match
                if role is None or member_role.lower() == role.lower():
                    result = True
                break
    return result

@lru_cache(maxsize=1)
@helper
def schemingdcat_get_catalog_publisher_info():
    return sdct_config.catalog_publisher_info

@helper
def schemingdcat_extract_base_url(url):
    """
    Extract the base URL without query parameters or fragments.
    Preserves the path including file extensions like .aspx, .php, etc.
    
    Args:
        url (str): The full URL
        
    Returns:
        str: The base URL without query parameters
        
    Examples:
        >>> _extract_base_url("https://wms.mapama.es/sig/Agua/ZonasProtPotablesPoligonos/2027/wms.aspx?service=WMS")
        'https://wms.mapama.es/sig/Agua/ZonasProtPotablesPoligonos/2027/wms.aspx'
        
        >>> _extract_base_url("https://www.mapa.gob.es/app/descargas/descargafichero.aspx?f=ComarcasAgrarias.rar")
        'https://www.mapa.gob.es/app/descargas/descargafichero.aspx'
    """
    try:        
        # Parse the URL
        parsed = urlparse(url)
        
        # Reconstruct the URL without query parameters and fragments
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            '',  # params
            '',  # query
            ''   # fragment
        ))
        
        return clean_url
        
    except Exception as e:
        return url