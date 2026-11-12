import uuid
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging

from six import text_type
import sqlalchemy as sa
from sqlalchemy.orm import class_mapper
try:
    from sqlalchemy.engine import Row
except ImportError:
    try:
        from sqlalchemy.engine.result import RowProxy as Row
    except ImportError:
        from sqlalchemy.engine.base import RowProxy as Row


from ckan import model
import ckan.logic as logic
from ckan.model.domain_object import DomainObject

from ckanext.schemingdcat.helpers import (
    get_schemingdcat_get_catalog_endpoints,
    schemingdcat_get_theme_statistics
)

log = logging.getLogger(__name__)

statistics_table = None

def make_uuid():
    return text_type(uuid.uuid4())

def setup():
    """
    Sets up the statistics table for SchemingDCAT if it does not already exist.

    This function checks if the `statistics_table` is defined and creates it if it does not exist.
    It ensures that the table is defined in the database and logs the action.

    Returns:
        None
    """
    if statistics_table is None:
        define_tables()

    if not statistics_table.exists():
        statistics_table.create(checkfirst=True)
        log.debug('SchemingDCAT statistics table defined in DB')

def clean():
    """
    Cleans the statistics table by dropping it if it exists and recreating it from scratch.

    This function ensures that the `schemingdcat_statistics` table is reset to an empty state.
    It drops the existing table and then calls `setup()` to recreate it.

    Returns:
        None    

    """
    global statistics_table

    try:
        if statistics_table is not None and statistics_table.exists():
            statistics_table.drop(checkfirst=True)
            log.debug('SchemingDCAT statistics table dropped from DB')
    except Exception as e:
        log.error('Error dropping statistics table: %s', e)
    
    setup()
    
def update_table():
    """
    Updates the statistics tables for the Open Data portal.

    This function updates the portal statistics and theme statistics tables.
    It logs a debug message indicating that the Open Data site statistics have been updated.

    Returns:
        None
    """
    update_portal_stats()
    update_theme_stats()
    log.debug('Updated Open Data site statistics')

class PortalStatistics(DomainObject):
    """
    Represents portal statistics within the database.
    """

    @classmethod
    def get(cls, **kw) -> Any:
        """
        Retrieves a single statistic based on the provided criteria.

        Args:
            **kw: Arbitrary keyword arguments to filter the statistic.

        Returns:
            The first `PortalStatistics` instance that matches the criteria, or `None` if no match is found.
        """
        query = model.Session.query(cls).autoflush(False)
        return query.filter_by(**kw).first()

    @classmethod
    def all(cls, order_dir='desc', **kw) -> list:
        """
        Retrieves all statistics that match the provided criteria, optionally sorted by a specified field and direction.

        Args:
            order_dir (str, optional): The direction to order the results ('asc' or 'desc'). Defaults to 'desc'.
            **kw: Arbitrary keyword arguments to filter the statistics.

        Returns:
            A list of `PortalStatistics` instances that match the criteria.
        """
        query = model.Session.query(cls).autoflush(False)
        if order_dir == 'asc':
            query = query.order_by(getattr(cls, 'stat_count').asc())
        else:
            query = query.order_by(getattr(cls, 'stat_count').desc())
        return query.filter_by(**kw).all()

    @classmethod
    def reset(cls, stat_type: Optional[str] = None) -> None:
        """
        Resets statistics to zero for a specific type or all types.

        If `stat_type` is provided, only statistics of that type will be reset.
        If `stat_type` is None, all statistics will be reset to zero.

        Args:
            stat_type (Optional[str]): The type of statistics to reset. Defaults to None.
        """
        query = model.Session.query(cls).autoflush(False)

        if stat_type:
            # Filter statistics by the specified type
            query = query.filter_by(stat_type=stat_type)

        # Update the stat_count to 0 for the selected statistics
        query.update({"stat_count": 0}, synchronize_session=False)

        # Commit the changes to the database
        model.Session.commit()

def define_tables():
    """
    Defines the statistics table in the database and maps it to the `PortalStatistics` class.

    This function creates a global `statistics_table` with the necessary columns if it does not already exist.
    It then maps the `PortalStatistics` class to this table using SQLAlchemy's mapper.
    """
    global statistics_table

    statistics_table = sa.Table(
        'schemingdcat_statistics',
        model.meta.metadata,
        sa.Column('id', sa.types.UnicodeText, primary_key=True, nullable=False),
        sa.Column('stat_count', sa.types.Integer, nullable=False),
        sa.Column('stat_type', sa.types.UnicodeText, nullable=False),
        sa.Column('value', sa.types.UnicodeText, nullable=False),
        sa.Column('icon', sa.types.UnicodeText, nullable=True),
        sa.Column('label', sa.types.UnicodeText, nullable=True)
    )

    model.meta.mapper(
        PortalStatistics,
        statistics_table,
    )
    
