import logging
import json

import ckan.plugins as p
from ckan.common import request

import ckanext.schemingdcat.config as sdct_config
from ckanext.schemingdcat.helpers import schemingdcat_get_current_lang
import ckanext.schemingdcat.utils as utils
from ckanext.schemingdcat.utils import deprecated

log = logging.getLogger(__name__)


class Faceted():

    p.implements(p.IFacets)
    facet_list = []

    def facet_load_config(self, facet_list):
        self.facet_list = facet_list
        #log.debug("Configured facet_list= {0}".format(self.facet_list))

    # Remove group facet
    def _facets(self, facets_dict):

        # if 'groups' in facets_dict:
        #   del facets_dict['groups']
        return facets_dict

    def dataset_facets(self,
                       facets_dict,
                       package_type):
        # This patch is necessary to avoid collisions with the harvest package type from the harvest plugin
        if package_type == "dataset":
            return self._custom_facets(facets_dict, package_type)
        else:
            return facets_dict

    def _custom_facets(self, facets_dict, package_type):
        lang_code = schemingdcat_get_current_lang()
    
        # Initialize cache dictionary if it does not exist
        if not hasattr(sdct_config, 'dataset_custom_facets'):
            sdct_config.dataset_custom_facets = {}
    
        # Check if we already cached the results for the current language
        if lang_code in sdct_config.dataset_custom_facets:
            return sdct_config.dataset_custom_facets[lang_code]
    
        _facets_dict = {}
        for facet in self.facet_list:
            # Look for the field label in the scheming file.
            # If it's not there, use the default dictionary provided
            scheming_item = utils.get_facets_dict().get(facet)
    
            if scheming_item:
                # Retrieve the corresponding label for the used language
                _facets_dict[facet] = scheming_item.get(lang_code)
                if not _facets_dict[facet]:
                    # If the label doesn't exist, try the default language label.
                    # And if that doesn't exist either, use the first one available.
                    raw_label = scheming_item.get(p.toolkit.config.get(
                        "ckan.locale_default", "en"),
                        list(scheming_item.values())[0]
                    )
                    if raw_label:
                        _facets_dict[facet] = p.toolkit._(raw_label)
                    else:
                        log.warning(
                            "Unable to find a valid label for the field '%s' when faceting" % facet)
    
                if not _facets_dict[facet]:
                    _facets_dict[facet] = p.toolkit._(facet)
    
            else:
                _facets_dict[facet] = p.toolkit._(facets_dict.get(facet))
    
        # Cache the results for the current language
        sdct_config.dataset_custom_facets[lang_code] = _facets_dict
    
        return _facets_dict

    def group_facets(self,
                     facets_dict,
                     group_type,
                     package_type):

        if p.toolkit.config.get('ckanext.schemingdcat.group_custom_facets'):
            #log.debug("Custom facets for group")
            facets_dict = self._custom_facets(facets_dict, package_type)
        return facets_dict

    def organization_facets(self,
                            facets_dict,
                            organization_type,
                            package_type):

        if p.toolkit.config.get('ckanext.schemingdcat.organization_custom_facets'):
            #log.debug("facetas personalizadas para organización")
            facets_dict = self._custom_facets(facets_dict, package_type)
        else:
            log.debug("Default facets for Organization")

#        lang_code = pylons.request.environ['CKAN_LANG']
#        facets_dict.clear()
#        facets_dict['organization'] = p.toolkit._('Organization')
#        facets_dict['theme_id'] =  p.toolkit._('Category')
#        facets_dict['res_format_label'] = p.toolkit._('Format')
#        facets_dict['publisher_display_name'] = p.toolkit._('Publisher')
#        facets_dict['administration_level'] = p.toolkit._(
#                                                'Administration level')
#        facets_dict['frequency'] = p.toolkit._('Update frequency')
#        tag_key = 'tags_' + lang_code
#        facets_dict[tag_key] = p.toolkit._('Tag')
#         FIXME: PARA FACETA COMUN DE TAGS
#         facets_dict['tags'] = p.toolkit._('Tag')
#        return self._facets(facets_dict)
        return facets_dict
