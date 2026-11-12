# SchemingDCAT CLI Documentation

The `schemingdcat` command offers utilities to manage CKAN tag vocabularies and download EU vocabularies. Below are the available commands and their descriptions.

## Commands

### `schemingdcat create_inspire_tags`

Creates the INSPIRE themes vocabulary.

**Usage:**

```sh
schemingdcat create_inspire_tags [-l LANG]
```

**Options:**

- `-l, --lang`: The language for the vocabulary. Defaults to `en`

**Example:**

```sh
schemingdcat create_inspire_tags -l es
```

### `schemingdcat delete_inspire_tags`

Deletes the INSPIRE themes vocabulary.

**Usage:**

```sh
schemingdcat delete_inspire_tags
```

**Example:**

```sh
schemingdcat delete_inspire_tags
```

### `schemingdcat create_dcat_tags`

Creates the DCAT themes vocabularies.

**Usage:**

```sh
schemingdcat create_dcat_tags [-l LANG]
```

**Options:**

- `-l, --lang`: The language for the vocabularies. Defaults to `en`

**Example:**

```sh
schemingdcat create_dcat_tags -l fr
```

### `schemingdcat delete_dcat_tags`

Deletes the DCAT themes vocabularies.

**Usage:**

```sh
schemingdcat delete_dcat_tags
```

**Example:**

```sh
schemingdcat delete_dcat_tags
```

### `schemingdcat create_iso_topic_tags`

Creates the ISO 19115 topics vocabulary.

**Usage:**

```sh
schemingdcat create_iso_topic_tags [-l LANG]
```

**Options:**

- `-l, --lang`: The language for the vocabulary. Defaults to `en`
**Example:**

```sh
schemingdcat create_iso_topic_tags -l de
```

### `schemingdcat delete_iso_topic_tags`

Deletes the ISO 19115 topics vocabulary.

**Usage:**

```sh
schemingdcat delete_iso_topic_tags
```

**Example:**

```sh
schemingdcat delete_iso_topic_tags
```

### `schemingdcat download_rdf_eu_vocabs`

Downloads EU Vocabularies.

**Usage:**

```sh
schemingdcat download_rdf_eu_vocabs
```

**Example:**

```sh
schemingdcat download_rdf_eu_vocabs
```

### `schemingdcat clean_stats`

Cleans the statistics table by deleting all existing records and recreating the table. This command performs a complete reset of the statistics table used by the SchemingDCAT extension. 

It deletes all existing records to ensure a fresh state and then recreates the table schema.

**Usage:**

```sh
schemingdcat clean_stats [-v]
```

**Options:**

- `-v, --verbose`: Enable verbose output.

**Example:**

```sh
schemingdcat clean_stats -v
```

### `schemingdcat update_stats`

Cleans the statistics table by deleting all existing records and recreating the table.

**Usage:**

```sh
schemingdcat update_stats [-v]
```

**Options:**

- `-v, --verbose`: Enable verbose output.

**Example:**

```sh
schemingdcat update_stats -v
```

## Examples

### Creating INSPIRE Tags

```sh
schemingdcat create_inspire_tags -l es
```

### Deleting INSPIRE Tags

```sh
schemingdcat delete_inspire_tags
```

### Creating DCAT Tags

```sh
schemingdcat create_dcat_tags -l fr
```

### Deleting DCAT Tags

```sh
schemingdcat delete_dcat_tags
```

### Creating ISO Topic Tags

```sh
schemingdcat create_iso_topic_tags -l de
```

### Deleting ISO Topic Tags

```sh
schemingdcat delete_iso_topic_tags
```

### Downloading EU Vocabularies

```sh
schemingdcat download_rdf_eu_vocabs
```

### Cleaning Statistics Table

```sh
schemingdcat clean_stats -v
```

### Updating Statistics Table

```sh
schemingdcat update_stats -v
```

For the full list of options, check `schemingdcat <command> --help`