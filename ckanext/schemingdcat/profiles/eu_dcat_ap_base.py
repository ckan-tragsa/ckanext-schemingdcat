import json
import re
import logging
from decimal import Decimal, DecimalException

from rdflib import term, URIRef, BNode, Literal
import ckantoolkit as toolkit

from ckan.lib.munge import munge_tag

from ckanext.dcat.utils import (
    resource_uri,
    DCAT_EXPOSE_SUBCATALOGS,
    DCAT_CLEAN_TAGS,
    publisher_uri_organization_fallback,
)

from ckanext.dcat.profiles.base import URIRefOrLiteral, CleanedURIRef

from ckanext.schemingdcat.profiles.base import (
    SchemingDCATRDFProfile,
    # Codelists
    MD_INSPIRE_REGISTER,
    MD_FORMAT,
    MD_EU_LANGUAGES,
    # Namespaces
    namespaces
)
from ckanext.schemingdcat.helpers import schemingdcat_get_catalog_publisher_info
from ckanext.schemingdcat.profiles.dcat_config import (
    # Vocabs
    RDF,
    XSD,
    SKOS,
    SCHEMA,
    RDFS,
    DCAT,
    DCATAP,
    DCT,
    ADMS,
    VCARD,
    FOAF,
    LOCN,
    GSP,
    OWL,
    SPDX,
    GEOJSON_IMT,
    CNT,
    ELI,
    EUROVOC,
    # Default values
    metadata_field_names,
    default_translated_fields,
    eu_dcat_ap_default_values,
    dcat_ap_default_licenses,
    )


config = toolkit.config

DISTRIBUTION_LICENSE_FALLBACK_CONFIG = "ckanext.dcat.resource.inherit.license"

log = logging.getLogger(__name__)

