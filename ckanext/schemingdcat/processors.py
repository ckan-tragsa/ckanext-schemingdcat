import logging
from typing import Dict, Set, List, Optional

from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF

from ckantoolkit import config

from ckanext.dcat.processors import RDFSerializer, DCAT
from ckanext.dcat.utils import catalog_uri, dataset_uri, url_to_rdflib_format, DCAT_EXPOSE_SUBCATALOGS

from ckanext.schemingdcat.profiles.dcat_config import (
    # Entity models info
    DCAT_ENTITY_PROPERTIES_CONFIG,
    DCAT_PROFILE_CONFIGS,
)

log = logging.getLogger(__name__)


class SchemingDCATRDFSerializer(RDFSerializer):
    """
    Extended version of the RDFSerializer that ensures that all literals are labeled in the default language. are language-tagged in the default language.
    """
    
    def serialize_dataset(self, dataset_dict, _format='xml', context=None):
        """
        Overwrites the original method to add language tags before serialization.
        """
        log.info('In SchemingDCATRDFSerializer serialize_dataset')
        
        # Check directly if any profile name matches our configuration
        profile_names = [p.name if hasattr(p, 'name') else str(p) for p in self._profiles]        
        matching_profiles = [name for name in profile_names if name in DCAT_PROFILE_CONFIGS]
        lang_filter_profile = matching_profiles[0] if matching_profiles else None
        
        self.graph_from_dataset(dataset_dict)
        
        # Only apply language processing if we have a matching profile
        if lang_filter_profile:
            # Ensure language literals
            self._ensure_language_literals_by_config(self.g, profile=lang_filter_profile)
            
            # Remove duplicate empty literals
            self._remove_empty_language_literals(self.g)
        
        if not _format:
            _format = 'xml'
        _format = url_to_rdflib_format(_format)

        if _format == 'json-ld':
            output = self.g.serialize(
                format=_format,
                auto_compact=True,
                context=context
            )
        else:
            output = self.g.serialize(format=_format)

        return output
    
    def serialize_catalog(self, catalog_dict=None, dataset_dicts=None,
                    _format='xml', pagination_info=None):
        """
        Overwrites the original method for adding language tags before serialization of the complete catalog.
        """
        log.info('In SchemingDCATRDFSerializer serialize_catalog')
        
        # Check directly if any profile name matches our configuration
        profile_names = [p.name if hasattr(p, 'name') else str(p) for p in self._profiles]        
        matching_profiles = [name for name in profile_names if name in DCAT_PROFILE_CONFIGS]
        lang_filter_profile = matching_profiles[0] if matching_profiles else None

        catalog_ref = self.graph_from_catalog(catalog_dict)
        if dataset_dicts:
            for dataset_dict in dataset_dicts:
                dataset_ref = self.graph_from_dataset(dataset_dict)

                cat_ref = self._add_source_catalog(catalog_ref, dataset_dict, dataset_ref)
                if not cat_ref:
                    self.g.add((catalog_ref, DCAT.dataset, dataset_ref))
        
        # Only apply language processing if we have a matching profile
        if lang_filter_profile:
            # Ensure language literals
            self._ensure_language_literals_by_config(self.g, profile=lang_filter_profile)
            
            # Remove duplicate empty literals
            self._remove_empty_language_literals(self.g)
        
        if pagination_info:
            self._add_pagination_triples(pagination_info)

        if not _format:
            _format = 'xml'
        _format = url_to_rdflib_format(_format)
        output = self.g.serialize(format=_format)

        return output
    
    def _ensure_language_literals_by_config(self, graph: Graph, profile: str = "eu_dcat_ap_2") -> None:
        """
        Ensures that all literals of the specified entity types are labelled with language tags
        for the configured properties.
        Also removes duplicate literals with the same language tag, keeping only the first one.
        
        Args: 
            graph (graph): The RDF graph to process.
            profile (str): The ckanext-dcat profile to use to determine which entities to process.
        """
        # Get profile settings
        profile_config = DCAT_PROFILE_CONFIGS.get(profile, DCAT_PROFILE_CONFIGS.get("eu_dcat_ap_2", {}))
        default_lang = profile_config.get("default_language", config.get("ckan.locale_default", "en"))
        
        # Prepare dictionary of properties by type
        property_by_type = {}
        properties_all = set()
        
        # Collect properties for each type of entity in the profile
        for entity_name in profile_config.get("entities", []):
            entity_config = DCAT_ENTITY_PROPERTIES_CONFIG.get(entity_name, {})
            entity_type = entity_config.get("type")
            properties = set(entity_config.get("properties", []))
            
            if entity_type and properties:
                property_by_type[entity_type] = properties
                properties_all.update(properties)
        
        # Optimize: First identify all the nodes by type
        nodes_by_type = {}
        for entity_type in property_by_type.keys():
            nodes_by_type[entity_type] = set()
            
            # Find all nodes of this type
            for s, p, o in graph.triples((None, RDF.type, entity_type)):
                nodes_by_type[entity_type].add(s)
    
        triples_to_add = []
        triples_to_remove = []
        
        # FIRST PASS: Add missing language tags to literals
        # Process each node type with its specific properties
        for entity_type, nodes in nodes_by_type.items():
            properties = property_by_type.get(entity_type, set())
            
            for node in nodes:
                for prop in properties:
                    # Check if there is any literal with the target language
                    literals = list(graph.objects(node, prop))
                    
                    if not literals:
                        continue
                        
                    # Check if you already have the target language
                    has_target_lang = any(
                        isinstance(o, Literal) and o.language == default_lang
                        for o in literals
                    )
                    
                    if has_target_lang:
                        continue
                    
                    # Identify literals without language and with language
                    no_lang_literals = [
                        o for o in literals 
                        if isinstance(o, Literal) and isinstance(o.value, str) and not o.language
                    ]
                    
                    lang_literals = [
                        o for o in literals 
                        if isinstance(o, Literal) and isinstance(o.value, str) and o.language
                    ]
                    
                    # Decide which literals to process
                    literals_to_process = no_lang_literals if no_lang_literals else lang_literals
                    
                    for literal in literals_to_process:
                        # Add new literal with target language
                        triples_to_add.append((node, prop, Literal(literal.value, lang=default_lang)))
                        
                        # Delete original if no language
                        if not literal.language:
                            triples_to_remove.append((node, prop, literal))
        
        # Also process generic literals without associated entity type
        for s, p, o in graph.triples((None, None, None)):
            # If it is a relevant property and a literal without a language
            if (p in properties_all and 
                isinstance(o, Literal) and 
                isinstance(o.value, str) and 
                not o.language):
                
                triples_to_add.append((s, p, Literal(o.value, lang=default_lang)))
                triples_to_remove.append((s, p, o))
    
        # Apply first pass changes
        for triple in triples_to_add:
            graph.add(triple)
            
        for triple in triples_to_remove:
            graph.remove(triple)
        
        # SECOND PASS: Remove duplicate literals with the same language
        # Process each node type with its specific properties
        triples_to_remove = []
        
        # Check all subject-predicate pairs to find duplicates with same language
        for entity_type, nodes in nodes_by_type.items():
            properties = property_by_type.get(entity_type, set())
            
            for node in nodes:
                for prop in properties:
                    # Group literals by language
                    literals_by_language = {}
                    
                    for o in graph.objects(node, prop):
                        if isinstance(o, Literal) and isinstance(o.value, str) and o.language:
                            lang = o.language
                            if lang not in literals_by_language:
                                literals_by_language[lang] = []
                            literals_by_language[lang].append(o)
                    
                    # For each language, keep only the first literal
                    for lang, lang_literals in literals_by_language.items():
                        if len(lang_literals) > 1:
                            # Keep the first literal and remove the rest
                            for duplicate in lang_literals[1:]:
                                triples_to_remove.append((node, prop, duplicate))
    
        # Also check generic literals without entity type
        for s, p, o in graph:
            if p in properties_all and isinstance(o, Literal) and o.language:
                # Count literals for this subject-predicate-language combination
                lang = o.language
                same_lang_literals = [
                    lit for lit in graph.objects(s, p)
                    if isinstance(lit, Literal) and lit.language == lang
                ]
                
                # If we have more than one literal with the same language,
                # mark all but the first one for removal
                if len(same_lang_literals) > 1 and o != same_lang_literals[0]:
                    triples_to_remove.append((s, p, o))
        
        # Remove duplicate language literals
        for triple in triples_to_remove:
            graph.remove(triple)
    
    def _remove_empty_language_literals(self, graph: Graph) -> None:
        """
        Removes empty language-tagged literals and ensures at least one valid literal remains for each property.
    
        This method improves the quality of the RDF output by:
        1. Removing empty language-tagged literals.
        2. Removing untagged literals when language-tagged alternatives exist.
        3. Ensuring at least one valid literal remains for each property.
    
        Args:
            graph (Graph): The RDF graph to process.
        """
        # Step 1: Identify and remove empty language-tagged literals
        empty_lang_literals = [
            (s, p, o) for s, p, o in graph 
            if isinstance(o, Literal) and o.language and isinstance(o.value, str) and not o.value.strip()
        ]
        for triple in empty_lang_literals:
            graph.remove(triple)
    
        # Step 2: Identify untagged literals that have language-tagged alternatives
        triples_to_remove = []
        for s, p, o in graph:
            if isinstance(o, Literal) and isinstance(o.value, str) and not o.language:
                # Check if this property should have language tags based on config
                property_requires_tag = False
    
                # Find the entity type for this subject
                entity_types = [t for _, _, t in graph.triples((s, RDF.type, None))]
    
                for entity_type in entity_types:
                    # Check if this entity type is in our configuration
                    for entity_config in DCAT_ENTITY_PROPERTIES_CONFIG.values():
                        if entity_config["type"] == entity_type and p in entity_config["properties"]:
                            property_requires_tag = True
                            break
    
                    if property_requires_tag:
                        break
    
                if property_requires_tag:
                    # Get all literals for this subject-predicate pair
                    all_literals = list(graph.objects(s, p))
    
                    # Find language-tagged literals
                    tagged_literals = [
                        lit for lit in all_literals 
                        if isinstance(lit, Literal) and isinstance(lit.value, str) and lit.language
                    ]
    
                    # If there are language-tagged literals, mark the untagged one for removal
                    if tagged_literals:
                        triples_to_remove.append((s, p, o))
    
        # Step 3: Remove all identified untagged literals
        for triple in triples_to_remove:
            graph.remove(triple)
    
        # Step 4: Ensure at least one valid literal remains for each property
        for s, p in set((s, p) for s, p, _ in graph):
            # Get all literals for this subject-predicate pair
            literals = list(graph.objects(s, p))
    
            # If no valid literals remain, log a warning
            if not literals:
                log.warning(f"No valid literals remain for subject {s} and predicate {p}.")