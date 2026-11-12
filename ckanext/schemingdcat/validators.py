import json
import re
import six
import mimetypes
from shapely.geometry import shape, Polygon
from functools import lru_cache

import ckanext.scheming.helpers as sh
import ckanext.schemingdcat.helpers as helpers
from ckan import plugins as p
import ckan.logic as logic
from ckan.lib import helpers as ckan_helpers
from urllib.parse import urlparse
from ckantoolkit import (
    config,
    get_validator,
    UnknownValidator,
    missing,
    Invalid,
    StopOnError,
    _,
    unicode_safe,
)

import datetime

import logging
from wsgiref.validate import validator
from ckanext.fluent.helpers import (
    fluent_form_languages, fluent_alternate_languages)

from ckanext.fluent.validators import (
    BCP_47_LANGUAGE, fluent_text_output, scheming_language_text, LANG_SUFFIX)

from ckanext.schemingdcat.utils import parse_json
from ckanext.schemingdcat.config import (
    OGC2CKAN_HARVESTER_MD_CONFIG,
    mimetype_base_uri,
    DCAT_AP_HVD_CATEGORY_LEGISLATION,
    TAGS_NORMALIZE_PATTERN,
    CONTACT_PUBLISHER_FALLBACK
)

log = logging.getLogger(__name__)

all_validators = {}

FORM_EXTRAS = ('__extras',)
OPENAPI_REQUIRED_KEYS = ['url', 'name', 'title', 'description']

def validator(fn):
    """
    collect validator functions into ckanext.schemingdcat.all_validators dict
    """
    all_validators[fn.__name__] = fn
    return fn

def scheming_validator(fn):
    """
    Decorate a validator that needs to have the scheming fields
    passed with this function. When generating navl validator lists
    the function decorated will be called passing the field
    and complete schema to produce the actual validator for each field.
    """
    fn.is_a_scheming_validator = True
    return fn

@scheming_validator
@validator
def schemingdcat_multiple_choice(field, schema):
    """
    Accept zero or more values from a list of choices and convert
    to a json list for storage. Also act like scheming_required to check for at least one non-empty string when required is true:
    1. a list of strings, e.g.
       ["choice-a", "choice-b"]
    2. a single string for single item selection in form submissions:
       "choice-a"
    """
    static_choice_values = None
    if 'choices' in field:
        static_choice_order = [c['value'] for c in field['choices']]
        static_choice_values = set(static_choice_order)
    def validator(key, data, errors, context):
        # if there was an error before calling our validator
        # don't bother with our validation
        if errors[key]:
            return

        value = data[key]
        # 1. single string to List or 2. List
        if value is not missing:
            if isinstance(value, six.string_types):
                if "[" not in value:
                    value = value.split(",")
                else:
                    value = json.loads(value)
            if not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                raise StopOnError
        else:
            value = []
        choice_values = static_choice_values
        if not choice_values:
            choice_order = [
                choice['value']
                for choice in sh.scheming_field_choices(field)
            ]
            choice_values = set(choice_order)
        selected = set()
        for element in value:
            if element in choice_values:
                selected.add(element)
                continue
            errors[key].append(_('unexpected choice "%s"') % element)

        if not errors[key]:
            # Return as a JSON string list of values
            data[key] = json.dumps([v for v in
                (static_choice_order if static_choice_values else choice_order)
                if v in selected], ensure_ascii=False)

            if field.get('required') and not selected:
                errors[key].append(_('Select at least one'))
    return validator

@validator
def schemingdcat_valid_json_object(value, context):
    """Store a JSON object as a serialized JSON string
    It accepts two types of inputs:
        1. A valid serialized JSON string (it must be an object or a list)
        2. An object that can be serialized to JSON
    Returns a parsing JSON string 
    """
    if not value:
        return
    elif isinstance(value, six.string_types):
        try:
            loaded = json.loads(value)
            if not isinstance(loaded, dict):
                raise Invalid(
                    _('Unsupported value for JSON field: {}').format(value)
                )

            return json.dumps(loaded, ensure_ascii=False)
        except (ValueError, TypeError) as e:
            raise Invalid(_('Invalid JSON string: {}').format(e))

    elif isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (ValueError, TypeError) as e:
            raise Invalid(_('Invalid JSON object: {}').format(e))
    else:
        raise Invalid(
            _('Unsupported type for JSON field: {}').format(type(value))
        )


