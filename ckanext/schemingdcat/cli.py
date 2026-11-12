# -*- coding: utf-8 -*-

from __future__ import print_function

import ckantoolkit as tk
import click
import logging
import requests

import ckanext.schemingdcat.utils as utils

import ckanext.schemingdcat.config as sdct_config
import ckanext.scheming.helpers as sh
import ckanext.schemingdcat.helpers as helpers
import ckanext.schemingdcat.statistics.model as model

from ckanext.schemingdcat.profiles.dcat_config import (
    EU_VOCABS_DIR,
    EU_VOCABULARIES,
    headers,  
    )
from ckanext.schemingdcat.codelists import (
    BasicRdfFile,
    LicenseRdfFile,
    FileTypesRdfFile,
    MediaTypesRdfFile
    )

log = logging.getLogger(__name__)


def get_commands():
    return [schemingdcat]

@click.group()
def schemingdcat():
    """
    This is the main entry point for the CLI. It groups all the schemingdcat commands together.
    """
    pass
   
def create_vocab(vocab_name, schema_name="dataset", lang="en"):
    """
    This function creates a CKAN tag vocabulary and adds configured INSPIRE themes to it.

    Parameters:
    vocab_name (str): The name of the vocabulary to be created.
    schema_name (str, optional): The name of the schema. Defaults to "dataset".
    lang (str, optional): The language for the vocabulary. Defaults to "en".

    The function first retrieves the site user and the list of vocabularies. It checks if the
    vocabulary already exists. If it does, it skips the creation step. If it doesn't, it creates a new vocabulary.

    Then, it retrieves the dataset schema and checks if the vocabulary field exists. If it
    does, it iterates over the field choices. For each choice, it checks if the tag already
    exists in the vocabulary. If it doesn't, it creates a new tag.

    This function can be safely called multiple times. It will only create the vocabulary and
    tags once.

    Returns:
    None
    """
    log.info(
        "Creating '{0}' CKAN tag vocabulary and adding configured INSPIRE themes to it...".format(
            vocab_name
        )
    )

    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}
    vocab_list = tk.get_action("vocabulary_list")(context)
    for voc in vocab_list:
        if voc["name"] == vocab_name:
            vocabulary = voc
            log.info(
                "Vocabulary '{0}' already exists, skipping creation...".format(
                    vocab_name
                )
            )
            break
    else:
        log.info(
            "Creating vocabulary {0}...".format(
                vocab_name
            )
        )
        vocabulary = tk.get_action("vocabulary_create")(
            context, {"name": vocab_name}
        )

    schema = helpers.schemingdcat_get_dataset_schema(schema_name)
    vocab_field = next((field for field in schema["dataset_fields"] if field['field_name'] == vocab_name), None)

    #log.debug(sh.scheming_field_choices(vocab_field))
    if vocab_field:
        for tag_name in sh.scheming_field_choices(vocab_field):
            if tag_name['value'] != "":
                vocab_value = helpers.get_ckan_cleaned_name(tag_name['value'].split('/')[-1])
                vocab_label = sh.scheming_language_text(tag_name['label'], lang)
                already_exists = vocab_value in [tag["name"] for tag in vocabulary["tags"]]
                if not already_exists:
                    log.info(
                        "Adding tag '{0}' and label to vocabulary {1}...".format(
                            vocab_value,
                            vocab_name
                        )
                    )
                    tk.get_action("tag_create")(
                        context, {"name": vocab_value, "vocabulary_id": vocabulary["id"]}
                    )
                else:
                    log.info(
                        "Tag '{0}' is already part of the {1} vocabulary, skipping...".format(
                            vocab_value,
                            vocab_name
                        )
                    )
        click.secho(f"{vocab_name} created!", fg="green")
        
    else:
        log.warning(
            "No field {0} in schema: {1}".format(
                vocab_name,
                schema_name
            )
        )

