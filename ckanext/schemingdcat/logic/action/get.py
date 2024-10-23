from ckanext.schemingdcat.helpers import schemingdcat_get_schema_names as _schemingdcat_get_schema_names

def schemingdcat_dataset_schema_name(context, data_dict):
    """
    Returns a list of schema names for the schemingdcat extension.

    Args:
        context (dict): The context of the API call.
        data_dict (dict): The data dictionary containing any additional parameters.

    Returns:
        list: A list of schema names.
    """
    return _schemingdcat_get_schema_names()