@scheming_validator
@validator
def schemingdcat_multiple_text(field, schema):
    """
    Accept repeating text input in the following forms and convert to a json list for storage.
    1. a list of strings, e.g.
       ["Person One", "Person Two"]
    2. a single string value to allow single text fields to be
       migrated to repeating text
       "Person One"
    """

    def _scheming_multiple_text(key, data, errors, context):
        # just in case there was an error before our validator,
        # bail out here because our errors won't be useful
        if errors[key]:
            return

        value = data[key]
        # 1. single string to List or 2. List
        if value is not missing:
            if isinstance(value, six.string_types):
                if "[" not in value:
                    value = value.split(",")
                else:
                    value = json.loads(value)
            if not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                raise StopOnError
            out = []
            for element in value:
                if not element:
                    continue
                if not isinstance(element, six.string_types):
                    errors[key].append(_('invalid type for repeating text: %r')
                                       % element)
                    continue
                if isinstance(element, six.binary_type):
                    try:
                        element = element.decode('utf-8')
                        element = element.strip()
                    except UnicodeDecodeError:
                        errors[key]. append(_('invalid encoding for "%s" value')
                                            % element)
                        continue

                # Avoid errors
                if '"' in element:
                    element=element.replace('"', '\"')
                if ckan_helpers.is_url(element):
                    element=element.replace(' ', '')
                out.append(element)

            if errors[key]:
                raise StopOnError

            # Return as a JSON string list of values
            if not errors[key]:
                data[key] = json.dumps([v for v in out], ensure_ascii=False)

        if (data[key] is missing or data[key] == '[]') and field.get('required'):
            errors[key].append(_('Missing value'))
            raise StopOnError
    return _scheming_multiple_text


@scheming_validator
@validator
def schemingdcat_valid_url(field, schema):
    """Validates a URL field.

    This validator checks if the value of the field is a string and starts with 'http'. If the value is not a string or does not start with 'http', it adds an error message to the errors dictionary.

    Args:
        field (dict): The field to validate.
            A dictionary containing information about the field to be validated.
        schema (dict): The schema for the field.
            A dictionary containing the schema for the field to be validated.

    Returns:
        function: A validation function that can be used to validate the field.

    """
    def validator(key, data, errors, context):
        value = data[key].strip()
        
        if value is missing or value is None or value == '':
            data[key] = value
            return validator
        elif not isinstance(value, six.string_types):
            errors[key].append(_('URL must be a string'))
        elif not value.startswith('http'):
            errors[key].append(_('Please provide a valid URL'))
            
        data[key] = value

    return validator

@validator
def schemingdcat_clean_identifier(value: str) -> str:
    """
    Cleans a value by removing spaces at the beginning and end of the string and replacing spaces between letters with underscores.
    
    Args:
    - value: A string representing the value.
    
    Returns:
    - The cleaned value string.
    """
    if not value.startswith('http'):
        value = value.strip().replace(' ', '-').strip()
    
    return value

@scheming_validator
@validator
def name_identifier_validator(field, schema):
    """Validates and normalizes a name field.

    This validator checks if the value of the field is a URL and, if so, extracts the last part of the URL as the name. If the value is not a URL but starts with 'http', it extracts the last part of the string after splitting it by '-' characters.

    Args:
        field (dict): The field to validate.
        schema (dict): The schema for the field.
    """
    def validator(key, data, errors, context):        
        value = data[key]
                
        if value.startswith('http'):
            data[key] = value.split('-')[-1].strip()
        elif check_url(value):
            data[key] = value.split('/')[-1].strip()

    return validator

# ckanext-fluent
@scheming_validator
@validator
def schemingdcat_translated_output(field, schema):
    """
    Output validator that returns a value for a core field using a multilingual dict.
    
    Args:
    - field: A dictionary containing the field information.
    - schema: A dictionary containing the schema information.
    
    Returns:
    - A validator function that returns a value for a core field using a multilingual dict.
    """
    assert field['field_name'].endswith(LANG_SUFFIX), 'Output validator "fluent_core_translated" must only used on a field that ends with "_translated"'

    required_langs = schema.get('required_language', field.get('required_language'))
    if required_langs and not isinstance(required_langs, list):
        required_langs = [required_langs]
    
    lang = required_langs[0] if required_langs else config.get('ckan.locale_default', 'en')

    def validator(key, data, errors, context):
        """
        Return a value for a core field using a multilingual dict.
        """
        data[key] = fluent_text_output(data[key])

        k = key[-1]
        new_key = key[:-1] + (k[:-len(LANG_SUFFIX)],)

        if new_key in data:
            data[new_key] = scheming_language_text(data[key], lang)

    return validator


@scheming_validator
@validator
def schemingdcat_fluent_core_translated_output(field, schema):
    """
    Output validator that returns a value for a core field using a multilingual dict.
    
    Args:
    - field: A dictionary containing the field information.
    - schema: A dictionary containing the schema information.
    
    Returns:
    - A validator function that returns a value for a core field using a multilingual dict.
    """
    assert field['field_name'].endswith(LANG_SUFFIX), 'Output validator "fluent_core_translated" must only used on a field that ends with "_translated"'

    required_langs = schema.get('required_language', field.get('required_language'))
    if required_langs and not isinstance(required_langs, list):
        required_langs = [required_langs]
    
    lang = required_langs[0] if required_langs else config.get('ckan.locale_default', 'en')

    def validator(key, data, errors, context):
        """
        Return a value for a core field using a multilingual dict.
        """
        data[key] = fluent_text_output(data[key])

        k = key[-1]
        new_key = key[:-1] + (k[:-len(LANG_SUFFIX)],)

        if new_key in data:
            data[new_key] = scheming_language_text(data[key], lang)

    return validator

