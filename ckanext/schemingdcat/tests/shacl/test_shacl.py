import json
import os
import logging

from rdflib import URIRef
from pyshacl import validate
import pytest

from ckan.tests.helpers import call_action

from ckanext.dcat.processors import RDFSerializer
from ckanext.schemingdcat.tests.utils import get_file_contents


log = logging.getLogger(__name__)

generated_graphs = {}

dataset_files = {
    "dcat_ap_2_full_dataset": "ckan_full_dataset_dcat_ap_2.json",
    "dcat_ap_2_legacy_dataset": "ckan_full_dataset_dcat_ap_2_legacy.json",
    "dcat_ap_2_vocabularies_dataset": "ckan_full_dataset_dcat_ap_2_vocabularies.json"
}

def _get_shacl_file_path(shacl_type, version):
    """
    Constructs the file path for a SHACL file based on the given type and version.

    Args:
        shacl_type (str): The suffix type of the SHACL file (e.g., 'shapes_recommended').
        version (str): The version of the DCAT-AP (e.g., '2.1.1').

    Returns:
        str: The full path to the SHACL file.
    """
    # Clean the shacl_type
    shacl_type = shacl_type.strip('_').replace('shacl_', '', 1)
    
    file_name = f"dcat-ap_{version}_shacl_{shacl_type}.ttl"

    return os.path.join(os.path.dirname(__file__), "shacl", version, file_name)

def graph_from_dataset(dataset_key):
    """
    Generates an RDF graph from a dataset identified by the given key.

    This function retrieves the dataset file name from the `dataset_files` dictionary
    using the provided `dataset_key`. If the dataset has not been previously processed,
    it reads the dataset file, creates the dataset, serializes it into an RDF graph,
    and stores the graph in the `generated_graphs` dictionary.

    Args:
        dataset_key (str): The key identifying the dataset in the `dataset_files` dictionary.

    Returns:
        rdflib.Graph: The RDF graph generated from the dataset.

    Raises:
        ValueError: If the `dataset_key` is not found in the `dataset_files` dictionary.
    """
    global generated_graphs

    file_name = dataset_files.get(dataset_key)
    if not file_name:
        raise ValueError(f"Dataset key '{dataset_key}' not found in dataset_files dictionary.")

    if not generated_graphs.get(file_name):
        if not file_name.startswith("ckan/"):
            file_name = "ckan/" + file_name
        dataset_dict = json.loads(get_file_contents(file_name))
       
        # Log the dataset_dict
        #log.info(f"Generated dataset_dict: {json.dumps(dataset_dict, indent=2)}")
        
        dataset = call_action("package_create", **dataset_dict)

        s = RDFSerializer()
        s.graph_from_dataset(dataset)

        generated_graphs[file_name] = s.g

    return generated_graphs[file_name]


def _results_count(results_graph):
    return len(
        [
            t
            for t in results_graph.triples(
                (None, URIRef("http://www.w3.org/ns/shacl#result"), None)
            )
        ]
    )


@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "dcat harvest schemingdcat_datasets schemingdcat fluent")
@pytest.mark.ckan_config(
    "scheming.dataset_schemas", "ckanext.schemingdcat:schemas/geodcat_ap/es_geodcat_ap_full.yaml"
)
@pytest.mark.ckan_config(
    "scheming.presets",
    "ckanext.schemingdcat:schemas/default_presets.json ckanext.fluent:presets.json",
)
@pytest.mark.ckan_config(
    "ckanext.dcat.rdf.profiles", "eu_dcat_ap_2 eu_dcat_ap_scheming"
)
def test_validate_dcat_ap_2_graph_shapes():

    graph = graph_from_dataset("dcat_ap_2_full_dataset")

    # dcat-ap_2.1.1_shacl_shapes.ttl: constraints concerning existance, domain and
    # literal range, and cardinalities.
    path = _get_shacl_file_path("shapes", "2.1.1")
    r = validate(graph, shacl_graph=path)
    conforms, results_graph, results_text = r
    assert conforms, results_text


@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "dcat harvest schemingdcat_datasets schemingdcat fluent")
@pytest.mark.ckan_config(
    "scheming.dataset_schemas", "ckanext.schemingdcat:schemas/geodcat_ap/es_geodcat_ap_full.yaml"
)
@pytest.mark.ckan_config(
    "scheming.presets",
    "ckanext.schemingdcat:schemas/default_presets.json ckanext.fluent:presets.json",
)
@pytest.mark.ckan_config(
    "ckanext.dcat.rdf.profiles", "eu_dcat_ap_2 eu_dcat_ap_scheming"
)
def test_validate_dcat_ap_2_graph_shapes_recommended():

    graph = graph_from_dataset("dcat_ap_2_full_dataset")

    # dcat-ap_2.1.1_shacl_shapes_recommended.ttl: constraints concerning existance
    # of recommended properties.
    path = _get_shacl_file_path("shapes_recommended", "2.1.1")
    r = validate(graph, shacl_graph=path)
    conforms, results_graph, results_text = r
    assert conforms, results_text


