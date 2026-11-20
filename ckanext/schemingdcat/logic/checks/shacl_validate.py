import logging, os
from pyshacl import validate as shacl_valid
from rdflib import Graph
from ckanext.dcat.processors import RDFSerializer
from ckan.plugins import toolkit as tk

path = os.path.abspath(os.path.dirname(__file__))
log = logging.getLogger(__name__)

profiles = tk.config.get("ckanext.dcat.rdf_profiles")


def validate():
    serializer = RDFSerializer(profiles=['es_dcat_ap_2','eu_dcat_ap_scheming'])
    datasets = tk.get_action('package_search')({}, {'q': '*:*'})['results']
    rdf_graph = serializer.serialize_catalog(dataset_dicts=datasets,_format="rdf")
    #log.debug(path+"/shacl/1.0.0/shacl_common_shapes.ttl")
    shacl_graph = Graph().parse(path+"/shacl/1.0.0/shacl_common_shapes.ttl", format="turtle")
    shacl_graph += Graph().parse(path+"/shacl/1.0.0/shacl_catalog_shape.ttl", format="turtle")
    shacl_graph += Graph().parse(path+"/shacl/1.0.0/hvd/shacl_common_hvd_shapes.ttl", format="turtle")

    #log.debug(rdf_graph)
    conforms, results_graph, results_text = shacl_valid(rdf_graph,
                                                        shacl_graph=shacl_graph,
                                                        advanced=True
                                                        )
    log.debug(results_text)