@scheming_validator
@validator
def schemingdcat_fluent_text(field, schema):
    """
    Accept multilingual text input in the following forms
    and convert to a json string for storage:

    1. a multilingual dict, e.g.

       {"en": "Text", "fr": "texte"}

    2. a JSON encoded version of a multilingual dict, for
       compatibility with old ways of loading data, e.g.

       '{"en": "Text", "fr": "texte"}'

    3. separate fields per language (for form submissions):

       fieldname-en = "Text"
       fieldname-fr = "texte"

    When using this validator in a ckanext-scheming schema setting
    "required" to true will make all required_language key required to
    pass validation.
    
    When type is group or organization and field name is title, the display_name field will be populated with the value of the first required language.
    
    4. If the value is missing and is required, an error message will be added to the errors list.
    
    5. If the value is missing and is not required, an empty JSON string will be assigned to the data key.
    """
    # combining scheming required checks and fluent field processing
    # into a single validator makes this validator more complicated,
    # but should be easier for fluent users and eliminates quite a
    # bit of duplication in handling the different types of input
    required_langs = []
    form_languages = fluent_form_languages(field, schema=schema)
    alternate_langs = {}
    if field and field.get('required'):
        if field.get('required_language'):
            if isinstance(field.get('required_language'), list):
                required_langs = field.get('required_language')
            else:
                required_langs = [field.get('required_language')]
        alternate_langs = fluent_alternate_languages(field, schema=schema)

    #log.debug("Start | required_langs: {0}".format(required_langs))
    #log.debug("Start | field: {0}".format(field))

    def validator(key, data, errors, context):
        # just in case there was an error before our validator,
        # bail out here because our errors won't be useful
        if errors[key]:
            return

        value = data[key]
        pkg_type = data.get(key[:-1] + ('type',), {})

        #log.debug("Start | key: {0}".format(key))
        #log.debug("Start | key: {0} and data:{1}".format(key, data))

        # Extract any extras from the data dictionary that match the prefix
        try:
            extras = data.get(key[:-1] + ('__extras',), {})
        except:
            extras = None

        # Extract the last character of the key and append a hyphen to it
        prefix = key[-1] + '-'
        
        # Check if extras is not None and contains keys starting with the fluent prefix
        extras_mode = extras is not None and any(name.startswith(prefix) for name in extras.keys())

        #log.debug("Start | extras_mode: {1} and extras: {0}".format(extras, extras_mode))

        # 1 or 2. dict or JSON encoded string
        if value is not missing and (value != '' and not field.get('required')) and extras_mode is False:
            #log.debug("1-2 | key: {0} - value: {1}".format(key, value))
            if isinstance(value, six.string_types):
                try:
                    value = json.loads(value)
                except ValueError:
                    errors[key].append(_('Failed to decode JSON string'))
                    return
                except UnicodeDecodeError:
                    errors[key].append(_('Invalid encoding for JSON string'))
                    return
            if not isinstance(value, dict):
                errors[key].append(_('expecting JSON object'))
                return

            for lang, text in value.items():
                try:
                    m = re.match(BCP_47_LANGUAGE, lang)
                except TypeError:
                    errors[key].append(_('invalid type for language code: %r')
                        % lang)
                    continue
                if not m:
                    errors[key].append(_('invalid language code: "%s"') % lang)
                    continue
                if not isinstance(text, six.string_types):
                    errors[key].append(_('invalid type for "%s" value') % lang)
                    continue
                if isinstance(text, str):
                    try:
                        value[lang] = text if six.PY3 else text.decode(
                            'utf-8')
                    except UnicodeDecodeError:
                        errors[key]. append(_('invalid encoding for "%s" value')
                            % lang)

            for lang in required_langs:
                if value.get(lang) or any(
                        value.get(l) for l in alternate_langs.get(lang, [])):
                    continue
                errors[key].append(_('Required language "%s" missing') % lang)

            if not errors[key]:
                data[key] = json.dumps(value)
                #log.debug("1-2 | output: {0}".format(data))
            return

        # 3. separate fields
        if extras_mode:
            #log.debug("3 | key: {0}".format(key))
            output = {}
            extras = data.get(key[:-1] + ('__extras',), {})

            for name, text in extras.items():
                if not name.startswith(prefix):
                    continue
                lang = name.split('-', 1)[1]
                m = re.match(BCP_47_LANGUAGE, lang)
                if not m:
                    errors[name] = [_('invalid language code: "%s"') % lang]
                    output = None
                    continue

                if output is not None:
                    output[lang] = text

            for lang in required_langs:
                if extras.get(prefix + lang) or any(
                        extras.get(prefix + l) for l in alternate_langs.get(lang, [])):
                    continue
                errors[key[:-1] + (key[-1] + '-' + lang,)] = [_('Missing value')]
                output = None

            if output is None:
                return

            for lang in output:
                del extras[prefix + lang]
            data[key] = json.dumps(output)
            #log.debug("3 | output: {0}".format(data))

            # group/organizations display_name fields
            if pkg_type in ('group', 'organization') and 'title' in ''.join(key):
                try:
                    lang = required_langs[0] if required_langs else config.get('ckan.locale_default', 'en')
                    display_name = ('display_name',)
                    #log.debug('3-group/organization | output[lang]: {0} and data: {1}'.format(output[lang], data))
                    data[display_name] = output[lang] or ''
                except ValueError:
                    data[display_name] = ''

        # 4. value is missing and is required
        if (value is missing) and field.get('required'):
            errors[key].append(_('Missing value'))
            return

        # 5. value is missing and is not required and is fluent field
        if (value is missing) and not field.get('required'):
            data[key] = {language: "" for language in form_languages}

    return validator

