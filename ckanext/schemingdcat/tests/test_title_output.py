"""Legacy translations must not break organization/group output."""
from copy import deepcopy

import pytest

from ckanext.schemingdcat.validators import schemingdcat_if_empty_same_as_title


@pytest.mark.parametrize('kind', ['organization', 'group'])
@pytest.mark.parametrize('field', ['display_name', 'longname'])
@pytest.mark.parametrize('translated,expected', [
    ('{"es":"Título español","en":"English title"}', 'Título español'),
    ({'es': 'Título español'}, 'Título español'),
    ('', 'Existing label'),
    ('   ', 'Existing label'),
    (None, 'Existing label'),
    ('invalid JSON', 'Existing label'),
    ('null', 'Existing label'),
    ('[]', 'Existing label'),
    ('42', 'Existing label'),
    ('"plain text"', 'Existing label'),
    ('{}', 'Existing label'),
    ('{"en":"English title"}', 'Existing label'),
    ('{"es":null}', 'Existing label'),
    ('{"es":[]}', 'Existing label'),
    ('{"es":"  "}', 'Existing label'),
])
def test_translation_output(kind, field, translated, expected):
    key = (field,)
    data = {('type',): kind, key: 'Existing label', ('title',): 'Core title',
            ('name',): 'slug', ('extras', 0, '__extras'): {
                'key': 'title_translated', 'value': translated}}
    before = deepcopy(data)
    errors = {}
    validator = schemingdcat_if_empty_same_as_title(
        {'field_name': field}, {'required_language': ['es', 'en']})
    validator(key, data, errors, {})
    assert data.pop(key) == expected
    before.pop(key)
    assert data == before
    assert errors == {}


@pytest.mark.parametrize('title,name,expected', [
    ('Core title', 'slug', 'Core title'),
    ('', 'slug', 'slug'),
    ('', '', ''),
])
def test_missing_translation_uses_core_fallback(title, name, expected):
    data = {('type',): 'organization', ('title',): title, ('name',): name}
    validator = schemingdcat_if_empty_same_as_title(
        {'field_name': 'display_name'}, {'required_language': 'es'})
    validator(('display_name',), data, {}, {})
    assert data[('display_name',)] == expected