class BaseEuDCATAPProfile(SchemingDCATRDFProfile):
    """
    A base profile with common RDF properties across the different DCAT-AP versions

    """

    def _parse_dataset_base(self, dataset_dict, dataset_ref):

        dataset_dict["extras"] = []
        dataset_dict["resources"] = []

        multilingual_fields = self._multilingual_dataset_fields()

        # Basic fields
        for key, predicate in (
            ("url", DCAT.landingPage),
            ("version", OWL.versionInfo),
            ('encoding', CNT.characterEncoding),
        ):
            multilingual = key in multilingual_fields
            value = self._object_value(
                dataset_ref, predicate, multilingual=multilingual
            )
            if value:
                dataset_dict[key] = value

        # Multilingual core fields
        for key, predicate in (
            ("title", DCT.title),
            ("notes", DCT.description)
        ):
            if f"{key}_translated" in multilingual_fields:
                value = self._object_value(dataset_ref, predicate, multilingual=True)
                dataset_dict[f"{key}_translated"] = value
                dataset_dict[f"{key}"] = value.get(self._default_lang)
            else:
                value = self._object_value(dataset_ref, predicate)
                if value:
                    dataset_dict[key] = value

        if not dataset_dict.get("version"):
            # adms:version was supported on the first version of the DCAT-AP
            value = self._object_value(dataset_ref, ADMS.version)
            if value:
                dataset_dict["version"] = value

        # Tags
        if "tags_translated" in multilingual_fields:
            dataset_dict["tags_translated"] = self._object_value_list_multilingual(
                dataset_ref, DCAT.keyword)
            dataset_dict["tags"] = [
                {"name": t } for t in dataset_dict["tags_translated"][self._default_lang]
            ]
        else:
            # replace munge_tag to noop if there's no need to clean tags
            do_clean = toolkit.asbool(config.get(DCAT_CLEAN_TAGS, False))
            tags_val = [
                munge_tag(tag) if do_clean else tag for tag in self._keywords(dataset_ref)
            ]
            tags = [{"name": tag} for tag in tags_val]
            dataset_dict["tags"] = tags

        #  Simple values
        for key, predicate in (
            ("language", DCT.language),
            ("issued", DCT.issued),
            ("modified", DCT.modified),
            ("identifier", DCT.identifier),
            ("version_notes", ADMS.versionNotes),
            ("frequency", DCT.accrualPeriodicity),
            ("dcat_type", DCT.type),
        ):

            multilingual = key in multilingual_fields
            value = self._object_value(
                dataset_ref, predicate, multilingual=multilingual
            )
            if value:
                dataset_dict["extras"].append({"key": key, "value": value})

        #  Lists
        for key, predicate, in (
            ("alternate_identifier", ADMS.identifier),
            ("conforms_to", DCT.conformsTo),
            ("documentation", FOAF.page),
            ("related_resource", DCT.relation),
            ("has_version", DCT.hasVersion),
            ("is_version_of", DCT.isVersionOf),
            ("source", DCT.source),
            ("sample", ADMS.sample),
        ):
            values = self._object_value_list(dataset_ref, predicate)
            if values:
                dataset_dict["extras"].append({"key": key, "value": json.dumps(values)})

        #FIX: ckanext-schemingdcat: Contact details
        contact = self._contact_details(dataset_ref, DCAT.contactPoint)
        if not contact:
            # adms:contactPoint was supported on the first version of DCAT-AP
            contact = self._contact_details(dataset_ref, ADMS.contactPoint)
        if contact:
            contact = contact[0]
            for key in ("uri", "name", "email", "identifier", "url", "role"):
                if contact.get(key):
                    dataset_dict["extras"].append(
                        {
                            "key": "contact_{0}".format(key),
                            "value": contact.get(key)
                        }
                    )

        # Publishers and creators
        for item in [("publisher", DCT.publisher), ("creator", DCT.creator)]:
            agent_key, predicate = item
            #FIX: ckanext-schemingdcat: agent details
            agents = self._agents_details(dataset_ref, predicate)
            if agents:
                agent = agents[0]
                for key in ("uri", "name", "email", "url", "type", "identifier", "role"):
                    if agent.get(key):
                        dataset_dict["extras"].append(
                            {
                                "key": f"{agent_key}_{key}",
                                "value": agent.get(key)
                            }
                        )

        # Publisher fallback. Use contact details for publisher if not already set
        self._publisher_fallback_details(dataset_dict)

        # Temporal
        start, end = self._time_interval(dataset_ref, DCT.temporal)
        if start:
            dataset_dict["extras"].append({"key": "temporal_start", "value": start})
        if end:
            dataset_dict["extras"].append({"key": "temporal_end", "value": end})

        # Spatial
        spatial = self._spatial(dataset_ref, DCT.spatial)
        for key in ("uri", "text", "geom"):
            self._add_spatial_to_dict(dataset_dict, key, spatial)

        # Dataset URI (explicitly show the missing ones)
        dataset_uri = str(dataset_ref) if isinstance(dataset_ref, term.URIRef) else ""
        dataset_dict["extras"].append({"key": "uri", "value": dataset_uri})

        # access_rights
        access_rights = self._access_rights(dataset_ref, DCT.accessRights)
        if access_rights:
            dataset_dict["extras"].append(
                {"key": "access_rights", "value": access_rights}
            )

        # License
        if "license_id" not in dataset_dict:
            dataset_dict["license_id"] = self._license(dataset_ref)

        # Source Catalog
        if toolkit.asbool(config.get(DCAT_EXPOSE_SUBCATALOGS, False)):
            catalog_src = self._get_source_catalog(dataset_ref)
            if catalog_src is not None:
                src_data = self._extract_catalog_dict(catalog_src)
                dataset_dict["extras"].extend(src_data)


        #TODO: DCAT-AP: Provenance
        provenance = self._object_value(dataset_ref, DCT.provenance)
        #log.debug('Provenance eu_dcat_ap_2: %s', provenance)
        if provenance:
            provenance_description = self._object_value(provenance, DCT.description)
            if provenance_description:
                dataset_dict["extras"].append(
                    {"key": "provenance", "value": provenance_description}
                )

        # DCAT-AP: Themes, tags and tag_uri
        for key, predicate in (
            ("theme", DCAT.theme),
        ):
            values = self._object_value_list(dataset_ref, predicate)
            if values:
                self._assign_theme_tags(dataset_dict, key, values)

        # Resources
        for distribution in self._distributions(dataset_ref):

            resource_dict = {}

            multilingual_fields = self._multilingual_resource_fields()

            #  Simple values
            for key, predicate in (
                ("language", DCT.language),
                ("access_url", DCAT.accessURL),
                ("download_url", DCAT.downloadURL),
                ("issued", DCT.issued),
                ("modified", DCT.modified),
                ("status", ADMS.status),
                ("license_url", DCT.license),
                ("rights", DCT.rights),
            ):
                multilingual = key in multilingual_fields
                value = self._object_value(
                    distribution, predicate, multilingual=multilingual
                )
                if value:
                    resource_dict[key] = value

            # Multilingual core fields
            for key, predicate in (
                ("name", DCT.title),
                ("description", DCT.description)
            ):
                if f"{key}_translated" in multilingual_fields:
                    value = self._object_value(
                        distribution, predicate, multilingual=True
                    )
                    resource_dict[f"{key}_translated"] = value
                    resource_dict[f"{key}"] = value.get(self._default_lang)
                else:
                    value = self._object_value(distribution, predicate)
                    if value:
                        resource_dict[key] = value

            # URL

            resource_dict["url"] = self._object_value(
                distribution, DCAT.downloadURL
            ) or self._object_value(distribution, DCAT.accessURL)

            #  Lists
            for key, predicate in (
                ("documentation", FOAF.page),
                ("conforms_to", DCT.conformsTo),
                ("metadata_profile", DCT.conformsTo),
            ):
                values = self._object_value_list(distribution, predicate)
                if values:
                    resource_dict[key] = json.dumps(values)

            # Format and media type
            normalize_ckan_format = toolkit.asbool(
                config.get("ckanext.dcat.normalize_ckan_format", True)
            )
            imt, label = self._distribution_format(distribution, normalize_ckan_format)

            if imt:
                resource_dict["mimetype"] = imt

            if label:
                resource_dict["format"] = label
            elif imt:
                resource_dict["format"] = imt

            # Size
            size = self._object_value_int(distribution, DCAT.byteSize)
            if size is not None:
                resource_dict["size"] = size

            # Checksum
            for checksum in self.g.objects(distribution, SPDX.checksum):
                algorithm = self._object_value(checksum, SPDX.algorithm)
                checksum_value = self._object_value(checksum, SPDX.checksumValue)
                if algorithm:
                    resource_dict["hash_algorithm"] = algorithm
                if checksum_value:
                    resource_dict["hash"] = checksum_value

            # Distribution URI (explicitly show the missing ones)
            resource_dict["uri"] = (
                str(distribution) if isinstance(distribution, term.URIRef) else ""
            )

            # Remember the (internal) distribution reference for referencing in
            # further profiles, e.g. for adding more properties
            resource_dict["distribution_ref"] = str(distribution)

            dataset_dict["resources"].append(resource_dict)

        if self.compatibility_mode:
            # Tweak the resulting dict to make it compatible with previous
            # versions of the ckanext-dcat parsers
            for extra in dataset_dict["extras"]:
                if extra["key"] in (
                    "issued",
                    "modified",
                    "publisher_name",
                    "publisher_email",
                ):
                    extra["key"] = "dcat_" + extra["key"]

                if extra["key"] == "language":
                    extra["value"] = ",".join(sorted(json.loads(extra["value"])))

        return dataset_dict

    def _graph_from_dataset_base(self, dataset_dict, dataset_ref):

        g = self.g

        for prefix, namespace in namespaces.items():
            g.bind(prefix, namespace)

        g.add((dataset_ref, RDF.type, DCAT.Dataset))

        # Basic fields
        title_key = (
            "title_translated"
            if "title_translated" in dataset_dict
            else "title"
        )
        notes_key = (
            "notes_translated"
            if "notes_translated" in dataset_dict
            else "notes"
        )
        items = [
            (title_key, DCT.title, None, Literal),
            (notes_key, DCT.description, None, Literal),
            ("url", DCAT.landingPage, None, URIRef, FOAF.Document),
            ("identifier", DCT.identifier, ["guid", "id"], URIRefOrLiteral),
            ("version", OWL.versionInfo, ["dcat_version"], Literal),
            ("version_notes", ADMS.versionNotes, None, Literal),
            ("frequency", DCT.accrualPeriodicity, None, URIRefOrLiteral, DCT.Frequency),
            ("dcat_type", DCT.type, None, URIRefOrLiteral),
        ]
        self._add_triples_from_dict(dataset_dict, dataset_ref, items)
            
        # Tags
        # Pre-process keywords inside INSPIRE MD Codelists and update dataset_dict
        dataset_tag_base = f'{dataset_ref.split("/dataset/")[0]}'
        tag_names = [tag["name"].replace(" ", "").lower() for tag in dataset_dict.get("tags", [])]

        # Search for matching keywords in MD_INSPIRE_REGISTER and update dataset_dict
        if tag_names:             
            self._search_values_codelist_add_to_graph(MD_INSPIRE_REGISTER, tag_names, dataset_dict, dataset_ref, dataset_tag_base, g, DCAT.keyword)

        # Tags
        # Pre-process keywords inside INSPIRE MD Codelists and update dataset_dict
        dataset_tag_base = f'{dataset_ref.split("/dataset/")[0]}'
        
        # Procesar tags_translated
        if "tags_translated" in dataset_dict:
            for lang in dataset_dict["tags_translated"]:
                tag_names = [value.replace(" ", "").lower() for value in dataset_dict["tags_translated"][lang]]
                if tag_names:
                    self._search_values_codelist_add_to_graph(MD_INSPIRE_REGISTER, tag_names, dataset_dict, dataset_ref, dataset_tag_base, g, DCAT.keyword, lang)
        else:
            # Procesar tags
            tag_names = [tag["name"].replace(" ", "").lower() for tag in dataset_dict.get("tags", [])]
            if tag_names:
                self._search_values_codelist_add_to_graph(MD_INSPIRE_REGISTER, tag_names, dataset_dict, dataset_ref, dataset_tag_base, g, DCAT.keyword)

        # Dates
        items = [
            ("issued", DCT.issued, ["metadata_created"], Literal),
            ("modified", DCT.modified, ["metadata_modified"], Literal),
        ]
        self._add_date_triples_from_dict(dataset_dict, dataset_ref, items)

        #  Lists
        items = [
            ("language", DCT.language, None, URIRefOrLiteral, DCT.LinguisticSystem),
            ("conforms_to", DCT.conformsTo, None, URIRefOrLiteral, DCT.Standard),
            ("alternate_identifier", ADMS.identifier, None, URIRefOrLiteral, ADMS.Identifier),
            ("documentation", FOAF.page, None, URIRefOrLiteral, FOAF.Document),
            ("related_resource", DCT.relation, None, URIRefOrLiteral, RDFS.Resource),
            ("has_version", DCT.hasVersion, None, URIRefOrLiteral),
            ("is_version_of", DCT.isVersionOf, None, URIRefOrLiteral),
            ("source", DCT.source, None, URIRefOrLiteral),
            ("sample", ADMS.sample, None, URIRefOrLiteral, DCAT.Distribution),
        ]
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items)

        # DCAT Themes (https://publications.europa.eu/resource/authority/data-theme)
        # Append the final result to the graph       
        # Generate theme_items dynamically from metadata_field_names
        theme_items = [("theme", DCAT.theme, None, URIRef)]
        theme_items.extend([(profile['theme'], DCAT.theme, None, URIRef) for profile in metadata_field_names.values() if 'theme' in profile])

        self._add_list_triples_from_dict(dataset_dict, dataset_ref, theme_items)
        dcat_themes = self._themes(dataset_ref)
        for theme in dcat_themes:
            g.add((dataset_ref, DCAT.theme, URIRefOrLiteral(theme)))

        # Contact details
        if any([
            self._get_dataset_value(dataset_dict, "contact_uri"),
            self._get_dataset_value(dataset_dict, "contact_name"),
            self._get_dataset_value(dataset_dict, "contact_email"),
            self._get_dataset_value(dataset_dict, "contact_url"),
        ]):

            contact_uri = self._get_dataset_value(dataset_dict, "contact_uri")
            if contact_uri:
                contact_details = CleanedURIRef(contact_uri)
            else:
                contact_details = BNode()

            g.add((contact_details, RDF.type, VCARD.Kind))
            g.add((dataset_ref, DCAT.contactPoint, contact_details))

            # Add name
            self._add_triple_from_dict(
                dataset_dict, contact_details,
                VCARD.fn, "contact_name"
            )
            # Add mail address as URIRef, and ensure it has a mailto: prefix
            self._add_triple_from_dict(
                dataset_dict, contact_details,
                VCARD.hasEmail,
                "contact_email",
                _type=URIRef,
                value_modifier=self._add_mailto,
            )
            # Add contact URL
            self._add_triple_from_dict(
                dataset_dict, contact_details,
                VCARD.hasURL, "contact_url",
                _type=URIRef)

            # Add contact role
            g.add((contact_details, VCARD.role, URIRef(eu_dcat_ap_default_values["contact_role"])))

        # Resource maintainer/contact 
        if any([
            self._get_dataset_value(dataset_dict, "maintainer"),
            self._get_dataset_value(dataset_dict, "maintainer_uri"),
            self._get_dataset_value(dataset_dict, "maintainer_email"),
            self._get_dataset_value(dataset_dict, "maintainer_url"),
        ]):
            maintainer_uri = self._get_dataset_value(dataset_dict, "maintainer_uri")
            if maintainer_uri:
                maintainer_details = CleanedURIRef(maintainer_uri)
            else:
                maintainer_details = dataset_ref + "/maintainer"
                
            g.add((maintainer_details, RDF.type, VCARD.Kind))
            g.add((dataset_ref, DCAT.contactPoint, maintainer_details))

            ## Add name & mail
            self._add_triple_from_dict(
                dataset_dict, maintainer_details,
                VCARD.fn, "maintainer"
            )
            # Add mail address as URIRef, and ensure it has a mailto: prefix
            self._add_triple_from_dict(
                dataset_dict, maintainer_details,
                VCARD.hasEmail,
                "maintainer_email",
                _type=URIRef,
                value_modifier=self._add_mailto,
            )
            # Add maintainer URL
            self._add_triple_from_dict(
                dataset_dict, maintainer_details,
                VCARD.hasURL, "maintainer_url",
                _type=URIRef)

            # Add maintainer role
            g.add((maintainer_details, VCARD.role, URIRef(eu_dcat_ap_default_values["maintainer_role"])))

        # Publisher
        publisher_ref = None

        if dataset_dict.get("publisher"):
            # Scheming publisher field: will be handled in a separate profile
            pass
        elif any(
            [
                self._get_dataset_value(dataset_dict, "publisher_uri"),
                self._get_dataset_value(dataset_dict, "publisher_name"),
            ]
        ):
            # Legacy publisher_* extras
            publisher_uri = self._get_dataset_value(dataset_dict, "publisher_uri")
            publisher_name = self._get_dataset_value(dataset_dict, "publisher_name")
            if publisher_uri:
                publisher_ref = CleanedURIRef(publisher_uri)
            else:
                # No publisher_uri
                publisher_ref = BNode()
            publisher_details = {
                "name": publisher_name,
                "email": self._get_dataset_value(dataset_dict, "publisher_email"),
                "url": self._get_dataset_value(dataset_dict, "publisher_url"),
                "type": self._get_dataset_value(dataset_dict, "publisher_type"),
                "identifier": self._get_dataset_value(dataset_dict, "publisher_identifier"),
                "uri": publisher_uri,
                "role": self._get_dataset_value(dataset_dict, "publisher_role")
            }
        elif dataset_dict.get("organization"):
            # Fall back to dataset org
            org_id = dataset_dict["organization"]["id"]
            org_dict = None
            if org_id in self._org_cache:
                org_dict = self._org_cache[org_id]
            else:
                try:
                    org_dict = toolkit.get_action("organization_show")(
                        {"ignore_auth": True}, {"id": org_id}
                    )
                    self._org_cache[org_id] = org_dict
                except toolkit.ObjectNotFound:
                    pass
            if org_dict:
                publisher_ref = CleanedURIRef(
                    publisher_uri_organization_fallback(dataset_dict)
                )
                publisher_details = {
                    "name": org_dict.get("title"),
                    "email": org_dict.get("publisher_email") or org_dict.get("email"),
                    "url": org_dict.get("url"),
                    "type": org_dict.get("publisher_type") or org_dict.get("dcat_type"),
                    "identifier": org_dict.get("identifier"),
                }
        # Add to graph
        if publisher_ref:
            g.add((publisher_ref, RDF.type, FOAF.Agent))
            g.add((dataset_ref, DCT.publisher, publisher_ref))
            items = [
                ("name", FOAF.name, None, Literal),
                ("email", FOAF.mbox, None, Literal),
                ("url", FOAF.homepage, None, URIRef),
                ("type", DCT.type, None, URIRefOrLiteral),
                ("identifier", DCT.identifier, None, URIRefOrLiteral),
            ]

            # Add publisher role
            g.add((publisher_details, VCARD.role, URIRef(eu_dcat_ap_default_values["publisher_role"])))

            self._add_triples_from_dict(publisher_details, publisher_ref, items)

        # Creator
        creator_ref = None

        if dataset_dict.get("creator"):
            # Scheming publisher field: will be handled in a separate profile
            pass
        elif any(
            [
                self._get_dataset_value(dataset_dict, "creator_uri"),
                self._get_dataset_value(dataset_dict, "creator_name"),
            ]
        ):
            # Legacy creator_* extras
            creator_uri = self._get_dataset_value(dataset_dict, "creator_uri")
            creator_name = self._get_dataset_value(dataset_dict, "creator_name")
            if creator_uri:
                creator_ref = CleanedURIRef(creator_uri)
            else:
                # No creator_uri
                creator_ref = BNode()

            creator_details = {
                "name": creator_name,
                "email": self._get_dataset_value(dataset_dict, "creator_email"),
                "url": self._get_dataset_value(dataset_dict, "creator_url"),
                "type": self._get_dataset_value(dataset_dict, "creator_type"),
                "identifier": self._get_dataset_value(dataset_dict, "creator_identifier"),
            }

        # Add to graph
        if creator_ref:
            g.add((creator_ref, RDF.type, FOAF.Agent))
            g.add((dataset_ref, DCT.creator, creator_ref))  # Use DCT.creator for creator
            items = [
                ("name", FOAF.name, None, Literal),
                ("email", FOAF.mbox, None, Literal),
                ("url", FOAF.homepage, None, URIRef),
                ("type", DCT.type, None, URIRefOrLiteral),
                ("identifier", DCT.identifier, None, URIRefOrLiteral),
            ]
            self._add_triples_from_dict(creator_details, creator_ref, items)

        # TODO: Deprecated: https://semiceu.github.io/GeoDCAT-AP/drafts/latest/#deprecated-properties-for-period-of-time
        # Temporal
        start = self._get_dataset_value(dataset_dict, "temporal_start")
        end = self._get_dataset_value(dataset_dict, "temporal_end")
        if start or end:
            temporal_extent = BNode()

            g.add((temporal_extent, RDF.type, DCT.PeriodOfTime))
            if start:
                self._add_date_triple(temporal_extent, SCHEMA.startDate, start)
            if end:
                self._add_date_triple(temporal_extent, SCHEMA.endDate, end)
            g.add((dataset_ref, DCT.temporal, temporal_extent))

        # Spatial
        spatial_text = self._get_dataset_value(dataset_dict, "spatial_text")
        spatial_geom = self._get_dataset_value(dataset_dict, "spatial")

        if spatial_text or spatial_geom:
            spatial_ref = self._get_or_create_spatial_ref(dataset_dict, dataset_ref)

            if spatial_text:
                g.add((spatial_ref, SKOS.prefLabel, Literal(spatial_text)))

            if spatial_geom:
                self._add_spatial_value_to_graph(
                    spatial_ref, LOCN.geometry, spatial_geom
                )

        # Coordinate Reference System
        if self._get_dataset_value(dataset_dict, "reference_system"):
            crs_uri = self._get_dataset_value(dataset_dict, "reference_system")
            crs_details = CleanedURIRef(crs_uri)
            g.add((crs_details, RDF.type, DCT.Standard))
            g.add((crs_details, DCT.type, CleanedURIRef(eu_dcat_ap_default_values["reference_system_type"])))
            g.add((dataset_ref, DCT.conformsTo, crs_details))

        # Update licenses if it is in dcat_ap_default_licenses. DCAT-AP Compliance
        resource_license_fallback = eu_dcat_ap_default_values["license_url"]
        if "license_url" in dataset_dict:
            license_info = dcat_ap_default_licenses.get(dataset_dict["license_url"], None)
            if license_info:
                dataset_dict["license_id"] = license_info["fallback_license_id"]
                dataset_dict["license_url"] = license_info["fallback_license_url"]
                resource_license_fallback = license_info["fallback_license_url"]

        # Use fallback license if set in config
        if toolkit.asbool(config.get(DISTRIBUTION_LICENSE_FALLBACK_CONFIG, False)):
            if "license_url" in dataset_dict and isinstance(
                URIRefOrLiteral(dataset_dict["license_url"]), URIRef
            ):
                resource_license_fallback = dataset_dict["license_url"]

        g.add(
            (
                dataset_ref,
                DCT.license,
                URIRefOrLiteral(resource_license_fallback),
            )
        )

        # Statetements
        self._add_statement_to_graph(
            dataset_dict,
            "access_rights",
            dataset_ref,
            DCT.accessRights,
            DCT.RightsStatement
        )

        self._add_statement_to_graph(
            dataset_dict,
            "provenance",
            dataset_ref,
            DCT.provenance,
            DCT.ProvenanceStatement
        )

        # Resources
        for resource_dict in dataset_dict.get("resources", []):

            distribution = CleanedURIRef(resource_uri(resource_dict))

            g.add((dataset_ref, DCAT.distribution, distribution))

            g.add((distribution, RDF.type, DCAT.Distribution))

            #  Simple values
            name_key = (
                "name_translated" if "name_translated" in resource_dict else "name"
            )
            description_key = (
                "description_translated"
                if "description_translated" in resource_dict
                else "description"
            )

            items = [
                (name_key, DCT.title, None, Literal),
                (description_key, DCT.description, None, Literal),
                ("status", ADMS.status, None, URIRefOrLiteral),
                ("encoding", CNT.characterEncoding, None, Literal),
            ]

            self._add_triples_from_dict(resource_dict, distribution, items)

            #  Lists
            items = [
                ("documentation", FOAF.page, None, URIRefOrLiteral, FOAF.Document),
                ("language", DCT.language, None, URIRefOrLiteral, DCT.LinguisticSystem),
                ("conforms_to", DCT.conformsTo, None, URIRefOrLiteral, DCT.Standard),
                ("metadata_profile", DCT.conformsTo, None, URIRef),
            ]
            self._add_list_triples_from_dict(resource_dict, distribution, items)

            # Statetements
            self._add_statement_to_graph(
                resource_dict,
                "rights",
                distribution,
                DCT.rights,
                DCT.RightsStatement
            )

            # Set default license for distribution if needed and available
            if resource_license_fallback or dcat_ap_default_licenses.get(resource_dict["license"], None) and not (distribution, DCT.license, None) in g:
                g.add(
                    (
                        distribution,
                        DCT.license,
                        URIRefOrLiteral(resource_license_fallback),
                    )
                )
            # TODO: add an actual field to manage this
            if (distribution, DCT.license, None) in g:
                g.add(
                    (
                        list(g.objects(distribution, DCT.license))[0],
                        DCT.type,
                        URIRef("http://purl.org/adms/licencetype/UnknownIPR")
                    )
                )

            # Format
            mimetype = resource_dict.get("mimetype")
            fmt = resource_dict.get("format")

            # IANA media types (either URI or Literal) should be mapped as mediaType.
            # In case format is available and mimetype is not set or identical to format,
            # check which type is appropriate.
            if fmt and (not mimetype or mimetype == fmt):
                if (
                    "iana.org/assignments/media-types" in fmt
                    or not fmt.startswith("http")
                    and "/" in fmt
                ):
                    # output format value as dcat:mediaType instead of dct:format
                    mimetype = fmt
                    fmt = None
                else:
                    # Use dct:format
                    mimetype = None

            if mimetype:
                mimetype = URIRefOrLiteral(mimetype)
                g.add((distribution, DCAT.mediaType, mimetype))
                if isinstance(mimetype, URIRef):
                    g.add((mimetype, RDF.type, DCT.MediaType))
            elif fmt:
                mime_val = self._search_value_codelist(MD_FORMAT, fmt, "id", "media_type") or None
                if mime_val and mime_val != fmt:
                    g.add((distribution, DCAT.mediaType, URIRefOrLiteral(mime_val)))

            # Try to match format field
            fmt = self._search_value_codelist(MD_FORMAT, fmt, "label", "id") or fmt

            # Add format to graph
            if fmt:
                fmt = URIRefOrLiteral(fmt)
                g.add((distribution, DCT["format"], fmt))
                if isinstance(fmt, URIRef):
                    g.add((fmt, RDF.type, DCT.MediaTypeOrExtent))

            # URL fallback and old behavior
            url = resource_dict.get("url")
            download_url = resource_dict.get("download_url")
            access_url = resource_dict.get("access_url")

            # Validate download_url
            if download_url and not self._is_direct_download_url(download_url):
                download_url = None

            # Use access_url/download_url if it exists and is a valid URL, otherwise use url
            self._add_valid_url_to_graph(g, distribution, DCAT.accessURL, access_url, url)
            self._add_valid_url_to_graph(g, distribution, DCAT.downloadURL, download_url, url)

            # Dates
            items = [
                ("issued", DCT.issued, ["created"], Literal),
                ("modified", DCT.modified, ["metadata_modified"], Literal),
            ]

            self._add_date_triples_from_dict(resource_dict, distribution, items)

            # Numbers
            if resource_dict.get("size"):
                try:
                    g.add(
                        (
                            distribution,
                            DCAT.byteSize,
                            Literal(Decimal(resource_dict["size"]), datatype=XSD.decimal),
                        )
                    )
                except (ValueError, TypeError, DecimalException):
                    g.add((distribution, DCAT.byteSize, Literal(resource_dict["size"])))
            # Checksum
            if resource_dict.get("hash"):
                checksum = BNode()
                g.add((checksum, RDF.type, SPDX.Checksum))
                g.add(
                    (
                        checksum,
                        SPDX.checksumValue,
                        Literal(resource_dict["hash"], datatype=XSD.hexBinary),
                    )
                )

                if resource_dict.get("hash_algorithm"):
                    checksum_algo = URIRefOrLiteral(resource_dict["hash_algorithm"])
                    g.add(
                        (
                            checksum,
                            SPDX.algorithm,
                            checksum_algo,
                        )
                    )
                    if isinstance(checksum_algo, URIRef):
                        g.add((checksum_algo, RDF.type, SPDX.ChecksumAlgorithm))

                g.add((distribution, SPDX.checksum, checksum))

    def _graph_from_catalog_base(self, catalog_dict, catalog_ref):

        g = self.g

        for prefix, namespace in namespaces.items():
            g.bind(prefix, namespace)

        g.add((catalog_ref, RDF.type, DCAT.Catalog))

        # Basic fields
        license, access_rights, spatial_uri, language = [
            self._get_catalog_field(field_name='license_url'),
            self._get_catalog_field(field_name='access_rights'),
            self._get_catalog_field(field_name='spatial_uri'),
            self._search_value_codelist(MD_EU_LANGUAGES, config.get('ckan.locale_default'), "label","id") or eu_dcat_ap_default_values['language'],
            ]

        # Mandatory elements by NTI-RISP (datos.gob.es)
        items = [
            ("identifier", DCT.identifier, f'{config.get("ckan_url")}/catalog.rdf', Literal),
            ("title", DCT.title, config.get("ckan.site_title"), Literal),
            ("encoding", CNT.characterEncoding, "UTF-8", Literal),
            ("description", DCT.description, config.get("ckan.site_description"), Literal),
            ("language", DCT.language, language, URIRefOrLiteral),
            ("spatial_uri", DCT.spatial, spatial_uri, URIRefOrLiteral),
            ("theme_taxonomy", DCAT.themeTaxonomy, eu_dcat_ap_default_values["theme_taxonomy"], URIRef),
            ("theme_es_taxonomy", DCAT.themeTaxonomy, eu_dcat_ap_default_values["theme_es_taxonomy"], URIRef),
            ("theme_eu_taxonomy", DCAT.themeTaxonomy, eu_dcat_ap_default_values["theme_eu_taxonomy"], URIRef),
            ("homepage", FOAF.homepage, config.get("ckan_url"), URIRef),
            ("license", DCT.license, license, URIRef),
            ("conforms_to", DCT.conformsTo, eu_dcat_ap_default_values["conformance"], URIRef),
            ("access_rights", DCT.accessRights, access_rights, URIRefOrLiteral),
        ]
                 
        for item in items:
            key, predicate, fallback, _type = item
            if catalog_dict:
                value = catalog_dict.get(key, fallback)
            else:
                value = fallback
            if value:
                g.add((catalog_ref, predicate, _type(value)))

        # Dates
        modified = self._last_catalog_modification()
        if modified:
            self._add_date_triple(catalog_ref, DCT.modified, modified)

        # Catalog Publisher
        catalog_publisher_info = schemingdcat_get_catalog_publisher_info()
        
        publisher_details = {
            "name": catalog_publisher_info.get("name"),
            "email": catalog_publisher_info.get("email"),
            "url": catalog_publisher_info.get("url"),
            "type": catalog_publisher_info.get("type"),
            "identifier": catalog_publisher_info.get("identifier"),
        }

        publisher_ref = CleanedURIRef(publisher_details["identifier"]
        )
        
        # Add to graph
        if publisher_ref:
            g.add((publisher_ref, RDF.type, FOAF.Organization))
            g.add((catalog_ref, DCT.publisher, publisher_ref))
            items = [
                ("name", FOAF.name, None, Literal),
                ("email", FOAF.mbox, None, Literal),
                ("url", FOAF.homepage, None, URIRef),
                ("type", DCT.type, None, URIRefOrLiteral),
                ("identifier", DCT.identifier, None, URIRefOrLiteral),
            ]

            # Add publisher role
            g.add((publisher_ref, VCARD.role, URIRef(eu_dcat_ap_default_values["publisher_role"])))

            self._add_triples_from_dict(publisher_details, publisher_ref, items)


    def _assign_theme_tags(self, dataset_dict, key, values):
        for value in values:
            # DCAT-AP-ES themes
            if 'datos.gob.es' in value and 'sector' in value:
                dataset_dict[metadata_field_names["es_dcat_ap"]["theme"]] = value
            # DCAT Themes
            elif 'data-theme' in value:
                dataset_dict[metadata_field_names["eu_dcat_ap"]["theme"]] = value
            else:
                # Ensure tag_uri and tag_string are lists
                dataset_dict.setdefault('tag_uri', [])
                dataset_dict.setdefault('tag_string', [])
                
                # Add value to tag_uri if it doesn't already exist
                if value not in dataset_dict['tag_uri']:
                    dataset_dict['tag_uri'].append(value)
                
                # Process tag_string
                tag_value = value
                if value.startswith('http://') or value.startswith('https://'):
                    tag_value = value.rstrip('/').rsplit('/', 1)[-1]
                
                # Add processed value to tag_string if it doesn't already exist
                if tag_value not in dataset_dict['tag_string']:
                    dataset_dict['tag_string'].append(self._clean_name(tag_value))
