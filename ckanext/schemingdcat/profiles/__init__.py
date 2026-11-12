# Custom ckanext-dcat EuropeanDCATAPSchemingProfile
from .eu_dcat_ap_scheming import EuDCATAPSchemingDCATProfile

# NTI-RISP Profile (Spanish custom DCAT profile of datos.gob.es) https://datos.gob.es/es/doc-tags/nti-risp
from .dcat.es_dcat import EsNTIRISPProfile

# DCAT-AP Profiles
from .dcat_ap.eu_dcat_ap_2 import EuDCATAP2Profile
from .dcat_ap.eu_dcat_ap_3 import EuDCATAP3Profile
from .dcat_ap.es_dcat_ap_2 import EsDCATAP2Profile

# GeoDCAT-AP Profiles
from .geodcat_ap.eu_geodcat_ap_2 import EuGeoDCATAP2Profile
from .geodcat_ap.eu_geodcat_ap_3 import EuGeoDCATAP3Profile


__all__ = [
    # Custom compatibilty profile meant to add support for ckanext-scheming 
    'EuDCATAPSchemingDCATProfile',
    
    # DCAT-AP profiles
    'EuDCATAP2Profile',
    'EuDCATAP3Profile',
    
    # GeoDCAT-AP profiles
    'EuGeoDCATAP2Profile',
    'EuGeoDCATAP3Profile',
    
    # Spanish profiles
    'EsNTIRISPProfile',
    'EsDCATAP2Profile',
]