
<!-- start-config -->


### General settings


#### ckanext.schemingdcat.icons_dir


Example:

    my-custom-plugin-folder/icons




Default value: `images/icons`


Path to the default directory for custom icons.



#### ckanext.schemingdcat.default_package_item_icon


Example:

    my_custom_theme




Default value: `theme`


Default category icon for packages, a specific field in the schemingdcat dataset (`field_name`) by default `theme` (INSPIRE Themes), can be changed to other thematic categories as `theme_es`, `theme_eu`, etc. 



#### ckanext.schemingdcat.default_package_item_show_spatial




Default value: `True`


Display spatial information on package elements by default. Is used to retrieve the configuration value that determines whether the spatial information should be shown in the default package item.



#### ckanext.schemingdcat.show_metadata_templates_toolbar





Determines whether the metadata templates toolbar should be shown or not.



#### ckanext.schemingdcat.metadata_templates_search_identifier


Example:

    my-org_template




Default value: `schemingdcat_xls-template`


Identifier used to search for packages that are metadata templates, used in schemingdcat schemas field `schemingdcat_xls_metadata_template`.



#### ckanext.schemingdcat.form_tabs_allowed




Default value: `True`


Use form tabs in the package forms to group the fields into different tabs.



#### ckanext.schemingdcat.endpoints_yaml


Example:

    ckanext.myplugin:codelists/endpoints.yaml




Default value: `endpoints.yaml`


The module path to the YAML file that contains the endpoint configurations. Like `module:file.yaml`. See https://github.com/mjanez/ckanext-schemingdcat#endpoints for more details.



#### ckanext.schemingdcat.geometadata_base_uri


Example:

    https://demo.pycsw.org/cite/csw




Default value: `/csw`


Base URI for spatial CSW Endpoint. By default `/csw` is used, provided it is used in the same instance as [`ckan-pycsw`](https://github.com/mjanez/ckan-pycsw).




### API settings


#### ckanext.schemingdcat.api.private_fields





List of fields that should not be exposed in the API actions like `package_show`, `package_search` `resource_show`, etc.



#### ckanext.schemingdcat.api.private_fields_roles




Default value: `['admin', 'editor', 'member']`


List of members that has access to private_fields. By default members of the organization with the role `admin`, `editor` and `member` have access to private fields.




### Facet settings


#### ckanext.schemingdcat.default_facet_operator




Default callable: `ckanext.schemingdcat.helpers:schemingdcat_default_facet_search_operator`


Sets the default operator for faceted searches. Only accepts `AND` or `OR`. Default: `OR`.



#### ckanext.schemingdcat.organization_custom_facets




Default value: `True`


Enables custom facets for organizations.



#### ckanext.schemingdcat.group_custom_facets




Default value: `True`


Enables custom facets for groups.




### Open Data stats settings


#### ckanext.schemingdcat.open_data_intro_enabled





Enables site description on the homepage of the portal.



#### ckanext.schemingdcat.open_data_statistics




Default value: `True`


Enable open data statistics on the homepage of the portal.



#### ckanext.schemingdcat.open_data_statistics_themes




Default value: `True`


Enables open data statistics for themes on the homepage of the portal.
`theme` field are defined by: `ckanext.schemingdcat.default_package_item_icon`



#### ckanext.schemingdcat.dcat_ap.publisher.name




Default value: `Organismo publicador del Catálogo`


A party that makes a dataset available to others.



#### ckanext.schemingdcat.dcat_ap.publisher.identifier




Default value: `http://datos.gob.es/recurso/sector-publico/org/Organismo/EA0000000`


Unique identifier of the publisher. Spain: Unique identifier (DIR3) of the public organization ([datos.gob.es](http://datos.gob.es/es/recurso/sector-publico/org/Organismo)).



#### ckanext.schemingdcat.dcat_ap.publisher.email




Default value: `organismo@example.org`


Email of the publisher



#### ckanext.schemingdcat.dcat_ap.publisher.type




Default value: `http://purl.org/adms/publishertype/NonProfitOrganisation`


Type of the publisher. [Publisher Type Codelist](http://purl.org/adms/publishertype)



#### ckanext.schemingdcat.dcat_ap.publisher.url




Default value: `https://organismo.example.org/`


Website of the publisher



#### ckanext.schemingdcat.dcat_ap.datastore_dataservice.title




Default value: `Datastore API service`


Title of the Datastore API service.



#### ckanext.schemingdcat.dcat_ap.datastore_dataservice.description




Default value: `This API provides live access to the Datastore portion of the Open Data Portal. Serve data resources in a machine-readable format.`


Description of the Datastore API service.



#### ckanext.schemingdcat.dcat_ap.datastore_dataservice.endpoint_description




Default value: `{ckan_site_url}/openapi/datastore/`


URI of the Datastore OpenAPI or online documentation.




### Social settings


#### ckanext.schemingdcat.social_github




Default value: `https://github.com/mjanez/ckanext-schemingdcat`


URL of your GitHub profile.



#### ckanext.schemingdcat.social_linkedin




Default value: `https://www.linkedin.com/company/ckanproject`


URL of your LinkedIn profile.



#### ckanext.schemingdcat.social_x




Default value: `https://x.com/ckanproject`


URL of your X (formerly Twitter) profile.




### SchemingDCATSQLHarvester settings


#### ckanext.schemingdcat.postgres.geojson_chars_limit




Default value: `1000`


Number of limit using in SchemingDCATSQLHarvester to select data from a specified column. For GeoJSON data, if the data length exceeds, the expression returns NULL to avoid performance issues with large GeoJSON objects.



#### ckanext.schemingdcat.postgres.geojson_tolerance




Default callable: `ckanext.schemingdcat.helpers:schemingdcat_validate_float`


For geographic columns, it applies a transformation to the EPSG:4326 coordinate system and simplifies the geometry based on a tolerance value. Default: `0.001`




<!-- end-config -->