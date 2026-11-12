from datetime import datetime, timezone
import json

import ckan.plugins as p
from ckan import model
import ckan.lib.navl.dictization_functions as df

from ckanext.schemingdcat.statistics import model as stats_model
from ckanext.schemingdcat.statistics.schema import schemingdcat_update_statistics_schema

#TODO: Implement the update action
def schemingdcat_statistics_update(context, data_dict):
    pass