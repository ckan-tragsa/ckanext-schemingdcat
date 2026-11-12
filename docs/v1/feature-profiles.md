## DCAT Profiles
This plugin also contains a custom [`ckanext-dcat` profiles](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/profiles) to serialize a CKAN dataset to a:

**European context**:
* [DCAT-AP v2.1.1](https://semiceu.github.io/DCAT-AP/releases/2.1.1) (default): `eu_dcat_ap_2`
* [GeoDCAT-AP v2.0.0](https://semiceu.github.io/GeoDCAT-AP/releases/2.0.0): `eu_geodcat_ap_2`
* [GeoDCAT-AP v3.0.0](https://semiceu.github.io/GeoDCAT-AP/releases/3.0.0): `eu_geodcat_ap_3`

**Spanish context**:
* Spain [NTI-RISP v1.0.0](https://datos.gob.es/es/documentacion/normativa-de-ambito-nacional): `es_dcat`
* Spain [DCAT-AP v2.1.1](https://semiceu.github.io/DCAT-AP/releases/2.1.1): `es_dcat_ap_2`
* Spain [GeoDCAT-AP v2.0.0](https://semiceu.github.io/GeoDCAT-AP/releases/2.0.0): `es_geodcat_ap_2`

To define which profiles to use you can:

1. Set the `ckanext.dcat.rdf.profiles` configuration option on your CKAN configuration file:

    ckanext.dcat.rdf.profiles = eu_dcat_ap_2 es_dcat eu_geodcat_ap_2

2. When initializing a parser or serializer class, pass the profiles to be used as a parameter, eg:

```python

   parser = RDFParser(profiles=['eu_dcat_ap_2', 'es_dcat', 'eu_geodcat_ap_2'])

   serializer = RDFSerializer(profiles=['eu_dcat_ap_2', 'es_dcat', 'eu_geodcat_ap_2'])
```

Note that in both cases the order in which you define them is important, as it will be the one that the profiles will be run on.

### Multilingual RDF support
To add multilingual values from CKAN to RDF, the [`SchemingDCATRDFProfile` method `_object_value](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/profiles/base.py)` can be called with optional parameter `multilang=true` (defaults to `false`)). 
If `_object_value` is called with the `multilang=true`-parameter, but no language-attribute is found, the value will be added as Literal with the default language (en).

!!! tip

    The custom `ckanext-dcat` profiles have multi-language compatibility, see the ckanext-dcat documentation for more information on [writing custom profiles](https://github.com/ckan/ckanext-dcat?tab=readme-ov-file#writing-custom-profiles).

Example RDF:
```xml
<dct:title xml:lang="en">Dataset Title (EN)</dct:title>
<dct:title xml:lang="de">Dataset Title (DE)</dct:title>
<dct:title xml:lang="fr">Dataset Title (FR)</dct:title>
```
```json
{
    "title":
        {
            "en": "Dataset Title (EN)",
            "de": "Dataset Title (DE)",
            "fr": "Dataset Title (FR)"
        }
}
```

Example with missing language in RDF:
```xml
<dct:title>Dataset Title</dct:title>
```
```json
{
    "title":
        {
            "en": "Dataset Title"
        }
}
```
