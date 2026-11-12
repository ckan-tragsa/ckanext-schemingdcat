import json
import logging
from decimal import Decimal, DecimalException

from rdflib import URIRef, BNode, Literal

from ckanext.dcat.utils import resource_uri
from ckanext.dcat.profiles.base import URIRefOrLiteral, CleanedURIRef

from ckanext.schemingdcat.profiles.base import (
    # Codelists
    MD_INSPIRE_REGISTER,
    MD_FORMAT,
    MD_EU_LANGUAGES,
    # Namespaces
    namespaces
)

from ckanext.schemingdcat.profiles.dcat_ap.eu_dcat_ap_2 import EuDCATAP2Profile
from ckanext.schemingdcat.profiles.dcat_config import (
    # Vocabs
    RDF,
    DCAT,
    DCATAP,
    GEODCATAP,
    VCARD,
    DCT,
    XSD,
    SCHEMA,
    RDFS,
    ADMS,
    CNT,
    ELI,
    # Default values
    metadata_field_names,
    eu_geodcat_ap_default_values,
    )
from ckanext.schemingdcat.config import (
    INVALID_CHARS,
    ACCENT_MAP,
)

log = logging.getLogger(__name__)

#TODO: Implement GeoDCAT-AP 2 profile
class EuGeoDCATAP2Profile(EuDCATAP2Profile):
    """
    A custom RDF profile based on the GeoDCAT-AP 2 for data portals in Europe

    More information and specification:

    https://joinup.ec.europa.eu/collection/semic-support-centre/solution/geodcat-application-profile-data-portals-europe

    """

    def parse_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        dataset_dict = self._parse_dataset_base(dataset_dict, dataset_ref)

        # DCAT AP v2 properties also applied to higher versions
        dataset_dict = self._parse_dataset_v2(dataset_dict, dataset_ref)

        # GeoDCAT-AP 2 properties
        dataset_dict = self._parse_dataset_geodcat_ap_v2(dataset_dict, dataset_ref)

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        # Call base method for common properties
        self._graph_from_dataset_base(dataset_dict, dataset_ref)

        # DCAT AP v2 properties also applied to higher versions
        self._graph_from_dataset_v2(dataset_dict, dataset_ref)

        # DCAT AP v2 specific properties
        self._graph_from_dataset_v2_only(dataset_dict, dataset_ref)
        
        # GeoDCAT-AP 2 properties
        self._graph_from_dataset_geodcat_ap_v2(dataset_dict, dataset_ref)

    def graph_from_catalog(self, catalog_dict, catalog_ref):
        
        # Call base method for common properties
        self._graph_from_catalog_base(catalog_dict, catalog_ref)
        
        # GeoDCAT-AP 2 Catalog properties
        self._graph_from_catalog_geodcat_ap_v2(catalog_dict, catalog_ref)

    def _parse_dataset_geodcat_ap_v2(self, dataset_dict, dataset_ref):

        # Call base super method for common properties
        super().parse_dataset(dataset_dict, dataset_ref)

        multilingual_fields = self._multilingual_dataset_fields()

        # Lists
        for key, predicate in (
            ("metadata_profile", DCT.conformsTo),
            ("inspire_id", ADMS.identifier),
            ("lineage_source", DCT.source),
            ("reference", DCAT.relation),
        ):
            values = self._object_value_list(dataset_ref, predicate)
            if values:
                # Replace the key directly in dataset_dict with the first value
                dataset_dict[key] = values

        # # Basic fields
        # for key, predicate in (
        #     ("topic", GEODCATAP.topicCategory, None),
        #     ("representation_type", ADMS.representionTechnique, None),
        # ):
        #     multilingual = key in multilingual_fields
        #     value = self._object_value(
        #         dataset_ref, predicate, multilingual=multilingual
        #     )
        #     if value:
        #         dataset_dict[key] = value


        # Basic fields
        for key, predicate in (
            ('dcat_type', GEODCATAP.resourceType),
            ('topic', GEODCATAP.topicCategory),
            ('identifier', DCT.identifier),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = value

        # INSPIRE Themes, tags and tag_uri
        for key, predicate in (
            ("theme", DCAT.theme),
        ):
            values = self._object_value_list(dataset_ref, predicate)
            if values:
                self._assign_theme_tags(dataset_dict, key, values)

        return dataset_dict

    def _graph_from_dataset_geodcat_ap_v2(self, dataset_dict, dataset_ref):
        """
        CKAN -> DCAT properties carried forward to higher GeoDCAT-AP versions
        """


        # INSPIRE roles. https://semiceu.github.io/GeoDCAT-AP/releases/3.0.0#responsible-party-and-metadata-point-of-contact---dataset-responsible-party-and-metadata-point-of-contact
        
        # Contact Point
        if any([
            self._get_dataset_value(dataset_dict, "contact_uri"),
            self._get_dataset_value(dataset_dict, "contact_role"),
        ]):
            self._add_role(dataset_dict, "contact_uri", role_key="contact_role")    
    
        # Maintainer
        if self._get_dataset_value(dataset_dict, "maintainer_uri"):
            self._add_role(dataset_dict, "maintainer_uri", role_value=eu_geodcat_ap_default_values["maintainer_role"])

        # Publisher
        if self._get_dataset_value(dataset_dict, "publisher_uri"):
            self._add_role(dataset_dict, "publisher_uri", role_value=eu_geodcat_ap_default_values["publisher_role"])

        # Author
        if self._get_dataset_value(dataset_dict, "author_uri"):
            self._add_role(dataset_dict, "author_uri", role_value=eu_geodcat_ap_default_values["author_role"])

        #  Lists
        items = [
            (metadata_field_names["eu_dcat_ap"]["theme"], DCAT.theme, None, URIRef),
            (metadata_field_names["es_dcat_ap"]["theme"], DCAT.theme, None, URIRef),
            ("metadata_profile", DCT.conformsTo, None, URIRef),
            ("lineage_source", DCT.source, None, Literal),
            ("reference", DCAT.relation, None, URIRefOrLiteral),
        ]
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items)

        # Basic fields without translating fields
        basic_items = [
            ("topic", GEODCATAP.topicCategory, None, URIRefOrLiteral),
            ("representation_type", ADMS.representionTechnique, None, URIRefOrLiteral),
        ]
        self._add_triples_from_dict(dataset_dict, dataset_ref, basic_items)

        self._add_triple_from_dict(
            dataset_dict,
            dataset_ref,
            ADMS.identifier,
            "inspire_id",
            list_value=True,
            _type=URIRefOrLiteral,
            _class=ADMS.Identifier,
        )

    def _graph_from_catalog_geodcat_ap_v2(self, catalog_dict, catalog_ref):
        """
        CKAN -> DCAT Catalog properties carried forward to higher GeoDCAT-AP versions
        """
        g = self.g

        for prefix, namespace in namespaces.items():
            g.bind(prefix, namespace)

        g.add((catalog_ref, RDF.type, DCAT.Catalog))
        
        # Mandatory elements by GeoDCAT-AP
        items = [
            ("conforms_to", DCT.conformsTo, eu_geodcat_ap_default_values["conformance"], URIRef),
        ]
                 
        for item in items:
            key, predicate, fallback, _type = item
            if catalog_dict:
                value = catalog_dict.get(key, fallback)
            else:
                value = fallback
            if value:
                g.add((catalog_ref, predicate, _type(value)))
    
    def _add_role(self, dataset_dict, uri_key, role_value=None, role_key=None):
        """
        Adds a role to a dataset entity in the graph.

        This function handles the addition of roles to dataset entities. It first
        retrieves the URI from the dataset dictionary using the provided `uri_key`.
        If the URI is found, it creates a `CleanedURIRef` object; otherwise, it
        creates a blank node (`BNode`). Depending on whether `role_value` or
        `role_key` is provided, it either adds a specific role or a role from the
        dataset dictionary.

        Args:
            dataset_dict (dict): The dataset dictionary containing metadata.
            uri_key (str): The key to retrieve the URI from the dataset dictionary.
            role_value (str, optional): The specific role URI to be added. Defaults to None.
            role_key (str, optional): The key to retrieve the role from the dataset dictionary. Defaults to None.

        Returns:
            None
        """
        uri = self._get_dataset_value(dataset_dict, uri_key)
        if uri:
            details = CleanedURIRef(uri)
        else:
            details = BNode()
        
        if role_value:
            # Remove existing role if any
            existing_roles = list(self.g.objects(details, VCARD.role))
            for role in existing_roles:
                self.g.remove((details, VCARD.role, role))
            
            # Add new role
            self.g.add((details, VCARD.role, URIRef(role_value)))
        elif role_key:
            # Add role from dataset_dict
            self._add_triple_from_dict(
                dataset_dict, details,
                VCARD.role, role_key,
                _type=URIRef)


    def _clean_name(self, name):
        """
        Cleans a name by removing accents, special characters, and spaces.

        Args:
            name (str): The name to clean.

        Returns:
            str: The cleaned name.
        """
        # Convert the name to lowercase
        name = name.lower()

        # Replace accented and special characters with their unaccented equivalents or -
        name = name.translate(ACCENT_MAP)
        name = INVALID_CHARS.sub("-", name.strip())

        # Truncate the name to 40 characters
        name = name[:40]

        return name
    
    def _assign_theme_tags(self, dataset_dict, key, values):
        """
        Assigns theme tags to the dataset dictionary based on the provided values.
    
        This method processes a list of values and assigns them to the appropriate
        theme fields in the dataset dictionary. It handles INSPIRE themes, DCAT-AP-ES
        themes, and DCAT themes. If a value does not match any of these themes, it is
        added to the 'tag_uri' and 'tag_string' fields.
    
        Args:
            dataset_dict (dict): The dataset dictionary to which the theme tags will be assigned.
            key (str): The key associated with the values.
            values (list): A list of values to be processed and assigned as theme tags.
    
        Returns:
            None
        """
        for value in values:
            # INSPIRE Themes
            if 'inspire' in value and 'theme' in value:
                dataset_dict['theme'] = value
            # DCAT-AP-ES themes
            elif 'datos.gob.es' in value and 'sector' in value:
                dataset_dict[metadata_field_names["es_dcat_ap"]["theme"]] = value
            # DCAT Themes
            elif 'data-theme' in value:
                dataset_dict[metadata_field_names["eu_dcat_ap"]["theme"]] = value
            else:
                # Ensure tag_uri and tag_string are lists
                tag_uri = dataset_dict.setdefault('tag_uri', [])
                tag_string = dataset_dict.setdefault('tag_string', [])
                
                # Add value to tag_uri if it doesn't already exist
                if value not in tag_uri:
                    tag_uri.append(value)
                
                # Process tag_string
                tag_value = value.rstrip('/').rsplit('/', 1)[-1] if value.startswith(('http://', 'https://')) else value
                
                # Add processed value to tag_string if it doesn't already exist
                cleaned_tag_value = self._clean_name(tag_value)
                if cleaned_tag_value not in tag_string:
                    tag_string.append(cleaned_tag_value)