import ckan.logic as logic
import ckan.plugins as p
import logging
import uuid
import os
import inspect
import json
import hashlib
from threading import Lock
import warnings
from functools import wraps
from urllib.parse import urljoin

import yaml
from yaml.loader import SafeLoader
from pathlib import Path

# Try to import from new location first, fall back to old location
try:
    from ckanext.dcat.helpers import get_endpoint
except ImportError:
    from ckanext.dcat.utils import get_endpoint

from ckanext.dcat.utils import CONTENT_TYPES
from ckanext.scheming.helpers import (
    scheming_dataset_schemas,
)

from ckanext.schemingdcat import config as sdct_config

try:
    from paste.reloader import watch_file
except ImportError:
    watch_file = None

log = logging.getLogger(__name__)


_facets_dict = None
_public_dirs = None
_dirs_hash = set()
_files_hash = set()

_facets_dict_lock = Lock()
_public_dirs_lock = Lock()

def deprecated(func):
    """This is a decorator which can be used to mark functions as deprecated.
    It will result in a warning being emitted when the function is used."""
    @wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn(f"Call to deprecated function {func.__name__}. This function will be removed in future versions.",
                      category=DeprecationWarning, stacklevel=2)
        return func(*args, **kwargs)
    return new_func

def get_facets_dict():
    """Get the labels for all fields defined in the scheming file.

    Returns:
        dict: A dictionary containing the labels for all fields defined in the scheming file.
    """
    global _facets_dict
    if not _facets_dict:
        with _facets_dict_lock:
            if not _facets_dict:
                _facets_dict = {}

                schema = logic.get_action('scheming_dataset_schema_show')(
                    {},
                    {'type': 'dataset'}
                    )

                for item in schema['dataset_fields']:
                    _facets_dict[item['field_name']] = item['label']

                for item in schema['resource_fields']:
                    _facets_dict[item['field_name']] = item['label']

    #log.debug('_facets_dict: %s', _facets_dict)

    return _facets_dict

def normalize_paths(paths):
    """Normalize a list of paths to remove redundancies like '..'.

    Args:
        paths (list): List of paths to normalize.

    Returns:
        list: List of normalized paths.
    """
    return [os.path.normpath(path) for path in paths]

def get_public_dirs():
    """Get the list of public directories specified in the configuration file.

    Returns:
        list: A list of public directories specified in the configuration file.
    """
    global _public_dirs

    if not _public_dirs:
        with _public_dirs_lock:
            if not _public_dirs:
                # CKAN 2.10 workaround
                _public_dirs = p.toolkit.config.get('plugin_public_paths', '')

                # Add extra_template_paths if it exists
                extra_template_paths = p.toolkit.config.get('extra_template_paths', '')
                if extra_template_paths:
                    _public_dirs.extend(extra_template_paths)

    return _public_dirs

def public_path_exists(path, check_func, cache):
    """Check if a path exists in the public directories specified in the configuration file.

    Args:
        path (str): The path to check.
        check_func (function): The function to use for checking (os.path.isfile or os.path.isdir).
        cache (set): The cache to use for storing path hashes.

    Returns:
        bool: True if the path exists in one of the public directories, False otherwise.
    """
    path_hash = hashlib.sha512(path.encode('utf-8')).hexdigest()

    if path_hash in cache:
        return True

    public_dirs = normalize_paths(get_public_dirs())
    if any(check_func(os.path.join(public_dir, path)) for public_dir in public_dirs):
        cache.add(path_hash)
        return True


    return False

def public_file_exists(path):
    """Check if a file exists in the public directories specified in the configuration file.

    Args:
        path (str): The path of the file to check.

    Returns:
        bool: True if the file exists in one of the public directories, False otherwise.
    """
    return public_path_exists(path, os.path.isfile, _files_hash)

def public_dir_exists(path):
    """Check if a directory exists in the public directories specified in the configuration file.

    Args:
        path (str): The path of the directory to check.

    Returns:
        bool: True if the directory exists in one of the public directories, False otherwise.
    """
    return public_path_exists(path, os.path.isdir, _dirs_hash)

