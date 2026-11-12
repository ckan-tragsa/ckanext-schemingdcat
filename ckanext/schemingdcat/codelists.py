import csv
import requests
from datetime import datetime
from pathlib import Path
import os
import logging

# third-party libraries
from rdflib import Graph, Namespace, RDF, URIRef, Literal
from xml.etree import ElementTree as ET

from ckanext.dcat.profiles.base import (
    RDF,
    SKOS
)

from ckanext.schemingdcat.profiles.dcat_config import (
    EU_VOCABS_DIR,
    INSPIRE_CODELISTS_DIR,
    EUROVOC
)

log = logging.getLogger(__name__)


def load_inspire_csv_codelists():
    # Check if the codelists directory exists
    csv_subdir = INSPIRE_CODELISTS_DIR.joinpath("csv")
    if csv_subdir.exists() and csv_subdir.is_dir():
        codelist_paths = list(csv_subdir.glob("*.csv"))
    else:
        codelist_paths = list(INSPIRE_CODELISTS_DIR.glob("*.csv"))
    
    codelists_dfs = {}

    log.debug('INSPIRE_CODELISTS_DIR: %s', INSPIRE_CODELISTS_DIR)

    # Iterate over file paths and read in data
    for file_path in codelist_paths:
        with file_path.open("r") as f:
            reader = csv.DictReader(f)
            df = list(reader)
            file_name = file_path.stem.lower()
            codelists_dfs[file_name] = df

    # INSPIRE Codelists
    MD_INSPIRE_REGISTER = [item for df in codelists_dfs.values() for item in df]

    return {
        'MD_INSPIRE_REGISTER': MD_INSPIRE_REGISTER,
        'MD_FORMAT': codelists_dfs.get('file-type'),
        'MD_ES_THEMES': codelists_dfs.get('theme_es'),
        'MD_EU_THEMES': codelists_dfs.get('theme-dcat_ap'),
        'MD_EU_LANGUAGES': codelists_dfs.get('languages'),
        'MD_ES_FORMATS': codelists_dfs.get('format_es'),
        'DCAT_AP_STATUS': codelists_dfs.get('status'),
        'DCAT_AP_ACCESS_RIGHTS': codelists_dfs.get('rights')
    }
    
class RdfFile:
    def __init__(self, name, url, description, title):
        self.name = name
        self.url = url
        self.title = title
        self.description = description

    def extract_description(self, rdf_content, rdf_url):
        raise NotImplementedError

    def parse_graph(self, rdf_content):
        return Graph().parse(data=rdf_content, format='xml')

    def get_label_from_uri(self, uri):
        return uri.split('/')[-1]

    def save_to_csv(self, data, filename):
        file_path = EU_VOCABS_DIR / 'csv' / filename
        # Remove any None elements from the data list
        data = [d for d in data if d is not None]
        sorted_data = sorted(data, key=lambda x: x[1])  # Sort by label (2nd column)
        # Open the file in write mode, which will overwrite the file if it exists
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(sorted_data)
        log.info(f"Data extracted and saved to {file_path}")

    def download_rdf(self, rdf_url):
        try:
            response = requests.get(rdf_url)
            response.raise_for_status()
            log.info(f"Successfully downloaded RDF from {rdf_url}")
            return response.content
        except requests.RequestException as e:
            log.error(f"Failed to download RDF from {rdf_url}: {e}")
            return None

    def save_to_rdf(self, data, filename):
        graph = Graph()
        for item in data:
            uri = URIRef(item[0])
            label = Literal(item[1])
            graph.add((uri, RDF.type, SKOS.Concept))
            graph.add((uri, SKOS.prefLabel, label))
            if len(item) > 2:
                eu_uri = URIRef(item[2])
                graph.add((uri, SKOS.exactMatch, eu_uri))

        file_path = f"{filename}.rdf"
        graph.serialize(destination=file_path, format='xml')
        log.info(f"Data saved to RDF file at {file_path}")

class BasicRdfFile(RdfFile):
    def extract_description(self, rdf_content, rdf_url):
        graph = self.parse_graph(rdf_content)
        data = set()

        for concept in graph.subjects():
            uri = str(concept)
            label = self.get_label_from_uri(uri)
            if uri != rdf_url and label != self.get_label_from_uri(rdf_url):
                data.add((uri, label))

        return data

class LicenseRdfFile(RdfFile):
    def extract_description(self, rdf_content, rdf_url):
        graph = self.parse_graph(rdf_content)
        data = set()

        for concept in graph.subjects(RDF.type, SKOS.Concept):
            label = self.get_label_from_uri(concept)
            eu_uri = concept
            uri = str(graph.value(concept, SKOS.exactMatch, default=eu_uri))
            if concept != rdf_url and label != self.get_label_from_uri(rdf_url):
                data.add((uri, label, eu_uri))

        return data

class FileTypesRdfFile(RdfFile):
    def extract_description(self, rdf_content, rdf_url):
        graph = self.parse_graph(rdf_content)
        data = set()
        non_proprietary_data = set()
        machine_readable_data = set()

        for concept in graph.subjects(RDF.type, EUROVOC.FileType):
            uri = str(concept)
            label = self.get_label_from_uri(uri)
            non_prop_ext = str(graph.value(concept, EUROVOC.nonPropExt, default="false"))

            if uri != rdf_url and label != self.get_label_from_uri(rdf_url):
                data.add((uri, label, non_prop_ext))
                machine_readable_data.add((uri, label))
                if non_prop_ext == "true":
                    non_proprietary_data.add((uri, label))

        self.save_to_csv(non_proprietary_data, "non-propietary.csv")
        self.save_to_csv(machine_readable_data, "machine-readable.csv")

        return data

class MediaTypesRdfFile(RdfFile):
    def extract_description(self, xml_content, rdf_url):
        data = set()
        tree = ET.ElementTree(ET.fromstring(xml_content))
        root = tree.getroot()

        for record in root.findall(".//{http://www.iana.org/assignments}record"):
            name_elem = record.find("{http://www.iana.org/assignments}file")
            name = name_elem.text if name_elem is not None else ""
            label_elem = record.find("{http://www.iana.org/assignments}file")
            label = label_elem.text if label_elem is not None else ""

            if name != self.get_label_from_uri(rdf_url):
                uri = f"http://www.iana.org/assignments/media-types/{name}"
                data.add((uri, label))

        return data