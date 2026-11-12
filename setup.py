# -*- coding: utf-8 -*-
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

version = "4.3.0"

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='''ckanext-schemingdcat''',
    version=version,
    description='''Custom CKAN schemas for DCAT vocabularies''',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='ckan',
    author="mjanez",
    url='https://github.com/mjanez/ckanext-schemingdcat',
    license='AGPL',   
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    entry_points='''
        [ckan.plugins]
        schemingdcat=ckanext.schemingdcat.plugin:SchemingDCATPlugin
        schemingdcat_datasets=ckanext.schemingdcat.plugin:SchemingDCATDatasetsPlugin
        schemingdcat_groups=ckanext.schemingdcat.plugin:SchemingDCATGroupsPlugin
        schemingdcat_organizations=ckanext.schemingdcat.plugin:SchemingDCATOrganizationsPlugin
        schemingdcat_open_data_statistics=ckanext.schemingdcat.plugin:SchemingDCATOpenDataStatisticsPlugin
        
        # Harvesters
        schemingdcat_ckan_harvester=ckanext.schemingdcat.harvesters:SchemingDCATCKANHarvester
        schemingdcat_xls_harvester=ckanext.schemingdcat.harvesters:SchemingDCATXLSHarvester
        schemingdcat_postgres_harvester=ckanext.schemingdcat.harvesters:SchemingDCATPostgresHarvester
        schemingdcat_csw_harvester=ckanext.schemingdcat.harvesters:SchemingDCATCSWHarvester
        #schemingdcat_ows_harvester=ckanext.schemingdcat.harvesters:SchemingDCATOWSHarvester     
        
        [ckan.rdf.profiles]
        # Custom compatibilty profile meant to add support for ckanext-scheming
        eu_dcat_ap_scheming=ckanext.schemingdcat.profiles:EuDCATAPSchemingDCATProfile
        
        # EU | European DCAT-AP/GeoDCAT-AP profiles
        eu_dcat_ap_2=ckanext.schemingdcat.profiles:EuDCATAP2Profile
        eu_dcat_ap_3=ckanext.schemingdcat.profiles:EuDCATAP3Profile
        eu_geodcat_ap_2=ckanext.schemingdcat.profiles:EuGeoDCATAP2Profile
        eu_geodcat_ap_3=ckanext.schemingdcat.profiles:EuGeoDCATAP3Profile
        
        # ES | Spanish NTI-RISP/DCAT profiles
        es_dcat=ckanext.schemingdcat.profiles:EsNTIRISPProfile
        es_dcat_ap_2=ckanext.schemingdcat.profiles:EsDCATAP2Profile  

        [babel.extractors]
        ckan = ckan.lib.extract:extract_ckan
    ''',
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
