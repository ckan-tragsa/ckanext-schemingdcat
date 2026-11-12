import ckan.plugins as p
from ckanext.schemingdcat.validators import schemingdcat_stats_id_validator
from ckanext.schemingdcat.interfaces import ISchemingDCATStatisticsSchema

def schemingdcat_default_statistics_schema():
    ignore_empty = p.toolkit.get_validator('ignore_empty')
    ignore_missing = p.toolkit.get_validator('ignore_missing')
    not_empty = p.toolkit.get_validator('not_empty')
    unicode_safe = p.toolkit.get_validator('unicode_safe')
    integer_validator = p.toolkit.get_validator('int_validator')  # Validador para enteros

    return {
        'id': [ignore_empty, unicode_safe, schemingdcat_stats_id_validator],
        'stat_value': [not_empty, integer_validator],
        'stat_type': [not_empty, unicode_safe],
        'icon': [ignore_missing, unicode_safe],
        'label': [ignore_missing, unicode_safe],
    }

def schemingdcat_update_statistics_schema():
    '''
    Returns the schema for the statistics fields that can be added by other
    extensions.

    By default, these are the keys of the
    :py:func:`ckanext.schemingdcat.schema.schemingdcat_default_statistics_schema`.

    Extensions can add or remove keys from this schema using the
    :py:meth:`ckanext.schemingdcat.interfaces.ISchemingDCATStatisticsSchema.schemingdcat_update_statistics_schema`
    method.

    :returns: a dictionary mapping field keys to lists of validator and
               converter functions to be applied to those fields
    :rtype: dict
    '''
    schema = schemingdcat_default_statistics_schema()
    for plugin in p.PluginImplementations(ISchemingDCATStatisticsSchema):
        if hasattr(plugin, 'schemingdcat_update_statistics_schema'):
            schema = plugin.schemingdcat_update_statistics_schema(schema)
    return schema