def init_config():
    sdct_config.linkeddata_links = _load_yaml('linkeddata_links.yaml')
    sdct_config.geometadata_links = _load_yaml('geometadata_links.yaml')
    sdct_config.endpoints = _load_yaml(p.toolkit.config.get('ckanext.schemingdcat.endpoints_yaml'))
    
    # Get publisher type and validate it has correct prefix
    default_publisher_type = "http://purl.org/adms/publishertype/NonProfitOrganisation"
    publisher_type = p.toolkit.config.get('ckanext.schemingdcat.dcat_ap.publisher.type')
    
    # Check prefix and set default if needed
    if not (publisher_type and "http://purl.org/adms/publishertype/" in publisher_type):
        log.warning('Publisher type does not contain the required prefix, using default: %s', default_publisher_type)
        publisher_type = default_publisher_type
    
    sdct_config.catalog_publisher_info = {
        'name': p.toolkit.config.get('ckanext.schemingdcat.dcat_ap.publisher.name'),
        'email': p.toolkit.config.get('ckanext.schemingdcat.dcat_ap.publisher.email'),
        'identifier': p.toolkit.config.get('ckanext.schemingdcat.dcat_ap.publisher.identifier'),
        'type': publisher_type,
        'url': p.toolkit.config.get('ckanext.schemingdcat.dcat_ap.publisher.url')
    }
    
    # Cache scheming schemas of local instance
    sdct_config.schemas = _get_schemas()
    sdct_config.form_tabs = set_schema_form_tabs()
    sdct_config.form_groups = set_schema_form_groups()
    
def construct_full_url(url, protocol, host, root_path=''):
    """
    Constructs a full URL from a relative URL.

    Args:
        url (str): The URL to process.
        protocol (str): The protocol (http or https).
        host (str): The CKAN host.
        root_path (str): The root path of CKAN.

    Returns:
        str: The full URL.
    """
    if not url.startswith(('http://', 'https://')):
        if root_path:
            base_url = f"{protocol}://{host}/{root_path.strip('/')}"
        else:
            base_url = f"{protocol}://{host}"
        url = urljoin(base_url, url.lstrip('/'))
    return url

def is_yaml(file):
    """Check if a file has a YAML extension.

    Args:
        file (str): The file name or path.

    Returns:
        bool: True if the file has a .yaml or .yml extension, False otherwise.
    """
    return file.lower().endswith(('.yaml', '.yml'))

def _load_yaml(file):
    """Load a YAML file, either from a module path or a default directory.

    Args:
        file (str): The name of the YAML file to load. Can be a module path like "module:file.yaml".

    Returns:
        dict: A dictionary containing the data from the YAML file, or an empty dictionary if the file is invalid or cannot be loaded.
    """
    if not is_yaml(file):
        log.error("The file {0} is not a valid YAML file".format(file))
        return {}

    yaml_data = _load_yaml_module_path(file)
    if not yaml_data:
        yaml_data = _load_default_yaml(file)
    return yaml_data

def _load_yaml_module_path(file):
    """Load a YAML file from a module path.

    Given a path like "module:file.yaml", find the file relative to the import path of the module.

    Args:
        file (str): The module path of the YAML file.

    Returns:
        dict or None: A dictionary containing the data from the YAML file, or None if the module cannot be imported or the file cannot be loaded.
    """
    
    if ':' not in file:
        return None

    module, file_name = file.split(':', 1)
    try:
        m = __import__(module, fromlist=[''])
    except ImportError:
        log.error("Module {0} could not be imported".format(module))
        return None

    return _load_yaml_file(os.path.join(os.path.dirname(inspect.getfile(m)), file_name))

def _load_default_yaml(file):
    """Load a YAML file from the 'codelists' directory of the schemingdcat extension.

    Args:
        file (str): The name of the YAML file to load.

    Returns:
        dict: A dictionary containing the data from the YAML file, or an empty dictionary if the file cannot be loaded.
    """
    source_path = Path(__file__).resolve(True)
    return _load_yaml_file(source_path.parent.joinpath('codelists', file))

def _load_yaml_file(path):
    """Load a YAML file from a given path.

    Args:
        path (str): The file path of the YAML file.

    Returns:
        dict: A dictionary containing the data from the YAML file, or an empty dictionary if the file cannot be loaded.
    """
    yaml_data = {}
    try:
        if os.path.exists(path):
            if watch_file:
                watch_file(path)
            with open(path, 'r') as f:
                yaml_data = yaml.load(f, Loader=SafeLoader)
        else:
            log.error("The file {0} does not exist".format(path))
    except Exception as e:
        log.error("Could not read configuration from {0}: {1}".format(path, e))
    return yaml_data

