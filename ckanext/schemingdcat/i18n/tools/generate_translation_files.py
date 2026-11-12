import yaml
from urllib.parse import urlparse
import os
import shutil

def get_ckanext_directory():
    # Get the absolute path of the script
    script_path = os.path.abspath(__file__)
    
    # Split the path into components
    path_components = script_path.split(os.sep)
    
    # Find the index of the 'ckanext-*' component
    ckanext_index = next(i for i, component in enumerate(path_components) if component.startswith('ckanext-'))
    
    # Return the 'ckanext-*' component
    return path_components[ckanext_index]

def append_to_file(file_path, data, lang=None):
    """
    Appends translation data to a file.

    Args:
        file_path (str): The path to the file.
        data (dict): The translation data.
        lang (str, optional): The language of the translation. Defaults to None.
    """
    field_name = data["field_name"]
    with open(f'./output/{field_name}/{file_path}', 'a') as file:
        # Check if "label" and "en" keys exist in data
        if "label" in data and "en" in data["label"]:
            file.write(f'\n\n# {data["label"]["en"]} - Schema field_name: {data["field_name"]}\n')
        else:
            file.write(f'\n\n# Schema field_name: {data["field_name"]}\n')
        for choice in data['choices']:
            value = extract_value(choice['value'])
            file.write(f'msgid "{value}"\n')  # Add a newline at the beginning
            if lang:
                label = choice['label'].get(lang, '')
                file.write(f'msgstr "{label}"\n\n')
            else:
                file.write('msgstr ""\n\n')

def read_yaml(file_path):
    """
    Reads a YAML file.

    Args:
        file_path (str): The path to the file.

    Returns:
        dict: The data from the YAML file.
    """
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def extract_value(value):
    """
    Extracts the value from a URL.

    Args:
        value (str): The URL.

    Returns:
        str: The extracted value.
    """
    if value.startswith('http'):
        return urlparse(value).path.split('/')[-1]
    return value

def write_to_file(file_path, data, lang=None):
    """
    Writes translation data to a file.

    Args:
        file_path (str): The path to the file.
        data (dict): The translation data.
        lang (str, optional): The language of the translation. Defaults to None.
    """
    field_name = data["field_name"]
    os.makedirs(f'output/{field_name}', exist_ok=True)
    with open(f'output/{field_name}/{file_path}', 'w') as file:
        # Check if "label" and "en" keys exist in data
        if "label" in data and "en" in data["label"]:
            file.write(f'# {data["label"]["en"]} - Schema field_name: {data["field_name"]}\n')
        else:
            file.write(f'# Schema field_name: {data["field_name"]}\n')
        for choice in data['choices']:
            value = extract_value(choice['value'])
            file.write(f'msgid "{value}"\n')
            if lang:
                label = choice['label'].get(lang, '')
                file.write(f'msgstr "{label}"\n\n')
            else:
                file.write('msgstr ""\n\n')

def create_directories(langs, field_name):
    """
    Creates directories for each language.

    Args:
        langs (list): The list of languages.
        field_name (str): The field name.
    """
    for lang in langs:
        os.makedirs(f'output/{field_name}/{lang}/LC_MESSAGES', exist_ok=True)

def get_languages(data):
    """
    Gets the languages from the data.

    Args:
        data (dict): The translation data.

    Returns:
        set: The set of languages.
    """
    return set(lang for choice in data['choices'] for lang in choice['label'])

def main():
    # Change working directory to the location of this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    data = read_yaml('input/input.yaml')
    field_name = data["field_name"]
    langs = get_languages(data)
    create_directories(langs, field_name)

    directory = get_ckanext_directory()
    for lang in langs:
        # Copy existing file to output directory
        shutil.copy(f'../{lang}/LC_MESSAGES/{directory}.po', f'./output/{field_name}/{lang}/LC_MESSAGES/{directory}.po')
        append_to_file(f'{lang}/LC_MESSAGES/{directory}.po', data, lang)
    # Copy existing .pot file to output directory
    shutil.copy(f'../{directory}.pot', f'./output/{field_name}/{directory}.pot')
    append_to_file(f'{directory}.pot', data)

if __name__ == "__main__":
    main()