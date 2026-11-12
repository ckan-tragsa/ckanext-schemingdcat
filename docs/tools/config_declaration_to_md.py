import yaml
from pathlib import Path
from jinja2 import Template

# Resolve the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent   # Adjust as needed

# Use the base directory to resolve the config path
CONFIG_YAML_PATH = BASE_DIR / 'ckanext/schemingdcat/config_declaration.yml'

# Defines the output folder and the output Markdown file
OUTPUT_DIR = Path(__file__).parent / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_MD_PATH = OUTPUT_DIR / 'configuration.md'


def load_config_yaml(file_path: Path) -> dict:
    """
    Loads a YAML configuration file.

    Args:
        file_path (Path): Path to the YAML file.

    Returns:
        dict: Parsed YAML content as a dictionary.
    """
    with file_path.open('r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def render_markdown(config: dict) -> str:
    """
    Renders a Markdown string from the given configuration using a Jinja2 template.

    Args:
        config (dict): Configuration dictionary to render.

    Returns:
        str: Rendered Markdown content.
    """
    markdown_template = Template("""
<!-- start-config -->

{% for group in config.groups %}
### {{ group.annotation }}

{% for option in group.options %}
#### {{ option.key }}

{% if option.example %}
Example:

    {{ option.example | replace('"', '\"') | replace("'", "\'") }}

{% endif %}

{% if option.default %}
Default value: `{{ option.default }}`
{% elif option.default_callable %}
Default callable: `{{ option.default_callable }}`
{% endif %}

{{ option.description }}

{% endfor %}
{% endfor %}
<!-- end-config -->
""")
    return markdown_template.render(config=config)

def save_markdown(content: str, file_path: Path) -> None:
    """
    Saves the rendered Markdown content to a file.

    Args:
        content (str): Rendered Markdown content.
        file_path (Path): Output file path for saving the content.
    """
    with file_path.open('w', encoding='utf-8') as file:
        file.write(content)


def main():
    """
    Main function to load YAML configuration, render it to Markdown, and save the output.

    This function performs the following steps:
    1. Load configuration from a YAML file.
    2. Render the configuration to a Markdown format.
    3. Save the rendered Markdown to a file.
    """
    config = load_config_yaml(CONFIG_YAML_PATH)
    markdown_content = render_markdown(config)
    save_markdown(markdown_content, OUTPUT_MD_PATH)


if __name__ == '__main__':
    main()