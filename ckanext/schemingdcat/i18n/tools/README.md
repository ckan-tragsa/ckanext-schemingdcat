# README.md
This script uses an [`input.yaml`](./input/input.yaml) YAML file to define a set of choices for a field in a form. The YAML file should follow the structure as shown in the example below:

```yaml
field_name: hvd_category
label: 
    en: High-value dataset category
    es: Categoría del conjunto de alto valor (HVD)
choices:
    - label:
        en: Meteorological
        es: Meteorología
    value: http://data.europa.eu/bna/c_164e0bf5
    - label:
        en: Companies and company ownership
        es: Sociedades y propiedad de sociedades
    value: http://data.europa.eu/bna/c_a9135398
# ... more choices ...
```

>[!WARNING]
> Make sure that field_name is not misspelled or starts with "-", otherwise it will fail.

## Field Definitions
- `field_name`: The name of the field.
- `label`: The label for the field in different languages.
- `choices`: The choices for the field. Each choice has a `label` in different languages and a `value`.

Please ensure that the YAML file is correctly formatted and all required fields are provided.

## Launch script
To run the script with `virtualenv`, follow these steps:
1. **Create and activate the virtual environment:
    ```sh
    # Install virtualenv if not already installed
    pip install virtualenv

    # Create the virtual environment
    virtualenv venv

    # Activate the virtual machine (Linux and MacOS)
    source venv/bin/activate

    # Activate virtual environment (Windows)
    .\venv/scripts/activate
    ```

2. Install the **dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

3. Run the script:
    ```sh
    python generate_translation_files.py
    ```

4. The updated i18n folder will be created with the new schema labels in: `output/{field_name}`.