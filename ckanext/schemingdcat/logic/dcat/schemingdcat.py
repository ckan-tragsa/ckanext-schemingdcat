import logging
from typing import Dict, Any, Callable

from ckan.plugins import toolkit

from ckanext.dcat.logic import _search_ckan_datasets, _pagination_info

from ckanext.schemingdcat.processors import SchemingDCATRDFSerializer

log = logging.getLogger(__name__)

@toolkit.chained_action
def dcat_dataset_show(original_action: Callable, context: Dict, data_dict: Dict) -> str:
    """
    Enhanced version of dcat_dataset_show that uses the custom RDF serializer.
    
    This function intercepts the original dcat_dataset_show action and replaces the serializer with our custom version that correctly handles language tags on all literals.
    
    Args:
        original_action: The original action function.
        context: The CKAN context
        data_dict: Dictionary with the data of the request
        
    Returns:
        str: The dataset in serialized RDF format with appropriate language tags.
    """
    toolkit.check_access('dcat_dataset_show', context, data_dict)

    dataset_dict = toolkit.get_action('package_show')(context, data_dict)

    serializer = SchemingDCATRDFSerializer(profiles=data_dict.get('profiles'))

    output = serializer.serialize_dataset(dataset_dict,
                                          _format=data_dict.get('format'))
    
    return output


@toolkit.chained_action
@toolkit.side_effect_free
def dcat_catalog_show(original_action: Callable, context: Dict, data_dict: Dict) -> str:
    """
    Enhanced version of dcat_catalog_show that uses the custom RDF serializer.
    
    This function intercepts the original dcat_catalog_show action and substitutes the serializer with our custom version that correctly handles the language tags on all literals.
    
    Args:
        original_action: The original action function.
        context: The CKAN context
        data_dict: Dictionary with the data of the request
        
    Returns:
        str: The catalog in serialized RDF format with appropriate language tags.
    """
    toolkit.check_access('dcat_catalog_show', context, data_dict)

    query = _search_ckan_datasets(context, data_dict)
    dataset_dicts = query['results']
    pagination_info = _pagination_info(query, data_dict)

    serializer = SchemingDCATRDFSerializer(profiles=data_dict.get('profiles'))

    output = serializer.serialize_catalog({}, dataset_dicts,
                                          _format=data_dict.get('format'),
                                          pagination_info=pagination_info)
    
    return output