def get_linked_data(id):
    """Get linked data for a given identifier.

    Args:
        id (str): The identifier to get linked data for.

    Returns:
        list: A list of dictionaries containing linked data for the identifier.
    """
    if p.toolkit.config.get("debug", False):
        linkeddata_links = _load_yaml('linkeddata_links.yaml')
    else:
        linkeddata_links = sdct_config.linkeddata_links

    data=[]
    for name in CONTENT_TYPES:
        data.append({
            'name': name,
            'display_name': linkeddata_links.get(name,{}).get('display_name',CONTENT_TYPES[name]),
            'image_display_url': linkeddata_links.get(name,{}).get('image_display_url', None),
            'description': linkeddata_links.get(name,{}).get('description','Formats '+ CONTENT_TYPES[name]),
            'description_url': linkeddata_links.get(name,{}).get('description_url', None),
            'endpoint_data':{
                '_id': id,
                '_format': name,
                }
        })

    return data

def get_geospatial_metadata():
    """Get geospatial metadata for CSW formats.

    Returns:
        list: A list of dictionaries containing geospatial metadata for CSW formats.
    """
    csw_uri = schemingdcat_get_geospatial_endpoint("dataset")
    
    if p.toolkit.config.get("debug", False):
        geometadata_links = _load_yaml('geometadata_links.yaml')
    else:
        geometadata_links = sdct_config.geometadata_links
    data=[]
    for item in geometadata_links.get('csw_formats',{}):
        data.append({
            'name': item['name'],
            'display_name': item['display_name'],
            'image_display_url': item['image_display_url'],
            'description': item['description'],
            'description_url': item['description_url'],
            "url": csw_uri.format(
                output_format=item["output_format"],
                version=item["version"],
                element_set_name=item["element_set_name"],
                output_schema=item["output_schema"],
                id="{id}",
            ),
        })

    return data

def parse_json(value, default_value=None):
    """
    Parses a JSON string and returns the resulting object.
    If the input value is not a valid JSON string, returns the default value.
    If the default value is not provided, returns the input value.

    Args:
        value (str): The JSON string to parse.
        default_value (any, optional): The default value to return if the input value is not a valid JSON string.
            Defaults to None.

    Returns:
        any: The parsed JSON object, or the default value if the input value is not a valid JSON string.
    """
    try:
        return json.loads(value)
    except (ValueError, TypeError, AttributeError):
        if default_value is not None:
            return default_value

        # The json may already have been parsed and we have the value for the
        # language already.
        if isinstance(value, int):
            # If the value is a number, it has been converted into an int - but
            # we want a string here.
            return str(value)
        return value

def _get_schemas():
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
    
def set_schema_form_tabs():
    """
    Sets the schema form tabs for each dataset type in the `sdct_config.schemas`.

    This function iterates over the schemas defined in `sdct_config.schemas` and sets the corresponding
    form tabs in `sdct_config.form_tabs`. If a schema does not have `schema_form_tabs`, it sets the form tab to None.
    Logs warnings and errors as appropriate.

    Raises:
        KeyError: If there is an issue accessing the schema form tabs.
    """
    if not sdct_config.schemas:
        log.warning('sdct_config.schemas is empty, no local scheming.dataset_schemas loaded.')
        return

    form_tabs = {}

    for dataset_type, schema in sdct_config.schemas.items():
        try:
            form_tabs[dataset_type] = schema.get('schema_form_tabs', None)
        except p.toolkit.ObjectNotFound:
            pass
        except KeyError as e:
            log.error('KeyError encountered while setting schema form tabs for dataset_type: %s, error: %s', dataset_type, e)
            
    return form_tabs     

def set_schema_form_groups():
    """
    Sets the schema form groups for each dataset type in the `sdct_config.schemas`.

    This function iterates over the schemas defined in `sdct_config.schemas` and sets the corresponding
    form tabs in `sdct_config.form_groups`. If a schema does not have `schema_form_groups`, it sets the form tab to None.
    Logs warnings and errors as appropriate.

    Raises:
        KeyError: If there is an issue accessing the schema form tabs.
    """
    if not sdct_config.schemas:
        log.warning('sdct_config.schemas is empty, no local scheming.dataset_schemas loaded.')
        return

    form_groups = {}

    for dataset_type, schema in sdct_config.schemas.items():
        try:
            form_groups[dataset_type] = schema.get('schema_form_groups', None)
        except p.toolkit.ObjectNotFound:
            pass
        except KeyError as e:
            log.error('KeyError encountered while setting schema form tabs for dataset_type: %s, error: %s', dataset_type, e)
            
    return form_groups     