@scheming_validator
@validator
def schemingdcat_if_empty_same_as_title(field, schema):
    """
    Returns a validator function that sets a value for a core field using a multilingual dict.

    Args:
        field (dict): The field to validate.
        schema (dict): The schema for the field.

    Returns:
        function: A validator function that sets a value for a core field using a multilingual dict.
    """
    required_langs = schema.get('required_language', field.get('required_language'))
    if required_langs and not isinstance(required_langs, list):
        required_langs = [required_langs]
    
    lang = required_langs[0] if required_langs else config.get('ckan.locale_default', 'en')

    def validator(key, data, errors, context):
        """
        Return a value for a core field check a multilingual dict.
        """
        # title_translated
        fallback_key = 'title' + LANG_SUFFIX
        pkg_type = data.get(key[:-1] + ('type',), {})
        
        extras = schemingdcat_get_extras(data, pkg_type)
        output = json.loads(extras.get(fallback_key, '{}')).get(lang, '')

        data[key] = output
        #log.debug('schemingdcat_if_empty_same_as_title | output: {0}'.format(output))

    return validator

@scheming_validator
@validator
def schemingdcat_if_empty_datenow(field, schema):
    """
    Returns a validator function that sets the current datetime as the value for a field if it's empty.

    This validator checks if the value of the field is missing, None, or an empty string. If so, it sets the current datetime in ISO format as the value of the field.

    Args:
        field (dict): The field to validate.
            A dictionary containing information about the field to be validated.
        schema (dict): The schema for the field.
            A dictionary containing the schema for the field to be validated.

    Returns:
        function: A validation function that can be used to validate the field and set the current datetime if it's empty.
    """
    def validator(key, data, errors, context):
        value = data[key]
        
        if value is missing or value is None or value == '':
            data[key] = datetime.datetime.now().isoformat()

    return validator

@scheming_validator
@validator
def schemingdcat_update_modified(field, schema):
    """
    Returns a validator function that always sets the current datetime as the value for a field.

    This validator does not check the current value of the field. It always sets the current datetime in ISO format as the value of the field.

    Args:
        field (dict): The field to update.
            A dictionary containing information about the field to be updated.
        schema (dict): The schema for the field.
            A dictionary containing the schema for the field to be updated.

    Returns:
        function: A validation function that can be used to update the field with the current datetime.
    """
    def validator(key, data, errors, context):
        data[key] = datetime.datetime.now().isoformat()

    return validator

@validator
def multilingual_text_output(value):
    """
    Returns a multilingual dictionary representation of the stored JSON value.
    If the value is already a dictionary, it is returned as is.

    Args:
        value (str or dict): The value to convert to a multilingual dictionary.

    Returns:
        dict: A multilingual dictionary representation of the stored JSON value.
    """
    if isinstance(value, dict):
        return value
    return parse_json(value)
    
def schemingdcat_get_extras(data, pkg_type='dataset'):
    """
    Returns the extras for a given package type from the provided data dictionary.

    Args:
        data (dict): The data dictionary to extract extras from.
        pkg_type (str, optional): The package type to extract extras for. Defaults to 'dataset'.

    Returns:
        dict: A dictionary containing the extras for the given package type.
    """
    extras = {}
    try:
        if pkg_type == 'dataset':
            extras = data.get(key[:-1] + ('__extras',), {})  # noqa: F821
            return extras
        elif pkg_type in ('group', 'organization'):
            for key, value in data.items():
                if isinstance(key, tuple) and key[0] == 'extras' and key[2] == '__extras':
                    extras[value['key']] = value['value']
            return extras
    except:
        return extras

