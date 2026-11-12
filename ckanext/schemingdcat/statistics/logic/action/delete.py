from typing import Any, Dict

import ckan.plugins as p
from ckan import model

from ckanext.schemingdcat.statistics import model as stats_model

def schemingdcat_statistics_delete(self, context: Dict[str, Any], data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resets statistics to zero for a specific type or all types.

    Only users with the 'sysadmin' role are authorized to perform this action.

    Args:
        context (Dict[str, Any]): The context dictionary containing authorization information.
        data_dict (Dict[str, Any]): The data dictionary with parameters for the action.
            - stat_type (Optional[str]): The type of statistics to reset. If not provided, all statistics are reset.

    Returns:
        Dict[str, Any]: A success message indicating that the statistics have been reset.

    Raises:
        NotAuthorized: If the user does not have the required permissions.
        ValidationError: If the input data is invalid.
    """
    # Authorization: Only sysadmins can reset statistics
    user = context.get('user')
    if not user:
        raise p.toolkit.NotAuthorized('User must be logged in to reset statistics.')

    user_obj = model.User.get(user)
    if not user_obj or not user_obj.sysadmin:
        raise p.toolkit.NotAuthorized('User %s not authorized to reset statistics. Only SysAdmins', user)

    # Extract and validate 'stat_type' from data_dict
    stat_type = data_dict.get('stat_type')

    try:
        stats_model.PortalStatistics.reset_statistics(stat_type=stat_type)
    except Exception as e:
        raise p.toolkit.ValidationError(f'An error occurred while resetting statistics: {str(e)}')

    return {'success': True, 'msg': 'Statistics have been reset successfully.'}