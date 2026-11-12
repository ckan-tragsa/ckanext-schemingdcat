import logging

import ckan.logic as logic
from ckan.types import ActionResult, Context, DataDict, Query, Schema

from ckanext.schemingdcat.helpers import schemingdcat_get_schema_names as _schemingdcat_get_schema_names

log = logging.getLogger(__name__)

NotFound = logic.NotFound
_check_access = logic.check_access
_get_or_bust = logic.get_or_bust

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


def schemingdcat_member_list(context: Context, data_dict: DataDict) -> ActionResult.MemberList:
    """
    Return the members of a group.

    This function updates the base CKAN action `member_list` to return the `capacity`
    without translation.

    The user must have permission to 'get' the group.

    :param id: the id or name of the group
    :type id: string
    :param object_type: restrict the members returned to those of a given type,
      e.g. ``'user'`` or ``'package'`` (optional, default: ``None``)
    :type object_type: string
    :param capacity: restrict the members returned to those with a given
      capacity, e.g. ``'member'``, ``'editor'``, ``'admin'``, ``'public'``,
      ``'private'`` (optional, default: ``None``)
    :type capacity: string

    :rtype: list of (id, type, capacity) tuples

    :raises: :class:`ckan.logic.NotFound`: if the group doesn't exist
    """
    _check_access('member_list', context, data_dict)
    model = context['model']

    group = model.Group.get(_get_or_bust(data_dict, 'id'))
    if not group:
        raise NotFound

    obj_type = data_dict.get('object_type', None)
    capacity = data_dict.get('capacity', None)

    # User must be able to update the group to remove a member from it
    _check_access('group_show', context, data_dict)

    q = model.Session.query(model.Member).\
        filter(model.Member.group_id == group.id).\
        filter(model.Member.state == "active")

    if obj_type:
        q = q.filter(model.Member.table_name == obj_type)
    if capacity:
        q = q.filter(model.Member.capacity == capacity)

    return [(m.table_id, m.table_name, m.capacity)
            for m in q.all()]