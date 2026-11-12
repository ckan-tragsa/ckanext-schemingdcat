# src/ckanext-schemingdcat/ckanext/schemingdcat/signals.py
import ckan.plugins as p

# Define la señal personalizada
schemingdcat_harvest_package_updated = p.toolkit.signals.ckanext.signal('schemingdcat_harvest_package_updated')

schemingdcat_harvest_package_created = p.toolkit.signals.ckanext.signal('schemingdcat_harvest_package_created')
