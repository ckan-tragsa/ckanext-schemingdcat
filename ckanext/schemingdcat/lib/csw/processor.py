import logging
import urllib3
from lxml import etree

from owslib.iso import MD_Metadata
from owslib.csw import CatalogueServiceWeb as OwsCatalogueServiceWeb
from owslib.util import Authentication
from owslib.fes import PropertyIsLike, PropertyIsEqualTo, SortBy, SortProperty
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

from ckanext.schemingdcat.config import (
    CSW_DEFAULT_LIMIT,
    CQL_QUERY_DEFAULT,
    CQL_SEARCH_TERM_DEFAULT,
    OUTPUT_SCHEMA
)

log = logging.getLogger(__name__)


# Disable SSL warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Custom exceptions.
class CSWNotFoundError(Exception):
    pass

class InvalidCSWServiceError(Exception):
    """Exception raised when the CSW service URL is invalid or unavailable."""
    pass

class SchemingDCATCatalogueServiceWeb(object):
    """
    A class to interact with a CSW (Catalogue Service for the Web) server.

    This class provides methods to retrieve records from a CSW server using various query parameters.

    Attributes:
        csw_url (str): The URL of the CSW server.
        csw (OwsCatalogueServiceWeb): An instance of the OWSLib CatalogueServiceWeb class.
        schema (str): The output schema for the CSW records.

    Args:
        url (str): The URL of the CSW server.
        ssl_verify (bool): Whether to verify the SSL certificate. Default is True.
    """

    def __init__(self, url, ssl_verify=True):
        """
        Initializes the SchemingDCATCatalogueServiceWeb with the given URL and SSL verification setting.

        Args:
            url (str): The URL of the CSW server.
            ssl_verify (bool): Whether to verify the SSL certificate. Default is True.
        """
        self.csw_url = self.get_csw_url(url)
        # Create an instance of Authentication with SSL_VERIFY
        auth = Authentication(verify=ssl_verify)
        # Pass 'auth' when initializing CatalogueServiceWeb
        self.csw = OwsCatalogueServiceWeb(self.csw_url, auth=auth)
        self.schema = OUTPUT_SCHEMA

    def get_csw_url(self, url, version="2"):
        """
        Constructs the CSW URL with the required service and request parameters.
    
        Args:
            url (str): The base URL of the CSW server.
    
        Returns:
            str: The constructed CSW URL with required parameters.
        """
        parsed_url = urlparse(url)
        
        # Required parameters for CSW
        query_params = {
            "service": "CSW",
            "request": "GetRecords",
            "version": "2.0.2"
        }
        
        # Merge with existing query parameters if any
        if parsed_url.query:
            existing_params = dict(parse_qsl(parsed_url.query))
            query_params.update(existing_params)
        
        query = urlencode(query_params)
        
        csw_url = urlunparse((
            parsed_url.scheme, 
            parsed_url.netloc, 
            parsed_url.path,
            parsed_url.params, 
            query, 
            parsed_url.fragment
        ))
        
        log.debug(f"Constructed CSW URL: {csw_url}")
        return csw_url

    def get_csw_records(self, cql=None, cql_query=None,
                        cql_search_term=None, cql_use_like=False,
                        typenames="csw:Record",  # Cambiado a csw:Record
                        limit=CSW_DEFAULT_LIMIT, 
                        esn="full", 
                        outputschema=OUTPUT_SCHEMA,
                        maxrecords=75, 
                        startposition=0, 
                        sortproperty='dc:identifier'):
        """
        Retrieve records from a CSW server.

        Args:
            typenames (str, optional): The typeNames to query against. Defaults to "csw:Record".
            limit (int, optional): The maximum number of records to return. No records are returned if 0. Defaults to None.
            esn (str, optional): The ElementSetName 'full', 'brief' or 'summary'. Defaults to 'summary'.
            outputschema (str, optional): The outputSchema. Defaults to 'http://www.opengis.net/cat/csw/2.0.2'.
            page (int, optional): The number of records to return per page. Defaults to 30.
            startposition (int, optional): Requests a slice of the result set, starting at this position. Defaults to 0.
            sortproperty (str, optional): The sortProperty. Defaults to 'dc:identifier'.

        Returns:
            record_ids (list): A list of record identifiers from the CSW server.

        Additional Information:
            getrecords2 (OWSLib): Construct and process a GetRecords request in order to retrieve metadata records from a CSW.
            Parameters
            ----------
            - constraints: the list of constraints (OgcExpression from owslib.fes module)
            - sortby: an OGC SortBy object (SortBy from owslib.fes module)
            - typenames: the typeNames to query against (default is csw:Record)
            - esn: the ElementSetName 'full', 'brief' or 'summary' (default is 'summary')
            - outputschema: the outputSchema (default is 'http://www.opengis.net/cat/csw/2.0.2')
            - format: the outputFormat (default is 'application/xml')
            - startposition: requests a slice of the result set, starting at this position (default is 0)
            - maxrecords: the maximum number of records to return. No records are returned if 0 (default is 10)
            - cql: common query language text.  Note this overrides bbox, qtype, keywords
            - xml: raw XML request.  Note this overrides all other options
            - resulttype: the resultType 'hits', 'results', 'validate' (default is 'results')
            - distributedsearch: `bool` of whether to trigger distributed search
            - hopcount: number of message hops before search is terminated (default is 1)
        """
        try:
            self.csw.sortby = SortBy([SortProperty(sortproperty)])
            record_ids = []
            all_records = {}

            # Base query parameters
            csw_args = {
                "typenames": typenames,
                "esn": esn,
                "maxrecords": maxrecords,
                "outputschema": outputschema,
                "sortby": self.csw.sortby,
                "startposition": startposition,
                "resulttype": "results"
            }

            log.info("Making CSW request: 'getrecords2()': %s", csw_args)

            # Try first without constraints
            self.csw.getrecords2(**csw_args)
            
            if self.csw.response is None:
                log.error("No response from CSW server")
                return []

            # If we have search parameters, try with them
            if cql_query and cql_search_term:                
                # Normalize query property name
                query_property = cql_query
                if not ':' in query_property:
                    query_property = 'csw:' + query_property.capitalize()
                
                if cql_use_like:
                    search_term = f"%{cql_search_term}%"
                    constraint = PropertyIsLike(query_property, search_term)
                else:
                    constraint = PropertyIsEqualTo(query_property, cql_search_term)
                
                log.debug('Using search constraints - Query: %s, Term: %s', query_property, cql_search_term)
                csw_args["constraints"] = [constraint]
                
                # Try with constraints
                self.csw.getrecords2(**csw_args)
                
                # Log request/response for debugging
                log.debug("Matches found: %d", self.csw.results.get('matches', 0))

            elif cql:
                log.debug('Using raw CQL: %s', cql)
                csw_args["cql"] = cql
                self.csw.getrecords2(**csw_args)

            # Process results
            if self.csw.results['matches'] == 0:
                log.warning("No matches found with current query")
                # Try without constraints as fallback
                csw_args.pop("constraints", None)
                self.csw.getrecords2(**csw_args)
                if self.csw.results['matches'] == 0:
                    return []

            # Process pagination and collect records
            nextrecord = startposition
            while nextrecord is not None:
                all_records.update(self.csw.records)
                record_ids.extend(self.csw.records.keys())

                if limit and len(record_ids) >= limit:
                    break

                if (self.csw.results['returned'] > 0 and 
                    0 < self.csw.results['nextrecord'] <= self.csw.results['matches']):
                    nextrecord = self.csw.results['nextrecord']
                    csw_args["startposition"] = nextrecord
                    self.csw.getrecords2(**csw_args)
                else:
                    nextrecord = None

            # Apply limit if specified
            if limit:
                record_ids = record_ids[:limit]

            # Restore all records
            self.csw.records = all_records
            log.info('Total CSW records found: %d', len(record_ids))
            
            return record_ids

        except Exception as e:
            log.error("Error in CSW query: %s", str(e))
            if self.csw.response is not None:
                log.debug("CSW Response: %s", self.csw.response)
            if hasattr(self.csw, 'request'):
                log.debug("CSW Request: %s", self.csw.request)
            return []
        
    def get_metadata_record(self, record_id):
        """
        Gets both the parsed metadata object and raw XML for a given record ID.
        
        Args:
            record_id (str): The CSW record identifier
            
        Returns:
            tuple: (MD_Metadata, etree._Element) containing:
                - The parsed owslib.iso.MD_Metadata object
                - The XML content of the metadata record
        """
        try:
            metadata = self.csw.records[record_id]
            # Parse bytes into etree
            xml_content = metadata.xml
            return metadata, xml_content
        except Exception as e:
            log.error(f"Error getting metadata record for ID {record_id}: {str(e)}")
            raise