def delete_vocab(vocab_name):
    """
    This function deletes a CKAN tag vocabulary and its respective tags.

    Parameters:
    vocab_name (str): The name of the vocabulary to be deleted.

    The function first retrieves the site user and the list of vocabularies. It checks if the
    vocabulary exists. If it does, it logs a message and retrieves the tags in the vocabulary.

    For each tag, it logs a message and deletes the tag. After all tags have been deleted, it
    logs a message and deletes the vocabulary.

    If the vocabulary does not exist, it logs a message and does nothing.

    This function can be safely called even if the vocabulary does not exist. It will not
    raise an error in this case.

    Returns:
    None
    """
    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}
    vocabulary_list = tk.get_action("vocabulary_list")(context)
    if vocab_name in [voc["name"] for voc in vocabulary_list]:
        log.info(
            "Deleting {0} CKAN tag vocabulary and respective tags...".format(
                vocab_name
            )
        )
        existing_tags = tk.get_action("tag_list")(
            context, {"vocabulary_id": vocab_name}
        )
        for tag_name in existing_tags:
            log.info("Deleting tag {0}...".format(tag_name))
            tk.get_action("tag_delete")(
                context, {"id": tag_name, "vocabulary_id": vocab_name}
            )
        log.info("Deleting vocabulary {0}...".format(vocab_name))
        tk.get_action("vocabulary_delete")(
            context, {"id": vocab_name}
        )
    else:
        log.info(
            "Vocabulary {0} does not exist, nothing to do".format(
                vocab_name
            )
        )
    click.secho(f"{vocab_name} deleted!", fg="green")
    
def manage_vocab(vocab_name, schema_name="dataset", lang="en", delete=False):
    """
    Base function to create or delete a CKAN vocabulary and manage its tags.

    This function retrieves the site user and the list of vocabularies. It checks if the
    vocabulary already exists. If it does and delete is False, it skips the creation step. If it
    doesn't and delete is False, it creates a new vocabulary.

    Then, it retrieves the dataset schema and checks if the vocabulary field exists. If it
    does, it iterates over the field choices. For each choice, it checks if the tag already
    exists in the vocabulary. If it doesn't and delete is False, it creates a new tag. If it does
    and delete is True, it deletes the tag.

    This function can be safely called multiple times. It will only create or delete the vocabulary and tags once.

    Raises:
        None

    Returns:
        None
    """

    if delete:
        delete_vocab(vocab_name)
    else:
        create_vocab(vocab_name, schema_name, lang)
        
@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_inspire_tags(lang):
    """
    This command creates the INSPIRE themes vocabulary.

    Args:
        lang (str, optional): The language for the vocabulary. Defaults to "en".

    This command calls the manage_vocab function with the INSPIRE themes vocabulary name,
    the default dataset schema name, and the provided language. The manage_vocab function
    will create the vocabulary and add the INSPIRE themes to it.

    Returns:
        None
    """
    manage_vocab(sdct_config.SCHEMINGDCAT_INSPIRE_THEMES_VOCAB, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, lang)

@schemingdcat.command()
def delete_inspire_tags():
    """
    This command deletes the INSPIRE themes vocabulary.

    This command calls the manage_vocab function with the INSPIRE themes vocabulary name,
    the default dataset schema name, and the delete flag set to True. The manage_vocab function
    will delete the vocabulary and all its tags.

    Returns:
        None
    """
    manage_vocab(sdct_config.SCHEMINGDCAT_INSPIRE_THEMES_VOCAB, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, delete=True)

@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_dcat_tags(lang):
    """
    This command creates the DCAT themes vocabularies.

    Args:
        lang (str, optional): The language for the vocabularies. Defaults to "en".

    This command iterates over the DCAT themes vocabulary names and calls the manage_vocab
    function with each vocabulary name, the default dataset schema name, and the provided language.
    The manage_vocab function will create each vocabulary and add the DCAT themes to it.

    Returns:
        None
    """
    for theme in sdct_config.SCHEMINGDCAT_DCAT_THEMES_VOCAB:
        manage_vocab(theme, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, lang)

@schemingdcat.command()
def delete_dcat_tags():
    """
    This command deletes the DCAT themes vocabularies.

    This command iterates over the DCAT themes vocabulary names and calls the manage_vocab
    function with each vocabulary name, the default dataset schema name, and the delete flag set to True.
    The manage_vocab function will delete each vocabulary and all its tags.

    Returns:
        None
    """
    for theme in sdct_config.SCHEMINGDCAT_DCAT_THEMES_VOCAB:
        manage_vocab(theme, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, delete=True)
        
@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_iso_topic_tags(lang):
    """
    This command creates the ISO 19115 topics vocabulary.

    Args:
        lang (str, optional): The language for the vocabulary. Defaults to "en".

    This command calls the manage_vocab function with the ISO 19115 topics vocabulary name,
    the default dataset schema name, and the provided language. The manage_vocab function
    will create the vocabulary and add the ISO 19115 topics to it.

    Returns:
        None
    """
    manage_vocab(sdct_config.SCHEMINGDCAT_ISO19115_TOPICS_VOCAB, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, lang)