def schemingdcat_catalog_endpoints():
    """Get the catalog endpoints.

    Returns:
        list: A list of dictionaries containing linked data for the identifier.
    """    
    csw_uri = schemingdcat_get_geospatial_endpoint("catalog")

    return [
        {
            "name": item["name"],
            "display_name": item["display_name"],
            "format": item["format"],
            "image_display_url": item["image_display_url"],
            "endpoint_icon": item["endpoint_icon"],
            "fa_icon": item["fa_icon"],
            "description": item["description"],
            "type": item["type"],
            "profile": item["profile"],
            "profile_id": item["profile_id"],
            "profile_label": item["profile_label"],
            "profile_label_order": item["profile_label_order"],
            "profile_version": tuple(map(int, str(item["version"]).split("."))),
            "profile_info_url": item["profile_info_url"],
            "endpoint": get_endpoint("catalog")
            if item.get("type").lower() == "lod"
            else csw_uri.format(version=item["version"])
            if item.get("type").lower() == "ogc"
            else None,
            "endpoint_data": {
                "_format": item["format"],
                "_external": True,
                "profiles": item["profile"],
            },
        }
        for item in sdct_config.endpoints["catalog_endpoints"]
    ]

def schemingdcat_get_geospatial_metadata():
    """Get geospatial metadata for CSW formats.

    Returns:
        list: A list of dictionaries containing geospatial metadata for CSW formats.
    """
    csw_uri = schemingdcat_get_geospatial_endpoint("dataset")

    return [
        {
            "name": item["name"],
            "display_name": item["display_name"],
            "format": item["format"],
            "image_display_url": item["image_display_url"],
            "endpoint_icon": item["endpoint_icon"],
            "description": item["description"],
            "description_url": item["description_url"],
            "url": csw_uri.format(
                output_format=item["output_format"],
                version=item["version"],
                element_set_name=item["element_set_name"],
                output_schema=item["output_schema"],
                id="{id}",
            ),
        }
        for item in sdct_config.geometadata_links["csw_formats"]
    ]

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

# SchemingDCATSQLHarvester utils
# Aux defs for SchemingDCATSQLHarvester import_stage validation
def normalize_temporal_dates(package_dict):
  """
  Normalizes 'temporal_start' and 'temporal_end' in a dictionary to YYYY-MM-DD format.

  Modifies 'temporal_start' and 'temporal_end' in `package_dict` to represent the first and last day of the year(s) specified. 
  Input can be a comma-separated string or a list of years.

  Args:
    package_dict (dict): Dictionary with 'temporal_start' and/or 'temporal_end' keys.

  Returns:
    None: Modifies `package_dict` in-place.
  """
  # Convert to standard date string assuming the first or last day of the selected year
  for key in ['temporal_start', 'temporal_end']:
    if key in package_dict:
      # Convert the value to a list of years if it's a string
      years = [int(year) for year in package_dict[key].split(',')] if isinstance(package_dict[key], str) else package_dict[key]
      
      # Select the appropriate year
      selected_year = min(years) if key == 'temporal_start' else max(years)
      
      # Convert to standard date string
      date_str = f"{selected_year}-01-01" if key == 'temporal_start' else f"{selected_year}-12-31"
      package_dict[key] = date_str
      
  return package_dict
      
def normalize_reference_system(package_dict):
  """
  Simplifies the normalization process by taking the SRID value as text and keeping everything to the left of the decimal point.

  Args:
    value (str): The SRID value as a string, which may contain decimals.

  Returns:
    str: The EPSG URI corresponding to the simplified SRID value.
  """ 
  try: 
    package_dict['reference_system'] = sdct_config.epsg_uri_template.format(srid=package_dict['reference_system'].split('.')[0] )
    return package_dict
    
  except Exception as e:
    raise ValueError('SRID value is not a valid number: %s', package_dict['reference_system']) from e


def normalize_resources(package_dict):
    """Filters out resources without a non-empty URL from the package dictionary.

    This function iterates over the resources in the given package dictionary. It keeps only those resources that have a non-empty URL field. The filtered list of resources is then reassigned back to the package dictionary.

    Args:
        package_dict (dict): A dictionary representing the package, which contains a list of resources.

    """
    # Filter resources that have a non-empty URL
    filtered_resources = [resource for resource in package_dict.get("resources", []) if resource.get('url')]
    
    # Reassign the filtered list of resources back to the package_dict
    package_dict["resources"] = filtered_resources
    
    return package_dict

