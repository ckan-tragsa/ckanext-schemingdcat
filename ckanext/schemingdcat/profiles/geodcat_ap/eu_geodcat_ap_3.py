import json
from decimal import Decimal, DecimalException

from rdflib import URIRef, BNode, Literal

from ckanext.dcat.utils import resource_uri
from ckanext.dcat.profiles.base import URIRefOrLiteral, CleanedURIRef

from ckanext.schemingdcat.profiles.base import (
    # Codelists
    MD_INSPIRE_REGISTER,
    MD_FORMAT,
    MD_EU_LANGUAGES,
)

from ckanext.schemingdcat.profiles.dcat_ap.eu_dcat_ap_3 import EuDCATAP3Profile
from ckanext.schemingdcat.profiles.geodcat_ap.eu_geodcat_ap_2 import EuGeoDCATAP2Profile
from ckanext.schemingdcat.profiles.eu_dcat_ap_scheming import EuDCATAPSchemingDCATProfile
from ckanext.schemingdcat.profiles.dcat_config import (
    # Vocabs
    RDF,
    DCAT,
    DCATAP,
    GEODCATAP,
    VCARD,
    DCT,
    XSD,
    SCHEMA,
    RDFS,
    ADMS,
    CNT,
    ELI,
    # Default values
    metadata_field_names,
    eu_geodcat_ap_default_values,
    )

#TODO: Implement GeoDCAT-AP 3 profile
class EuGeoDCATAP3Profile(EuGeoDCATAP2Profile, EuDCATAP3Profile, EuDCATAPSchemingDCATProfile):
    """
    A custom RDF profile based on the GeoDCAT-AP 3 for data portals in Europe

    More information and specification:

    https://joinup.ec.europa.eu/collection/semic-support-centre/solution/geodcat-application-profile-data-portals-europe

    """

    def parse_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        dataset_dict = self._parse_dataset_base(dataset_dict, dataset_ref)

        # DCAT AP v2 properties also applied to higher versions
        dataset_dict = self._parse_dataset_v2(dataset_dict, dataset_ref)

        # DCAT AP v2 scheming fields
        dataset_dict = self._parse_dataset_v2_scheming(dataset_dict, dataset_ref)

        # GeoDCAT-AP 2 properties
        dataset_dict = self._parse_dataset_geodcat_ap_v2(dataset_dict, dataset_ref)

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        self._graph_from_dataset_base(dataset_dict, dataset_ref)

        # DCAT AP v2 properties also applied to higher versions
        self._graph_from_dataset_v2(dataset_dict, dataset_ref)

        # DCAT AP v2 scheming fields
        self._graph_from_dataset_v2_scheming(dataset_dict, dataset_ref)

        # GeoDCAT-AP 2 properties
        self._graph_from_dataset_geodcat_ap_v2(dataset_dict, dataset_ref)

        # DCAT AP v3 properties also applied to higher versions
        self._graph_from_dataset_v3(dataset_dict, dataset_ref)

        # GeoDCAT-AP 3 properties
        self._graph_from_dataset_geodcat_ap_v3(dataset_dict, dataset_ref)


    def graph_from_catalog(self, catalog_dict, catalog_ref):
        
        # Call base method for common properties
        self._graph_from_catalog_base(catalog_dict, catalog_ref)
        
        # GeoDCAT-AP 2 Catalog properties
        self._graph_from_catalog_geodcat_ap_v2(catalog_dict, catalog_ref)

    #TODO: Implement GeoDCAT-AP 3
    def _graph_from_dataset_geodcat_ap_v3(self, dataset_dict, dataset_ref):
        pass