@scheming_validator
@validator
def schemingdcat_multiple_choice_custom_tag_string(field, schema):
    """
    Accept zero or more values from a list of choices and convert
    to a json list for storage. Also act like scheming_required to check for at least one non-empty string when required is true:
    1. a list of strings, e.g.
       ["choice-a", "choice-b"]
    2. a single string for single item selection in form submissions:
       "choice-a"
    """
    static_choice_values = None
    if 'choices' in field:
        static_choice_order = [c['value'] for c in field['choices']]
        static_choice_values = set(static_choice_order)
    def validator(key, data, errors, context):
        # if there was an error before calling our validator
        # don't bother with our validation
        if errors[key]:
            return

        value = data[key]
        
        # 1. single string to List or 2. List to string comma separated
        if value is not missing:
            if isinstance(value, six.string_types):
                if "," not in value:
                    # If there are no commas, treat the whole string as one value
                    value = [value]
                elif "[" not in value:
                    # If there are commas but no brackets, split on commas
                    value = value.split(",")
                else:
                    # If there are brackets, assume it's a JSON array
                    value = json.loads(value)
            if not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                raise StopOnError
        else:
            value = []
        choice_values = static_choice_values
        if not choice_values:
            choice_order = [
                choice['value']
                for choice in sh.scheming_field_choices(field)
            ]
            choice_values = set(choice_order)
        selected = set()
        for element in value:
            if element in choice_values:
                selected.add(element)
                continue
            errors[key].append(_('unexpected choice "%s"') % element)

        if not errors[key]:
            # Return as a comma-separated string of values
            data[key] = ','.join([v for v in
                (static_choice_order if static_choice_values else choice_order)
                if v in selected])

            if field.get('required') and not selected:
                errors[key].append(_('Select at least one'))
    
    return validator

@validator
def schemingdcat_multiple_choice_custom_tag_output(value):
    """
    Output validator that returns a list of values for a field.
    
    This function takes a value and checks if it is a list. If it is, it returns the list as is.
    If the value is a string that can be loaded as a JSON, it does so and returns the result.
    If the value is a string containing commas, it splits the string into a list of strings.
    If the value is a string without commas, it returns a list containing the string.
    
    Args:
    - value: The value to be processed.
    
    Returns:
    - A list of values derived from the input value.
    """
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except ValueError:
        if ',' in value:
            return [tag_string.strip() for tag_string in value.split(',') if tag_string.strip()]
        else:
            return [value]

@validator
def copy_from(copy_key):
    def validator(key, data, errors, context):
        current_value = data.get(key)
        if current_value and current_value is not missing:
            return
        value = data.pop((copy_key, ), None)
        if not value:
            value = data.get(('__extras', ), {}).get(copy_key)
        if value is not missing:
            data[key] = value

    return validator