# @pytest.mark.usefixtures("with_plugins", "clean_db")
# @pytest.mark.ckan_config("ckan.plugins", "dcat harvest schemingdcat_datasets schemingdcat fluent")
# @pytest.mark.ckan_config("ckanext.dcat.rdf.profiles", "eu_dcat_ap_2")
# def test_validate_dcat_ap_2_legacy_graph_shapes():

#     graph = graph_from_dataset("dcat_ap_2_legacy_dataset")

#     # dcat-ap_2.1.1_shacl_shapes.ttl: constraints concerning existance, domain and
#     # literal range, and cardinalities.
#     path = _get_shacl_file_path("shapes", "2.1.1")
#     r = validate(graph, shacl_graph=path)
#     conforms, results_graph, results_text = r
#     assert conforms, results_text


# @pytest.mark.usefixtures("with_plugins", "clean_db")
# @pytest.mark.ckan_config("ckan.plugins", "dcat harvest schemingdcat_datasets schemingdcat fluent")
# @pytest.mark.ckan_config("ckanext.dcat.rdf.profiles", "eu_dcat_ap_2")
# def test_validate_dcat_ap_2_legacy_graph_shapes_recommended():

#     graph = graph_from_dataset("dcat_ap_2_legacy_dataset")

#     # dcat-ap_2.1.1_shacl_shapes_recommended.ttl: constraints concerning existance
#     # of recommended properties.
#     path = _get_shacl_file_path("shapes_recommended", "2.1.1")
#     r = validate(graph, shacl_graph=path)
#     conforms, results_graph, results_text = r
#     assert conforms, results_text


@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "dcat harvest schemingdcat_datasets schemingdcat fluent")
@pytest.mark.ckan_config(
    "scheming.dataset_schemas", "ckanext.schemingdcat:schemas/geodcat_ap/es_geodcat_ap_full.yaml"
)
@pytest.mark.ckan_config(
    "scheming.presets",
    "ckanext.schemingdcat:schemas/default_presets.json ckanext.fluent:presets.json",
)
@pytest.mark.ckan_config(
    "ckanext.dcat.rdf.profiles", "eu_dcat_ap_2 eu_dcat_ap_scheming"
)
def test_validate_dcat_ap_2_graph_shapes_range():

    graph = graph_from_dataset("dcat_ap_2_vocabularies_dataset")

    # dcat-ap_2.1.1_shacl_range.ttl: constraints concerning object range
    path = _get_shacl_file_path("range", "2.1.1")
    r = validate(graph, shacl_graph=path)
    conforms, results_graph, results_text = r

    failures = [
        str(t[2])
        for t in results_graph.triples(
            (
                None,
                URIRef("http://www.w3.org/ns/shacl#resultMessage"),
                None,
            )
        )
    ]

    known_failures = [
        "Value does not have class skos:Concept",
        "Value does not have class dcat:Dataset",
        # Qualified relations
        "Value does not conform to Shape :DcatResource_Shape. See details for more information.",
        "The node is either a Catalog, Dataset or a DataService",
    ]

    assert set(failures) - set(known_failures) == set(), results_text


@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "dcat scheming_datasets")
@pytest.mark.ckan_config(
    "scheming.dataset_schemas", "ckanext.dcat.schemas:dcat_ap_full.yaml"
)
@pytest.mark.ckan_config("ckanext.dcat.rdf.profiles", "euro_dcat_ap_3")
def test_validate_dcat_ap_3_graph():

    graph = graph_from_dataset("ckan_full_dataset_dcat_ap_vocabularies.json")

    path = _get_shacl_file_path("dcat-ap_3_shacl_shapes.ttl")
    r = validate(graph, shacl_graph=path)
    conforms, results_graph, results_text = r

    failures = [
        str(t[2])
        for t in results_graph.triples(
            (
                None,
                URIRef("http://www.w3.org/ns/shacl#resultMessage"),
                None,
            )
        )
    ]

    known_failures = [
        "Value does not have class skos:Concept",
        "Value does not have class dcat:Dataset",
    ]

    assert set(failures) - set(known_failures) == set(), results_text


@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "dcat scheming_datasets")
@pytest.mark.ckan_config(
    "scheming.dataset_schemas", "ckanext.dcat.schemas:dcat_us_full.yaml"
)
@pytest.mark.ckan_config(
    "scheming.presets",
    "ckanext.scheming:presets.json ckanext.dcat.schemas:presets.yaml",
)
@pytest.mark.ckan_config("ckanext.dcat.rdf.profiles", "dcat_us_3")
def test_validate_dcat_us_3_graph():

    graph = graph_from_dataset("ckan_full_dataset_dcat_us_vocabularies.json")

    path = _get_shacl_file_path("dcat-us_3.0_shacl_shapes.ttl")
    r = validate(graph, shacl_graph=path)
    conforms, results_graph, results_text = r

    failures = [
        str(t[2])
        for t in results_graph.triples(
            (
                None,
                URIRef("http://www.w3.org/ns/shacl#resultMessage"),
                None,
            )
        )
    ]

    known_failures = [
        "Value does not have class skos:Concept",
        "Value does not have class dcat:Dataset",
    ]

    assert set(failures) - set(known_failures) == set(), results_text
