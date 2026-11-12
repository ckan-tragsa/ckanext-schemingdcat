# Getting started

## Requirements
### Compatibility
Compatibility with core CKAN versions:

| CKAN version | Compatible?                                                                 |
|--------------|-----------------------------------------------------------------------------|
| 2.8          | ❌ No (>= Python 3)                                                          |
| 2.9          | ✅ Yes (<= [`v3.2.2`](https://github.com/mjanez/ckanext-schemingdcat/releases/tag/v3.2.2)) |
| 2.10         | ✅ Yes (>= [`v4.0.0`](https://github.com/mjanez/ckanext-schemingdcat/releases/tag/v4.0.0)) |

### Plugins
This plugin needs the following plugins to work properly:

  ```sh
  # Install latest stable release of:
  ## ckan/ckanext-scheming: https://github.com/ckan/ckanext-scheming/tags (e.g. release-3.0.0)
  pip install -e git+https://github.com/ckan/ckanext-scheming.git@release-3.0.0#egg=ckanext-scheming

  ## ckan/ckanext-dcat: https://github.com/ckan/ckanext-dcat/tags (e.g. 1.8.0)
  pip install -e git+https://github.com/ckan/ckanext-dcat.git@1.8.0#egg=ckanext-dcat
  pip install -r https://raw.githubusercontent.com/ckan/ckanext-dcat/master/requirements.txt

  ## ckan/ckanext-spatial: https://github.com/ckan/ckanext-spatial/tags (e.g. v2.1.1)
  pip install -e git++https://github.com/ckan/ckanext-spatial.git@v2.1.1/#egg=ckanext-spatial#egg=ckanext-spatial
  pip install -r https://raw.githubusercontent.com/ckan/ckanext-spatial/v2.1.1/requirements.txt

  ## ckan/ckanext-harvest: https://github.com/ckan/ckanext-harvest/tags (e.g. v1.5.6)
  pip install -e git++https://github.com/ckan/ckanext-harvest.git@v1.5.6#egg=ckanext-spatial
  pip install -r https://raw.githubusercontent.com/ckan/ckanext-harvest/v1.5.6/requirements.txt

  ## ckan/ckanext-fluent: https://github.com/mjanez/ckanext-fluen/tags (e.g. v1.0.1)
  pip install -e git++https://github.com/mjanez/ckanext-fluent.git@v1.0.1#egg=ckanext-fluent
  ```

## Installation
  ```sh
  cd $CKAN_VENV/src/

  # Install the scheming_dataset plugin
  pip install -e "git+https://github.com/ckan/ckanext-schemingdcat.git#egg=ckanext-schemingdcat"
  ```

## Configuration
Set the plugin:

  ```ini
  # Add the plugin to the list of plugins
  ckan.plugins = ... spatial_metadata ... dcat ... schemingdcat
  ```

!!! warning

    When using `schemingdcat` extension,**`scheming` should not appear in the list of plugins loaded in CKAN.** But `dcat` and `spatial` should.
 
### Scheming DCAT
Set the schemas you want to use with configuration options:

  ```ini
  # Each of the plugins is optional depending on your use
  ckan.plugins = schemingdcat_datasets schemingdcat_groups schemingdcat_organizations
  ```

To use CSW Endpoint in `ckanext-schemingdcat`:

  ```ini
  schemingdcat.geometadata_base_uri = http://localhost:81/csw
  ckanext.dcat.base_uri = http://localhost:81/catalog
  ```

To use custom schemas in `ckanext-scheming`:

  ```ini
  # module-path:file to schemas being used
  scheming.dataset_schemas = ckanext.schemingdcat:schemas/geodcat_ap/es_geodcat_ap_full.yaml
  scheming.group_schemas = ckanext.schemingdcat:schemas/geodcat_ap/es_geodcat_ap_group.json
  scheming.organization_schemas = ckanext.schemingdcat:schemas/geodcat_ap/es_geodcat_ap_org.json

  #   URLs may also be used, e.g:
  #
  # scheming.dataset_schemas = http://example.com/spatialx_schema.yaml

  #   Preset files may be included as well. The default preset setting is:
  scheming.presets = ckanext.schemingdcat:schemas/default_presets.json

  #   The is_fallback setting may be changed as well. Defaults to false:
  scheming.dataset_fallback = false
  ```

### Harvest
Add the [custom Harvesters](./feature-harvesters.md) to the list of plugins as you need:

  ```ini
  ckan.plugins = ... spatial_metadata ... dcat ... schemingdcat ... harvest ... schemingdcat_ckan_harvester schemingdcat_csw_harvester ...
  ```

### Endpoints
You can update the [`endpoints.yaml`](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/codelists/endpoints.yaml) file to add your custom OGC/LOD endpoints, only has 2 types of endpoints: `lod` and `ogc`, and the `profile` avalaible in [`ckanext-dcat`](https://github.com/ckan/ckanext-dcat) Preferably between 4 and 8.

Examples:

* LOD endpoint: A Linked Open Data endpoint is a DCAT endpoint that provides access to RDF data. More information about the catalogue endpoint, how to use the endpoint, (e.g. `https://{ckan-instance-host}/catalog.{format}?[page={page}]&[modified_since={date}]&[profiles={profile1},{profile2}]&[q={query}]&[fq={filter query}]`, and more at [`ckanext-dcat`](https://github.com/ckan/ckanext-dcat?tab=readme-ov-file#catalog-endpoint)
    ```yaml
    - name: eu_dcat_ap_2_rdf
      display_name: RDF DCAT-AP 2
      type: lod
      format: rdf
      image_display_url: /images/icons/endpoints/eu_dcat_ap.svg
      endpoint_icon: /images/endpoints/catalog-rdf-eu.png
      fa_icon: fa-share-alt
      description: RDF DCAT-AP 2.1.1 Endpoint for european data portals.
      profile: eu_dcat_ap_2,eu_dcat_ap_scheming
      profile_id: dcat_ap
      profile_label: DCAT-AP 2
      profile_label_order: 1
      profile_info_url: https://joinup.ec.europa.eu/collection/semic-support-centre/solution/dcat-application-profile-data-portals-europe
      version: 2.1.1
    ```

* OGC Endpoint: An OGC CSW endpoint provides a standards-based interface to discover, browse, and query metadata about spatial datasets and data services. More info about the endpoint at [OGC: Catalogue Service](https://www.ogc.org/)standard/cat/
    ```yaml
    - name: csw_inspire
      display_name: CSW INSPIRE-3.0.0
      type: ogc
      format: xml
      image_display_url: /images/icons/endpoints/csw_inspire.svg
      endpoint_icon: /images/endpoints/catalog-csw-eu.png
      fa_icon: fa-globe
      description: OGC-INSPIRE Endpoint for spatial metadata.
      profile: csw
      profile_id: inspire
      profile_label: INSPIRE
      profile_label_order: 0
      profile_info_url: https://inspire.ec.europa.eu/metadata/6541
      version: 3.0.0
    ```

* Other endpoints, like `ckan` or `sparql`:
    ```yaml
    - name: sparql
      display_name: SPARQL
      type: sparql
      format: sparql
      image_display_url: /images/icons/endpoints/w3c.svg
      endpoint_icon: /images/endpoints/catalog-sparql.png
      fa_icon: fa-share-alt
      description: SPARQL Endpoint for querying RDF data.
      profile: sparql
      profile_id: sparql
      profile_label: SPARQL
      profile_label_order: 5
      profile_info_url: https://wwwhttps://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/.w3.org/TR/sparql11-overview/
      version: 1.1

    - name: ckan
      display_name: CKAN API
      type: ckan
      format: json
      image_display_url: /images/icons/endpoints/global.svg
      endpoint_icon: /images/endpoints/catalog-ckan.png
      fa_icon: fa-cogs
      description: CKAN’s Action API is a powerful RPC-style API.
      profile: ckan
      profile_id: ckan_api
      profile_label: CKAN-API
      profile_label_order: 4
      profile_info_url: https://docs.ckan.org/en/latest/api/index.html
      version: 3
    ```

### Facet Scheming
To configure facets, there are no mandatory sets in the config file for this extension. The following sets can be used:

  ```ini
  schemingdcat.facet_list: [list of fields]      # List of fields in scheming file to use to faceting. Use ckan defaults if not provided.
  schemingdcat.default_facet_operator: [AND|OR]  # OR if not defined

   schemingdcat.icons_dir: (dir)                  # images/icons if not defined
  ```

As an example for facet list, we could suggest:

  ```ini
  schemingdcat.facet_list = "theme groups theme_es dcat_type owner_org res_format publisher_name publisher_type frequency tags tag_uri conforms_to spatial_uri"
  ```

The same custom fields for faceting can be used when browsing organizations and groups data:

  ```ini
  schemingdcat.organization_custom_facets = true
  schemingdcat.group_custom_facets = true
  ```

This two last settings are not mandatory. You can omit one or both (or set them to `false`), and the default fields for faceting will be used instead.

#### Facet Scheming integration with Solr
1. Clear the index in solr:

    `ckan -c [route to your .ini ckan config file] search-index clear`
   
2. Modify the schema file on Solr (schema or managed schema) to add the multivalued fields added in the scheming extension used for faceting. You can add any field defined in the schema file used in the ckanext-scheming extension that you want to use for faceting.
   You must define each field with these parameters:
   - `type: string` - to avoid split the text in tokens, each individually "faceted".
   - `uninvertible: false` - as recomended by solr´s documentation 
   - `docValues: true` - to ease recovering faceted resources
   - `indexed: true` - to let ckan recover resources under this facet 
   - `stored: true` - to let the value to be recovered by queries
   - `multiValued`: well... it depends on if it is a multivalued field (several values for one resource) or a regular field (just one value). Use "true" or "false" respectively. 
   
   E.g. [`ckanext-iepnb`](https://github.com/OpenDataGIS/ckanext-iepnb) extension are ready to use these multivalued fields. You have to add this configuration fragment to solr schema in order to use them:
    
  ```xml
    <!-- Extra fields -->
    <field name="tag_uri" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
    <field name="conforms_to" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
    <field name="lineage_source" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
    <field name="lineage_process_steps" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
    <field name="reference" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
    <field name="theme" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
    <field name="theme_es" type="string" uninvertible="false" docValues="true" multiValued="true" indexed="true" stored="true"/>
    <field name="metadata_profile" type="string" uninvertible="false" docValues="true" multiValued="true" indexed="true" stored="true"/>
    <field name="resource_relation" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
  ```

!!! note

    You can ommit any field you're not going to use for faceting, but the best policy could be to add all values at the beginning. 
    
    The extra fields depend on your [schema](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/)
    
    **Be sure to restart Solr after modify the schema.**
    
3. Restart CKAN. 
     
4. Reindex solr index:

    `ckan -c [route to your .ini ckan config file] search-index rebuild-fast`

    Sometimes solr can issue an error while reindexing. In that case I'd try to restart solr, delete index ("search-index clear"), restart solr, rebuild index, and restart solr again.
    
    Ckan needs to "fix" multivalued fields to be able to recover values correctly for faceting, so this step must be done in order to use faceting with multivalued fields. 

### Icons
Icons for each field option in the [`scheming file`](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/geodcat_ap/es_geodcat_ap_full.yaml) can be set in multiple ways:

- Set a root directory path for icons for each field using the `icons_dir` key in the scheming file.
- If `icons_dir` is not defined, the directory path is guessed starting from the value provided for the `schemingdcat.icons_dir` parameter in the CKAN config file, adding the name of the field as an additional step to the path (`public/images/icons/{field_name`).
- For each option, use the `icon` setting to provide the last steps of the icon path from the field's root path defined before. This value may be just a file name or include a path to add to the icon's root directory.
- If `icon` is not used, a directory and file name are guessed from the option's value.
- Icons files are tested for existence when using `schemingdcat_schema_icon` function to get them. If the file doesn't exist, the function returns `None`. Icons can be provided by any CKAN extension in its `public` directory.
- Set a `default icon` for a field using the default_icon setting in the scheming file. You can get it using `schemingdcat_schema_get_default_icon` function, and it is your duty to decide when and where to get and use it in a template.