def table_dictize(obj_or_list, context):
    """
    Converts a model object or a list of model objects into a dictionary or a list of dictionaries.

    This function introspects the model object's class to retrieve its mapped table
    and extracts all column fields. It then constructs a dictionary where each key
    is a field name and the corresponding value is the value of that field in the
    given object. If a list of objects is provided, it returns a list of dictionaries.

    Args:
        obj_or_list (object or list): The model object or list of model objects to be converted into a dictionary or list of dictionaries.

    Returns:
        dict or list: A dictionary representation of the model object with field names as keys
                      and their corresponding values, or a list of such dictionaries if a list of objects is provided.
    """
    def dictize(obj):
        result_dict = {}

        if isinstance(obj, Row):
            fields = obj.keys()
        else:
            ModelClass = obj.__class__
            table = class_mapper(ModelClass).mapped_table
            fields = [field.name for field in table.c]

        for field in fields:
            value = getattr(obj, field)
            result_dict[field] = value

        return result_dict

    if isinstance(obj_or_list, list):
        return [dictize(obj) for obj in obj_or_list]
    else:
        return dictize(obj_or_list)

def update_portal_stats():
    """
    Updates or creates multiple portal statistics in the database based on current data.
    """
    stat_type = 'portal'

    # Define the additional information for each statistic
    stat_info = {
        'dataset': {
            'icon': 'fas fa-table-list',
        },
        'spatial_dataset': {
            'icon': 'fas fa-globe',
        },
        'tag': {
            'icon': 'fas fa-tags',
        },
        'organization': {
            'icon': 'fa-solid fa-sitemap',
        },
        'group': {
            'icon': 'fas fa-folder-open',
        },
        'endpoint': {
            'icon': 'fa-solid fa-square-share-nodes',
        }
    }

    try:
        stats = {
            'dataset': logic.get_action('package_search')({'fq': 'type:dataset'}, {"rows": 0})['count'],
            'spatial_dataset': get_spatial_datasets(return_count=True),
            'tag': len(logic.get_action('tag_list')({}, {})),
            'organization': len(logic.get_action('organization_list')({}, {})),
            'group': len(logic.get_action('group_list')({}, {})),
            'endpoint': len(get_schemingdcat_get_catalog_endpoints()),
        }
    except Exception as e:
        log.error("Error aggregating portal statistics: %s", e)
        raise

    # Iterate over each statistic and update or create the corresponding entry
    for stat_name, stat_count in stats.items():
        try:
            stat_id = f"{stat_name}s"
            stat = PortalStatistics.get(id=stat_id, stat_type=stat_type)
            icon = stat_info.get(stat_name, {}).get('icon', None)
            if stat:
                stat.stat_count = stat_count
                stat.icon = icon
                stat.value = stat_name
            else:
                new_stat = PortalStatistics(
                    id=stat_id,
                    stat_count=stat_count,
                    stat_type=stat_type,
                    value=stat_name,
                    icon=icon,
                    label=stat_name
                )
                model.Session.add(new_stat)
        except Exception as e:
            log.error("Error updating portal statistic '%s': %s", stat_name, e)

    # Commit all changes at once
    try:
        model.Session.commit()
        log.debug("All portal statistics have been updated.")
    except Exception as e:
        log.error("Error committing portal statistics to the database: %s", e)
        model.Session.rollback()

def update_theme_stats():
    """
    Updates or creates multiple theme statistics in the database based on current data.
    """
    try:
        themes_stats = schemingdcat_get_theme_statistics()
    except Exception as e:
        log.error("Error aggregating theme statistics: %s", e)
        raise

    for stat in themes_stats:
        try:
            count = stat['count']
            icon = stat['icon']
            label = stat['label']
            stat_type = stat['field_name']
            theme_name = f"{stat_type}_{stat['label']}"
            value = stat['value']

            existing_stat = PortalStatistics.get(id=theme_name, stat_type=stat_type)
            if existing_stat:
                existing_stat.stat_count = count
                if not existing_stat.icon:
                    existing_stat.icon = icon
                if not existing_stat.label:
                    existing_stat.label = label
            else:
                new_stat = PortalStatistics(
                    id=theme_name,
                    stat_count=count,
                    stat_type=stat_type,
                    value=value,
                    icon=icon,
                    label=label
                )
                model.Session.add(new_stat)
        except Exception as e:
            log.error("Error updating theme statistic '%s': %s", theme_name, e)

    try:
        model.Session.commit()
        log.debug("All theme statistics have been updated.")
    except Exception as e:
        log.error("Error committing theme statistics to the database: %s", e)
        model.Session.rollback()
        
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