@schemingdcat.command()
def delete_iso_topic_tags():
    """
    This command deletes the ISO 19115 topics vocabulary.

    This command calls the manage_vocab function with the ISO 19115 topics vocabulary name,
    the default dataset schema name, and the delete flag set to True. The manage_vocab function
    will delete the vocabulary and all its tags.

    Returns:
        None
    """
    manage_vocab(sdct_config.SCHEMINGDCAT_ISO19115_TOPICS_VOCAB, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, delete=True)
    
@schemingdcat.command()
def download_rdf_eu_vocabs():
    """
    """
    log.info(
        "Downloading EU Vocabularies..."
        )
    
    rdf_files = []
    for rdf_data in EU_VOCABULARIES:
        rdf_vocab = rdf_data["name"]
        url = rdf_data["url"]
        description = rdf_data["description"]
        title = rdf_data["title"]

        if rdf_vocab == "access-right":
            rdf_files.append(BasicRdfFile(rdf_vocab, url, description, title))
        elif rdf_vocab == "licenses":
            rdf_files.append(LicenseRdfFile(rdf_vocab, url, description, title))
        elif rdf_vocab == "file-types":
            rdf_files.append(FileTypesRdfFile(rdf_vocab, url, description, title))
        elif rdf_vocab == "media-types":
            rdf_files.append(MediaTypesRdfFile(rdf_vocab, url, description, title))
        else:
            log.warning(f"Unrecognized RDF vocab '{rdf_vocab}'. Skipping.")

    for rdf_file in rdf_files:
        try:
            response = requests.get(rdf_file.url, headers=headers, timeout=10)
            if response.status_code == 200:
                rdf_content = response.text
                extracted_data = rdf_file.extract_description(rdf_content, rdf_file.url)
                if extracted_data:  # Avoid creating CSV if no valid descriptions
                    file_name = f"{rdf_file.name}.csv"
                    rdf_file.save_to_csv(extracted_data, EU_VOCABS_DIR / 'csv' / 'download' / file_name)
                    rdf_file.save_to_rdf(extracted_data,  EU_VOCABS_DIR / 'rdf' / 'download' / file_name)
                    log.info(f"{rdf_file.name} data extracted and saved to {file_name}")
            else:
                logging.warning(f"Failed to retrieve data for URL: {rdf_file.url}. Status Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            log.error(f":An error occurred for URL: {rdf_file.url}. Error: {e}")

    click.secho("EU Vocabs downloaded!", fg=u"green")
    
@schemingdcat.command()
@click.option("-v", "--verbose", is_flag=True, help='Enable verbose output.')
@click.confirmation_option(
    prompt="Are you sure you want to clean and set up the statistics table? This will delete all existing data."
)
def clean_stats(verbose):
    """
    Cleans the statistics table by deleting all existing records and recreating the table.

    This command performs a complete reset of the statistics table used by the SchemingDCAT extension.
    It deletes all existing records to ensure a fresh state and then recreates the table schema.
    Use this command with caution, as it will remove all existing statistics data.

    Args:
        verbose (bool): Enables verbose output if set.

    Returns:
        None
    """
    try:
        if verbose:
            log.setLevel(logging.DEBUG)
        log.info("Starting the reset process for the statistics table...")
        model.clean()
        click.secho("Statistics table cleaned!", fg=u"green")
    except Exception as e:
        log.error(f"An error occurred while cleaning the statistics table: {e}")
        raise click.ClickException(f"Failed to clean statistics table: {e}")

@schemingdcat.command()
@click.option("-v", "--verbose", is_flag=True, help='Enable verbose output.')
def update_stats(verbose):
    """
    Cleans the statistics table by deleting all existing records and recreating the table.

    This command performs a complete reset of the statistics table used by the SchemingDCAT extension.
    It deletes all existing records to ensure a fresh state and then recreates the table schema.
    Use this command with caution, as it will remove all existing statistics data.

    Args:
        verbose (bool): Enables verbose output if set.

    Returns:
        None
    """
    try:
        if verbose:
            log.setLevel(logging.DEBUG)
        log.info("Starting the update process for the statistics table...")
        model.update_table()
        click.secho("Statistics table updated!", fg=u"green")
    except Exception as e:
        log.error(f"An error occurred while updating the statistics table: {e}")
        raise click.ClickException(f"Failed to update statistics table: {e}")
