import logging
from ckanext.schemingdcat.harvesters.csw import SchemingDCATCSWHarvester

log = logging.getLogger(__name__)


# TODO: Adapt SchemingDCATCSWHarvester to using OWS (OGC Web Services/Geoserver) instead of CSW
class SchemingDCATOWSHarvester(SchemingDCATCSWHarvester):
    '''
    An expanded Harvester for OWS servers like Geoserver
    '''
    
    def info(self):
        return {
            'name': 'schemingdcat_ows',
            'title': 'Scheming DCAT OWS Server endpoint',
            'description': 'Harvester for OWS Servers like Geoserver to generate INSPIRE-GeoDCAT-AP dataset descriptions ' +
                           'serialized as XML metadata according to the INSPIRE ISO 19139 standard.',
            'about_url': 'https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#schemingdcat-ows-harvester'
        }
    
    pass 