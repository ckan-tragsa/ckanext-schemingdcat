## Schemas
With this plugin, you can customize the group, organization, and dataset entities in CKAN. Adding and enabling a schema will modify the forms used to update and create each entity, indicated by the respective `type` property at the root level. Such as `group_type`, `organization_type`, and `dataset_type`. Non-default types are supported properly as is indicated throughout the examples.

Are available to use with this extension a number of custom schema, more info: [`schemas/README.md`](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/README.md)

**Schema Enhancements:**
We've made several improvements to our schema to provide a better metadata and metadata group management. Here are some of the key changes:

- **Form Groups:** We've introduced the use of `form_groups` and improve `form_pages` in our schemas. This allows us to group related fields into the same form, making it easier to navigate and manage metadata.
- **Metadata Management Improvements:** We've improved how we manage metadata in our schema. It's now easier to add, remove, and modify metadata, allowing us to keep our data more organized and accessible.
- **Metadata Group Updates:** We've made changes to how we handle metadata groups (`form_groups`). It's now easier to group related metadata, helping us keep our data more organized and making it easier to find specific information.

For more details on these enhancements check [Form Groups documentation](#form-groups), please refer to the schema files in [`ckanext/schemingdcat/schemas`](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas).

### GeoDCAT-AP (ES)
[`schemas/geodcat_ap/es_geodcat_ap_full`](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/geodcat_ap/es_geodcat_ap_full.yaml) with specific extensions for spatial data and [GeoDCAT-AP](https://github.com/SEMICeu/GeoDCAT-AP)/[INSPIRE](https://github.com/INSPIRE-MIF/technical-guidelines) metadata [profiles](https://en.wikipedia.org/wiki/Geospatial_metadata). 

!!! note

    RDF to CKAN dataset mapping: [GeoDCAT-AP (ES) to CKAN](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/README.md#geodcat-ap-es)


### DCAT 
[`schemas/dcat`](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/dcat/dcat_dataset.yaml) based
on: [DCAT](https://www.w3.org/TR/vocab-dcat-3/).

!!! note

    RDF to CKAN dataset mapping: [DCAT to CKAN](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/README.md#dcat)

### DCAT-AP (EU)
[`schemas/dcat_ap/eu_dcat_ap`](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/dcat_ap/eu_dcat_ap.yaml) based on: [DCAT-AP](https://op.europa.eu/en/web/eu-vocabularies/dcat-ap) for the european context.

!!! note

    RDF to CKAN dataset mapping: [DCAT-AP (EU) to CKAN](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/README.md#dcat-ap-eu)

### GeoDCAT-AP (EU)
[`schemas/geodcat_ap/eu_geodcat_ap`](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/geodcat_ap/eu_geodcat_ap.yaml) based on: [GeoDCAT-AP](https://github.com/SEMICeu/GeoDCAT-AP) for the european context.

!!! note

    RDF to CKAN dataset mapping: [GeoDCAT-AP (EU) to CKAN](https://github.com/mjanez/ckanext-schemingdcat/tree/main/ckanext/schemingdcat/schemas/README.md#geodcat-ap-eu)


### Form Groups
Form groups are a way to group related fields together in the same form. This makes it easier to navigate and manage metadata. A form group is defined with the following elements:

- `form_group_id`: A unique identifier for the form group. For example, `contact`.
- `label`: A human-readable label for the form group. This can be provided in multiple languages. For example:
    ```yaml
    label: 
      en: Contact information 
      es: Información de contacto
    ```
- `fa_icon`: An optional [Font Awesome icon](https://fontawesome.com/v4/icons/) that can be used to visually represent the form group. For example, `fa-address-book`.

Here is an example of a form group definition:

  ```yaml
  form_group_id: contact 
  label: 
    en: Contact information 
    es: Información de contacto 
  fa_icon: fa-address-book
  ```

#### Adding Fields to Form Groups
Fields can be added to a form group by specifying the `form_group_id` in the field definition. The `form_group_id` should match the `form_group_id` of the form group that the field should be part of.

Here is an example of a field that is part of the `general_info` form group:

  ```yaml
  field_name: owner_org
  label:
    en: Organization
    es: Organización
  required: True
  help_text:
    en: Entity (organisation) responsible for making the Dataset available.
    es: Entidad (organización) responsable de publicar el conjunto de datos.
  preset: dataset_organization
  form_group_id: general_info
  ```

In this example, the `owner_org` field will be part of the `general_info` form group.
