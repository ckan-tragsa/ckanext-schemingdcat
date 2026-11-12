# ckanext-schemingdcat. LOD/INSPIRE metadata enhancement for ckanext-scheming/dcat


[![Tests](https://github.com/mjanez/ckanext-schemingdcat/actions/workflows/test.yml/badge.svg)](https://github.com/mjanez/ckanext-schemingdcat/actions)


Ckanext-dcat is a [CKAN](https://github.com/ckan/ckan) extension that helps data publishers expose and consume metadata as serialized RDF documents using [DCAT](https://github.com/ckan/ckan).

This CKAN extension provides functions and templates specifically designed to extend `ckanext-scheming` and `ckanext-dcat` and includes RDF profiles and Harvest enhancements to adapt CKAN Schema to multiple metadata profiles as: [GeoDCAT-AP](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/geodcat_ap/es_geodcat_ap_full.yaml) or [DCAT-AP](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/dcat_ap/eu_dcat_ap_full.yaml).

!!! warning

    This project requires [ckan/ckanext-dcat](https://github.com/ckan/ckanext-dcat) (for newer releases) or [ckan/ckanext-dcat](https://github.com/ckan/ckanext-dcat) (older), along with [ckan/ckanext-scheming](https://github.com/ckan/ckanext-scheming) and [ckan/ckanext-spatial](https://github.com/ckan/ckanext-spatial) to work properly. If you want to use custom schemas with multilingual support, you need to use `ckanext-fluent`. A fixed version is available at [mjanez/ckanext-fluent](https://github.com/mjanez/ckanext-fluent).

!!! tip
    
    It is **recommended to use with:** [`ckan-docker`](https://github.com/mjanez/ckan-docker) deployment or only use [`ckan-pycsw`](https://github.com/mjanez/ckan-pycsw) to deploy a CSW Catalog.

![image](https://github.com/mjanez/ckanext-schemingdcat/raw/main/doc/img/schemingdcat_home.png)

Enhancements:

- Custom schemas for `ckanext-scheming` in the plugin like [CKAN GeoDCAT-AP custom schemas](https://github.com/mjanez/ckanext-schemingdcat/blob/main/ckanext/schemingdcat/schemas/README.md)

- [`ckanext-dcat` profiles](./v1/feature-profiles.md) for RDF serialization according to profiles such as DCAT, DCAT-AP, GeoDCAT-AP and in the Spanish context, NTI-RISP.

- Improve metadata management forms to include tabs that make it easier to search metadata categories and simplify metadata editing.

- Improve the search functionality in CKAN for custom schemas. It uses the fields defined in a scheming file to provide a set of tools to use these fields for scheming, and a way to include icons in their labels when displaying them. More info: [`ckanext-schemingdcat`](https://github.com/mjanez/ckanext-schemingdcat)

- Add improved harvesters for custom metadata schemas integrated with `ckanext-harvest` in CKAN using [`mjanez/ckan-ogc`](https://github.com/mjanez/ckan-ogc).

- Add Metadata downloads for Linked Open Data formats ([`ckan/ckanext-dcat`](https://github.com/ckan/ckanext-dcat)) and Geospatial Metadata (ISO 19139, Dublin Core, etc. with [`mjanez/ckan-pycsw`](https://github.com/mjanez/ckanext-pycsw))

- Add custom i18n translations to `datasets`, `groups`, `organizations` in schemas, e.g: [GeoDCAT-AP (ES)](./v1/feature-schemas.md#geodcat-ap-es), and improvement multilang extension. [^1]

- Add a set of useful helpers and templates to be used with Metadata Schemas.

- [Update the base theme](./v1/feature-new-theme.md) of CKAN to use with the enhancements of this extension, now using Tabs instead of older `stages`.

- Modern UI inspired on [`datopian/ckanext-datopian`](https://github.com/datopian/ckanext-datopian).

- LOD/OGC Endpoints based on avalaible profiles (DCAT) and CSW capabilities with [`mjanez/ckan-pycsw`](https://github.com/mjanez/ckanext-pycsw).


[^1]: An improvement to [`ckanext-fluent`](https://github.com/ckan/ckanext-fluent) to allow more versatility in multilingual schema creation and metadata validation.