def check_url(url):
    """Checks if a given URL is valid.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
    
@scheming_validator
@validator
def schemingdcat_dataset_scope(field, schema):
    """
    Returns a validator function that checks if the 'dcat_type' value exists in the choices. If it exists, it sets the value of the field to the value of 'non_spatial_dataset' in the choice. Otherwise, it sets the value to 'non_spatial_dataset'.

    Args:
        field (dict): Information about the field to be updated.
        schema (dict): The schema for the field to be updated.

    Returns:
        function: A validation function that can be used to update the field based on the presence of 'non_spatial_dataset' in the choice corresponding to 'dcat_type'.
    """
    schema_data = helpers.schemingdcat_get_cached_schema(schema['dataset_type'])
    dcat_type_field = next((f for f in schema_data['dataset_fields'] if f['field_name'] == 'dcat_type'), None)
    choices = dcat_type_field['choices'] if dcat_type_field else []
    choices_dict = {item["value"]: item.get('dataset_scope', 'non_spatial_dataset') for item in choices}

    def validator(key, data, errors, context):
        dcat_type = data.get(('dcat_type', ))
        data[key] = choices_dict.get(dcat_type, 'non_spatial_dataset')

    return validator

@scheming_validator
@validator
def schemingdcat_xls_metadata_template(field, schema):
    """
    Returns a validator function that checks if the 'metadata_template_id' value exists in the 'identifier'. If it exists, it sets the value of the field to True. Otherwise, it leaves the value unchanged.

    Args:
        field (dict): Information about the field to be updated.
        schema (dict): The schema for the field to be updated.

    Returns:
        function: A validation function that can be used to update the field based on the presence of 'metadata_template_id' in the 'identifier'.
    """
    metadata_template_id = helpers.schemingdcat_get_metadata_templates_search_identifier()
    
    def validator(key, data, errors, context):
        identifier = data.get(('identifier', ))
        if identifier and metadata_template_id in identifier:
            data[key] = True

    return validator

@scheming_validator
@validator
def schemingdcat_spatial_uri_validator(field, schema):
    """
    Returns a validator function that checks if the 'spatial_uri' value exists in the choices. If it exists, it sets the value of the field to the value of 'spatial' in the choice and 'spatial_coverage' fields. Otherwise, it sets the value to ''.

    Args:
        field (dict): Information about the field to be updated.
        schema (dict): The schema for the field to be updated.

    Returns:
        function: A validation function that can be used to update the field based on the presence of 'spatial' in the choice corresponding to 'spatial_uri'.
    """
    schema_data = helpers.schemingdcat_get_cached_schema(schema['dataset_type'])
    spatial_uri_field = next((f for f in schema_data['dataset_fields'] if f['field_name'] == 'spatial_uri'), None)
    choices = spatial_uri_field['choices'] if spatial_uri_field else []

    def validator(key, data, errors, context):
        if data[key] is missing or data[key] is None or data[key] == '':
            spatial_uri = data.get(('spatial_uri', ))
            choice = next((item for item in choices if item["value"] == spatial_uri), None)
            data[key] = choice.get('spatial', '') if choice else missing

    return validator

@scheming_validator
@validator
def schemingdcat_if_empty_guess_format(field, schema):
    """
    Guess the format of a resource based on its URL.

    This function attempts to guess the format of a resource based on its URL.
    If the resource format is not provided or is missing, and the resource is not being updated,
    it tries to guess the format from the URL. If the URL is a valid URL (i.e., it has a scheme and a path),
    it uses the mimetypes module to guess the format and encoding. If a mimetype is found, it is stored in the data
    dictionary and the format is set to the last part of the mimetype (after the '/'). If no mimetype is found,
    the format is set to the file extension of the URL.

    Args:
        field (dict): The field dictionary.
        schema (dict): The schema dictionary.

    Returns:
        function: A validator function which takes four arguments: key, data, errors, context.
    """
    def validator(key, data, errors, context):
        value = data[key]
        resource_id = data.get(key[:-1] + ('id',))
        
        # if resource_id then an update
        if (not value or value is missing) and not resource_id:
            url = data.get(key[:-1] + ('url',), '')
            if not url:
                return

            # Uploaded files have only the filename as url, so check scheme to
            # determine if it's an actual url
            parsed = urlparse(url)
            if parsed.scheme and not parsed.path:
                return

            mimetype, encoding = mimetypes.guess_type(url)
            if mimetype:
                data[key] = mimetype.split('/')[-1].upper()
                data[key[:-1] + ('mimetype',)] = f"{mimetype_base_uri}/{mimetype}"
                data[key[:-1] + ('encoding',)] = encoding or OGC2CKAN_HARVESTER_MD_CONFIG["encoding"]
                
    return validator

@scheming_validator
@validator
def schemingdcat_valid_email(field, schema):
    """
    Validates if the provided string is a basically valid email address.

    Args:
        field (dict): Information about the field to be validated.
        schema (dict): The schema for the field to be validated.

    Returns:
        function: A validation function that checks if the email is valid.
    """
    
    def validator(key, data, errors, context):
        value = data[key].strip()
        
        if value in (missing, None, ''):
            data[key] = None
            return validator

        elif "@" not in value or "." not in value.split("@")[-1]:
            errors[key].append(_('Expecting valid email: "user@example.org"'))
            
        data[key] = value

    return validator

# subfield dicts. Spatial coverage validators
@scheming_validator
@validator
def schemingdcat_fill_spatial_dependent_fields(field, schema):
    """
    Fills spatial dependent fields such as centroid and bounding box based on the provided GeoJSON value.

    Args:
        field (dict): The field definition containing the dependent fields information.
        schema (dict): The schema definition.

    Returns:
        function: A validator function that processes the GeoJSON value and fills the dependent fields.

    Raises:
        json.JSONDecodeError: If the provided value is not a valid JSON.
        ValueError: If the provided GeoJSON does not represent a Polygon.
    """    
    def validator(key, data, errors, context):
        dependent_fields = field.get('dependent_fields')

        if not dependent_fields:
            return validator                  

        value = data.get(key)

        if value in (missing, None, ''):
            data[key] = None
            return validator

        try:
            value_dict = json.loads(value)
            polygon = shape(value_dict)
            if not isinstance(polygon, Polygon):
                raise ValueError("The provided GeoJSON does not represent a Polygon.")
        except (json.JSONDecodeError, ValueError) as e:
            log.error('Invalid GeoJSON value: %s', e)
            errors[key].append('Invalid GeoJSON value.')
            return validator

        centroid = polygon.centroid
        centroid_value = {
            "type": "Point",
            "coordinates": [round(centroid.x, 5), round(centroid.y, 5)]
        }
        
        subfields = {
            'centroid': centroid_value,
            'bbox': value_dict
        }
        
        for subfield_name, subfield_value in subfields.items():
            subfield_dict = {
                'field_name': dependent_fields['field_name'],
                'subfields': [{'field_name': subfield_name}]
            }
            schemingdcat_fill_subfields(dependent_fields['field_name'], subfield_dict, subfield_value, data)

    return validator

@scheming_validator
@validator
def schemingdcat_fill_spatial_uri_dependent_fields(field, schema):
    """
    Validator to fill dependent fields based on the spatial URI.

    This validator checks if the provided spatial URI has corresponding dependent fields
    and fills them with appropriate values. It uses the default locale to fetch the 
    language-specific text for the spatial URI.

    Args:
        field (dict): The field dictionary containing 'choices' and 'dependent_fields'.
        schema (dict): The schema dictionary.

    Returns:
        function: The validator function to be used in the scheming validation process.
    """
    lang = config.get('ckan.locale_default', 'en')
    spatial_uri_choices = field['choices'] if field else []
    
    def validator(key, data, errors, context):
        dependent_fields = field.get('dependent_fields')

        if not dependent_fields:
            return validator                  

        value = data.get(key)
        
        if value in (missing, None, ''):
            data[key] = None
            return validator
        
        value_choice = next((item for item in spatial_uri_choices if item.get('value') == value), None)
        
        if value_choice:
            spatial_text_value = scheming_language_text(value_choice.get('label'), lang)
            
            subfields = {
                'uri': value,
                'text': spatial_text_value
            }
            
            for subfield_name, subfield_value in subfields.items():
                subfield_dict = {
                    'field_name': dependent_fields['field_name'],
                    'subfields': [{'field_name': subfield_name}]
                }
                schemingdcat_fill_subfields(dependent_fields['field_name'], subfield_dict, subfield_value, data)
                
    return validator

# subfield dicts. Validators used to populate dependent fields need to be migrated to only contact dict instead of contact_* fields in the future.
@scheming_validator
@validator
def schemingdcat_fill_dependent_fields(field, schema):
    """
    Validator that fills dependent fields based on the value of the primary field.

    This validator checks if the primary field has a value and, if so, fills the dependent fields
    specified in the `dependent_fields` attribute of the primary field. If the dependent fields
    have subfields, it will also fill those subfields with the same value.

    Args:
        field (dict): The field definition containing the `dependent_fields` attribute.
        schema (dict): The schema definition.

    Returns:
        function: A validator function that processes the dependent fields.

    Validator Args:
        key (tuple): The key of the field being validated.
        data (dict): The data dictionary containing all field values.
        errors (dict): The dictionary to collect validation errors.
        context (dict): The context dictionary containing additional information.

    Raises:
        None: This validator does not raise exceptions but logs errors if they occur.
    """
    #log.debug('field.dependent_fields: %s', field.get('dependent_fields'))
    def validator(key, data, errors, context):        
        dependent_fields = field.get('dependent_fields')

        if not dependent_fields:
            return validator                  

        value = data.get(key)
        
        if value in (missing, None, ''):
            data[key] = None
            return validator
                
        dependent_field_name = dependent_fields['field_name']
                        
        schemingdcat_fill_subfields(dependent_field_name, dependent_fields, value, data)

    return validator

# Aux function to fill subfields for schemingdcat fill_dependent_fields validators
def schemingdcat_fill_subfields(dependent_field_name, dependent_fields, value, data):
    """
    Fills subfields for schemingdcat fill_dependent_fields validators.

    Args:
        dependent_field_name (str): The name of the dependent field.
        dependent_fields (dict): The dictionary containing subfields information.
        value (any): The value to be set for the subfields.
        data (dict): The data dictionary where the subfields will be set.

    Returns:
        None

    Raises:
        IndexError: If there is an indexing error while setting the subfield value.
        ValueError: If there is a value error while setting the subfield value.
        KeyError: If there is a key error while setting the subfield value.
    """
    dependent_key = (dependent_field_name,)
    subfields = dependent_fields.get('subfields')

    if subfields:
        for subfield in subfields:
            subfield_name = subfield['field_name']
            if value:
                dependent_subkey = (dependent_field_name, 0, subfield_name)
                try:
                    data[dependent_subkey] = value
                except (IndexError, ValueError, KeyError) as e:
                    log.error('Exception occurred while setting subfield value: %s', e)
    else:
        if value:
            try:
                data[dependent_key] = value
            except (IndexError, ValueError, KeyError) as e:
                log.error('Exception occurred while setting field value: %s', e)
                
@validator
def schemingdcat_stats_id_validator(value, context):
    '''
    Custom validator for the 'id' field (stat_name). Ensures that the stat_name meets certain criteria.
    
    Parameters:
        - value: The value provided for the key.
        - context: Additional context (optional).

    Return:
        - value
    
    '''
    if not isinstance(value, str):
        raise logic.ValidationError('The name of the statistic must be a text string.')
    return value

@scheming_validator
@validator
def schemingdcat_hvd_category_applicable_legislation(field, schema):
    """
    Returns a validator function that checks if the 'hvd_category' value is not empty. If it is not empty, it updates the value of the field by adding the Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use (Text with EEA relevance) to all datasets that contain an hvd_category (HVD Category).

    Args:
        field (dict): Information about the field to be updated.
        schema (dict): The schema for the field to be updated.

    Returns:
        function: A validation function that updates the field based on the presence of 'hvd_category'.
    """   
    def validator(key, data, errors, context):
        hvd_category = data.get(('hvd_category', ))
        if hvd_category:
            if isinstance(data.get(key), list):
                if DCAT_AP_HVD_CATEGORY_LEGISLATION not in data[key]:
                    data[key].append(DCAT_AP_HVD_CATEGORY_LEGISLATION)
            else:
                if data.get(key) != DCAT_AP_HVD_CATEGORY_LEGISLATION:
                    data[key] = [DCAT_AP_HVD_CATEGORY_LEGISLATION]

    return validator

@scheming_validator
@validator
def normalize_tag_strings(field, schema):
    """
    Normalizes the value of a specified tag_string and tags before tag_string_convert validator using the rules determined by normalize_string

    Args:
        field (dict): Information about the field to update.
        schema (dict): The schema for the field to update.

    Returns:
        function: A validation function to normalize the value of the key.
    """
    def validator(key, data, errors, context):
        value = data.get(key)

        try:
            if value:
                normalized_values = []
                if isinstance(value, str):
                    tags = value.split(',')
                    normalized_values = [normalize_string(tag.strip()) for tag in tags]
                    data[key] = ','.join(normalized_values)
                elif isinstance(value, list):
                    for tag in value:
                        if 'name' in tag:
                            tag['name'] = normalize_string(tag['name'].strip())
                        if 'display_name' in tag:
                            tag['display_name'] = normalize_string(tag['display_name'].strip())

            # Normalize the tags in data
            for data_key in data.keys():
                if isinstance(data_key, tuple) and data_key[0] == 'tags' and data_key[2] == 'name':
                    data[data_key] = normalize_string(data[data_key].strip())

        except Exception as e:
            log.error(f"Error normalizing tags: {e}")
            
    return validator

@lru_cache(maxsize=44)
def normalize_string(s):
    """Normalizes a string according to the rules:
        - Replaces spaces with hyphens.
        - Converts to lowercase.
        - Removes disallowed characters.
        - Normalize to using only alphanumeric and spanish accents (áéíóúüñ) or hyphens "-", underscores "_" and dots "."
        - Limits the length to 30 characters.

    Args:
        s (str): String to normalize.

    Returns:
        str: Normalized string.

    Raises:
        Invalid: If the string contains disallowed characters.
    """    
    s = s.strip()
    s = s.lower()
    s = s.replace(' ', '-')
    s = TAGS_NORMALIZE_PATTERN.sub('', s)
    s = s[:30]
    return s

@scheming_validator
@validator
def schemingdcat_contact_as_default_publisher(field, schema):
    """
    Validator to set a default publisher contact information if not provided.

    Args:
        field (str): The field name.
        schema (dict): The schema definition.

    Returns:
        function: The validator function.
    """
    def validator(key, data, errors, context):
        try: 
            # Convert key to string if it is a tuple
            if isinstance(key, tuple):
                field_name = key[0]
            else:
                field_name = key
            
            fallback_value = CONTACT_PUBLISHER_FALLBACK.get(field_name, None)
            
            if not data.get(key):
                if fallback_value and 'ckanext.schemingdcat' in fallback_value:
                    data[key] = config.get(fallback_value)
                elif fallback_value:
                    data[key] = fallback_value
            
            if fallback_value is None:
                data[key] = None
        except Exception as e:
            raise ValueError(f"Unable to set default publisher value {fallback_value} for contact field: {field_name}. Error: {e}")

    return validator

@scheming_validator
@validator
def schemingdcat_access_url_if_empty_same_as_url(field, schema):
    """
    Validator to set a distribution access URL based on the resource URL type.
    """
    def validator(key, data, errors, context):
        # Get resource URL and dataset ID
        dataset_id = data.get(key[:-1] + ('package_id',), None)
        resource_id = data.get(key[:-1] + ('id',), None)
        resource_url = data.get(key[:-1] + ('url',))

        if dataset_id and resource_id and not resource_url:
            data[key] = ckan_helpers.url_for('resource.read', id=dataset_id, resource_id=resource_id, _external=True)
        else: 
            data[key] = resource_url

    return validator

@scheming_validator
@validator
def schemingdcat_download_url_if_empty_same_as_url(field, schema):
    """
    Validator to set a distribution download URL based on the resource URL type.
    """
    def validator(key, data, errors, context):
        resource_url = data.get(key[:-1] + ('url',), None)
        value = data.get(key)
        
        if not value or value is missing or value == resource_url:
            # Get resource URL and dataset ID
            dataset_id = data.get(key[:-1] + ('package_id',), None)
            resource_id = data.get(key[:-1] + ('id',), None)
            resource_url = data.get(key[:-1] + ('url',))

            if dataset_id and resource_id and dataset_id in resource_url:
                data[key] = ckan_helpers.url_for('resource.download', id=dataset_id, resource_id=resource_id, _external=True)
            else:
                data[key] = resource_url

    return validator

@scheming_validator
@validator
def schemingdcat_dataset_url(field, schema):
    """
    Validator to set a dataset URL based on the dataset ID.

    Args:
        field (str): The field name.
        schema (dict): The schema definition.

    Returns:
        function: The validator function.
    """
    def validator(key, data, errors, context):
        dataset_id = data.get(('id', ))
        package_type = data.get(('type', ), 'dataset')
        if dataset_id:
            data[key] = ckan_helpers.url_for(
                'dataset.read',
                id=dataset_id,
                package_type=package_type,
                _external=True
            )
        else:
            data[key] = ''
    return validator