# Specific SQL clauses
def sql_clauses(schema, table, column, alias):
  """
  Generates a SQL expression for GeoJSON data, spatial reference system, or other data with conditional logic based on length or alias.

  This function constructs a SQL expression to select data from a specified column. For GeoJSON data, if the data length exceeds a predefined limit set in `ckanext.schemingdcat.postgres.geojson_chars_limit`, the expression returns NULL to avoid performance issues with large GeoJSON objects. Otherwise, it returns the GeoJSON data. For geographic columns, it applies a transformation to the EPSG:4326 coordinate system and simplifies the geometry based on a tolerance value defined in `postgres.geojson_tolerance`. If the alias is 'reference_system', it returns the SRID of the geometry.

  Parameters:
  - schema (str): The database schema name.
  - table (str): The table name where the column is located.
  - column (str): The column name containing GeoJSON data or geometry.
  - alias (str): The alias to use for the resulting column in the SQL query.

  Returns:
  - str: A SQL expression as a string.
  """
  postgres_geojson_chars_limit = p.toolkit.config.get('ckanext.schemingdcat.postgres.geojson_chars_limit')
  postgres_geojson_tolerance = p.toolkit.config.get('ckanext.schemingdcat.postgres.geojson_tolerance')
  
  if alias == 'spatial':
    # NULL if SRID=0
    return f"CASE WHEN ST_SRID({schema}.{table}.{column}) = 0 THEN NULL ELSE ST_AsGeoJSON(ST_Transform(ST_Envelope({schema}.{table}.{column}), 4326), 2) END AS {alias}"

  elif alias == 'spatial_simple':
    # NULL if SRID=0
    return f"CASE WHEN ST_SRID({schema}.{table}.{column}) = 0 THEN NULL ELSE CASE WHEN LENGTH(ST_AsGeoJSON(ST_Simplify(ST_Transform({schema}.{table}.{column}, 4326), {postgres_geojson_tolerance}), 2)) <= {postgres_geojson_chars_limit} THEN ST_AsGeoJSON(ST_Simplify(ST_Transform({schema}.{table}.{column}, 4326), {postgres_geojson_tolerance}), 2) ELSE NULL END END AS {alias}"

  elif alias == 'reference_system':
    return f"ST_SRID({schema}.{table}.{column}) AS {alias}"

  else:
    return f"{schema}.{table}.{column} AS {alias}"

def remove_private_keys(data, private_keys=None):
    """
    Removes private keys from a dictionary.

    Args:
        data (dict): The dictionary from which private keys will be removed.
        private_keys (list, optional): A list of private keys to remove. If not provided, uses DEFAULT_PRIVATE_KEYS.

    Returns:
        dict: The dictionary without the private keys.
    """
    if private_keys is None:
        private_keys = p.toolkit.config.get('ckanext.schemingdcat.api.private_fields')

    #log.debug('private_keys: %s', private_keys)
    for key in private_keys:
        if key in data:
            del data[key]
    #log.debug('Processed data: %s', data)
    return data

def dataservice_uri(dataservice_dict, catalog_uri):
    '''
    Returns an URI for the dataservice

    This will be used to uniquely reference the dataset on the RDF
    serializations.

    The value will be the first found of:

        1. The value of the `uri` field
        2. The value of an extra with key `uri`
        3. `catalog_uri` + '/dataservice/' + `id` field

    Check the documentation for `catalog_uri()` for the recommended ways of
    setting it.

    Returns a string with the dataset URI.
    '''

    uri = dataservice_dict.get('uri')
    if not uri:
        for extra in dataservice_dict.get('extras', []):
            if extra['key'] == 'uri' and extra['value'] != 'None':
                uri = extra['value']
                break
    if not uri and dataservice_dict.get('id'):
        uri = '{0}/dataservice/{1}'.format(catalog_uri.rstrip('/'),
                                       dataservice_dict['id'])
    if not uri:
        uri = '{0}/dataservice/{1}'.format(catalog_uri.rstrip('/'),
                                       str(uuid.uuid4()))
        log.warning('Using a random id for dataset URI')

    return uri