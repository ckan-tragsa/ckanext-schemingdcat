import re
import logging

log = logging.getLogger(__name__)

from ckanext.schemingdcat.lib.field_mapping import FieldMappingValidator


class SqlFieldMappingValidator(FieldMappingValidator):
    def __init__(self):
        """
        Initialize the SqlFieldMapping object.

        This method overrides the base class's __init__ method and sets up the valid properties and validators
        for the SqlFieldMapping object.

        Valid properties:
        - field_value: The value of the field.
        - field_name: The name of the field.
        - languages: The languages associated with the field.
        - is_key_type: If the field is a key field.
        - f_key_references: The reference to the table.
        - index: The index of the field.

        Validators:
        - 1: validate_v1

        """
        super().__init__()

        # Override valid_props and validators
        self.valid_props = {
            'field_value',
            'field_name',
            'is_p_key', 
            'f_key_references',
            'index',
            self.language_field
        }
        
        self.validators = {
            1: self.validate_v1
        }

    def _is_not_boolean(self, local_field, prop, value):
        """
        Checks if the given value is not a boolean.

        Args:
            local_field (str): The name of the local field being checked.
            prop (str): The name of the property being checked.
            value (Any): The value to be checked.

        Raises:
            ValueError: If the value is not None and not a boolean.

        Returns:
            None
        """
        if value is not None and not isinstance(value, bool):
            raise ValueError(f'The property "{prop}" in field: "{local_field}" should be a boolean. It currently is: "{type(value).__name__}"')

    def _is_not_integer(self, local_field, prop, value):
        """
        Checks if the given value is not an integer.

        This function checks if the given value is not an integer.
        It raises a ValueError if the value is not an integer.

        Args:
            local_field (str): The local field to check.
            prop (str): The property to check.
            value (str): The value to check.

        Raises:
            ValueError: If the value is not an integer.
        """
        if not isinstance(value, int):
            raise ValueError(f'The property "{prop}" in field: "{local_field}" should be an integer. It currently is: "{type(value).__name__}"')

    def _validate_f_key_references(self, local_field, prop, value):
        """
        Validates if the key type is a list and checks if the value is in the correct database key format.

        Args:
            local_field (str): The name of the local field.
            prop (str): The name of the property being validated.
            value (str): The value of the property.

        Raises:
            ValueError: If the key type is not a list or if the value is not in the correct database key format.
        """
        # Validate if the key type is a list
        if isinstance(value, list):
            for f_key_ref in value:
                # If it's a foreign key, validate the database key format
                if f_key_ref:
                    self._is_not_db_key(local_field, prop, f_key_ref)
        else:
            raise ValueError(f'The property "{prop}" in field: "{local_field}" should be a list. It currently is: "{type(value).__name__}"')

    def _is_not_db_key(self, local_field, prop, value):
        """
        Checks if the given value is not a database key.

        This function checks if the given value is not in the format of a database key, i.e., '{schema}.{table}.{field}'.
        It raises a ValueError if the value is not in the correct format.

        Args:
            local_field (str): The local field to check.
            prop (str): The property to check. This function only checks the property 'field_name'.
            value (str): The value to check.

        Raises:
            ValueError: If the value is not in the format of a database key.
        """
        if isinstance(value, str):
            value_split = value.split('.')
            if len(value_split) != 3:
                raise ValueError('The field: "%s" should be in the format: {schema}.{table}.{field}. It currently has "%d" parts: "%s"' % (local_field, len(value_split), value))
        else:
            raise ValueError(f'The property "{prop}" in field: "{local_field}" should be a string. It currently is: "{type(value).__name__}"')

    def validate_v1(self, field_mapping):
        """
        Validate the field mapping for version 1.

        Args:
            field_mapping (dict): The field mapping to validate.

        Raises:
            ValueError: If the field mapping is not valid.
        """
        self._check_non_translated_fields(field_mapping)

        for local_field, field_config in field_mapping.items():
            # Initialize the flags for each local_field
            field_name_defined = False
            field_value_defined = False

            if not isinstance(local_field, str):
                raise ValueError('"local_field_name" must be a string')
            if not isinstance(field_config, dict):
                raise ValueError('"field_config" must be a dictionary')

            for prop, value in field_config.items():
                if prop not in self.valid_props:
                    raise ValueError(f'Invalid property "{prop}" in *_field_mapping. Check: https://github.com/mjanez/ckanext-schemingdcat?tab=field-mapping-structure')
                if prop == 'field_name':
                    field_name_defined = True
                    self._is_not_db_key(local_field, prop, value)
                    self._check_value(local_field, prop, value)
                if prop == 'field_value':
                    field_value_defined = True
                    self._check_value(local_field, prop, value)
                if prop == 'f_key_references':
                    self._validate_f_key_references(local_field, prop, value)
                    self._check_value(local_field, prop, value)
                if prop in ['index', 'is_p_key']:
                    self._is_not_boolean(local_field, prop, value)
                if prop == self.language_field:
                    if not isinstance(value, dict):
                        raise ValueError('%s must be a dictionary', self.language_field)
                    for lang, lang_config in value.items():
                        if not isinstance(lang, str) or not re.match("^[a-z]{2}$", lang):
                            raise ValueError('Language code must be a 2-letter ISO 639-1 code')
                        if not isinstance(lang_config, dict):
                            raise ValueError('Language config must be a dictionary')
                        for lang_prop, lang_value in lang_config.items():
                            if lang_prop not in self.valid_props:
                                raise ValueError(f'Invalid property "{lang_prop}" in *_field_mapping. Check: https://github.com/mjanez/ckanext-schemingdcat?tab=field-mapping-structure')
                            if lang_prop == 'field_name':
                                field_name_defined = True
                                self._is_not_db_key(local_field, lang_prop, lang_value)
                                self._check_value(local_field, lang_prop, lang_value)
                            if lang_prop == 'field_value':
                                field_value_defined = True
                                self._check_value(local_field, lang_prop, lang_value)
                            if lang_prop == 'f_key_references':
                                self._validate_f_key_references(local_field, lang_prop, lang_value)
                                self._check_value(local_field, lang_prop, lang_value)
                            if lang_prop in ['index', 'is_p_key']:
                                self._is_not_boolean(local_field, lang_prop, lang_value)

            # Check the flags after processing each local_field
            if field_name_defined and field_value_defined:
                if field_config.get('field_name') is not None:
                    if not isinstance(field_config.get('field_value'), list):
                        raise ValueError(f'"field_value" for "{local_field}" can only be used if it is a list. First, check that the local_field_name accepts lists, otherwise the harvester validator may have problems.')

        return field_mapping