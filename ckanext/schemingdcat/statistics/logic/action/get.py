from ckan.logic import side_effect_free

from ckanext.schemingdcat.statistics import model as stats_model

@side_effect_free
def schemingdcat_statistics_show(context, data_dict):
    """
    Retrieve a specific portal statistic by its ID and type.

    Args:
        context (dict): The context of the API call.
        data_dict (dict): A dictionary containing the parameters for the API call.
            id (str): The ID of the statistic to retrieve. For `stat_type: portal`, the possible values are:
                - datasets
                - distributions
                - groups
                - organizations
                - tags
                - spatial_datasets
                - endpoints
            For `stat_type: theme`, the ID depends on the schema (e.g., theme, theme_es, theme_eu, etc.) and the value set in `schemingdcat.default_package_item_icon`.
            stat_type (str): The type of the statistic to retrieve. Possible values are `portal` and `theme`.

    Returns:
        dict: A dictionary representing the portal statistic, or None if not found.

    Example:
        To use this API, you can make a GET request to the following URL:
        ```
        http://<your-ckan-instance>/api/3/action/schemingdcat_statistics_show?id=datasets&stat_type=portal
        ```
    """
    stats_id = data_dict.get('id')
    stat_type = data_dict.get('stat_type')

    out = stats_model.PortalStatistics.get(id=stats_id, stat_type=stat_type)
    if out:
        out = stats_model.table_dictize(out, context)
    return out

@side_effect_free
def schemingdcat_statistics_list(context, data_dict):
    """
    Retrieves a list of all portal statistics, optionally sorted by a specified field and direction.

    Args:
        context (dict): The context of the API call.
        data_dict (dict): A dictionary containing the parameters for the API call, including optional 'order_dir' fields.
            order_dir: `asc` or `desc` to specify the order direction.

    Returns:
        list: A list of dictionaries representing the portal statistics, optionally sorted by the specified field and direction.

    Example:
        To use this API, you can make a GET request to the following URL:
        ```
        http://<your-ckan-instance>/api/3/action/schemingdcat_statistics_list?order_dir=asc
        ```
    """
    order_dir = data_dict.get('order_dir', 'desc').lower()

    # Retrieve all portal statistics and order by the specified field and direction
    out = stats_model.PortalStatistics.all(order_dir=order_dir)
    if out:
        out = stats_model.table_dictize(out, context)
    return out
