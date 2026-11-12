from datetime import datetime
import logging

from ckanext.schemingdcat.lib.csw.processor import SchemingDCATCatalogueServiceWeb


log = logging.getLogger(__name__)


# Custom exceptions.
class OWSNotFoundError(Exception):
    pass

class InvalidOWSServiceError(Exception):
    """Exception raised when the OWS service URL is invalid or unavailable."""
    pass

#TODO: Implentent HarvestOGC logic from [ckan-ogc](https://github.com/mjanez/ckan-ogc/blob/main/ogc2ckan/harvesters/ogc.py)
class OwsService(SchemingDCATCatalogueServiceWeb):
    """
    Represents a OWS (OGC Web Service) service. GeoServer includes several types of OGC services like WCS, WFS and WMS, commonly referred to as “OWS” services

    This class provides methods to interact with a CSW service, such as querying for records.

    Args:
        OwsService (SchemingDCATCatalogueServiceWeb): The base class for the OWS service.

    Attributes:
        sortby (str): The sort order for the records.

    """
