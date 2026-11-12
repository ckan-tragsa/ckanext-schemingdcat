from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
from datetime import datetime
from owslib.iso import MD_Metadata
from lxml import etree

log = logging.getLogger(__name__)

#TODO: Not sure if this is the best way to do this
@dataclass
class InspireMetadataExtractor:
    """Base class for INSPIRE metadata extractors"""
    namespaces: Dict[str, str]
    root: etree.Element
    metadata: MD_Metadata

    @staticmethod
    def extract_text(element: Optional[etree.Element], xpath: str, namespaces: Dict[str, str]) -> Optional[str]:
        """Safely extracts text from XML element"""
        if element is None:
            return None
        result = element.xpath(xpath, namespaces=namespaces)
        return result[0] if result else None

class IdentificationExtractor(InspireMetadataExtractor):
    """Extracts identification metadata (title, abstract, etc)"""
    
    def extract(self) -> Dict[str, Any]:
        return {
            "title": self._extract_title(),
            "abstract": self._extract_abstract(),
            "alternative_title": self._extract_alternative_title(),
            "dataset_language": self._extract_dataset_language(),
            "topic_category": self._extract_topic_category(),
            "keywords": self._extract_keywords()
        }

    def _extract_title(self) -> Optional[str]:
        return self.metadata.identification.title if self.metadata.identification else None

    def _extract_abstract(self) -> Optional[str]:
        return self.metadata.identification.abstract if self.metadata.identification else None

    def _extract_alternative_title(self) -> Optional[str]:
        return self.extract_text(self.root, ".//gmd:alternateTitle/gco:CharacterString/text()", self.namespaces)
    
    def _extract_dataset_language(self) -> Optional[str]:
        return self.extract_text(self.root, ".//gmd:language/gco:CharacterString/text()", self.namespaces)
    
    def _extract_topic_category(self) -> List[str]:
        topics = self.root.xpath(".//gmd:topicCategory/gmd:MD_TopicCategoryCode/text()", namespaces=self.namespaces)
        return topics if topics else []
    
    def _extract_keywords(self) -> List[Dict[str, str]]:
        keywords = []
        if self.metadata.identification and self.metadata.identification.keywords:
            for kw_group in self.metadata.identification.keywords:
                keywords.extend([{"name": kw} for kw in kw_group.keywords])
        return keywords

class ExtentExtractor(InspireMetadataExtractor):
    """Extracts spatial and temporal extent information"""
    
    def extract(self) -> Dict[str, Any]:
        return {
            "geographic_bounding_box": self._extract_bounding_box(),
            "geographic_description": self._extract_geographic_description(),
            "temporal_extent": self._extract_temporal_extent(),
            "vertical_extent": self._extract_vertical_extent()
        }

    def _extract_bounding_box(self) -> Optional[Dict[str, float]]:
        bbox = self.root.xpath(".//gmd:EX_GeographicBoundingBox", namespaces=self.namespaces)
        if not bbox:
            return None
        
        return {
            "west": float(self.extract_text(bbox[0], ".//gmd:westBoundLongitude/gco:Decimal/text()", self.namespaces) or 0),
            "east": float(self.extract_text(bbox[0], ".//gmd:eastBoundLongitude/gco:Decimal/text()", self.namespaces) or 0),
            "north": float(self.extract_text(bbox[0], ".//gmd:northBoundLatitude/gco:Decimal/text()", self.namespaces) or 0),
            "south": float(self.extract_text(bbox[0], ".//gmd:southBoundLatitude/gco:Decimal/text()", self.namespaces) or 0)
        }

    def _extract_geographic_description(self) -> Optional[str]:
        return self.extract_text(
            self.root,
            ".//gmd:EX_GeographicDescription//gmd:geographicIdentifier//gco:CharacterString/text()",
            self.namespaces
        )

    def _extract_temporal_extent(self) -> Optional[Dict[str, str]]:
        extent = self.root.xpath(".//gmd:EX_TemporalExtent//gml:TimePeriod", namespaces=self.namespaces)
        if not extent:
            return None
            
        return {
            "start": self.extract_text(extent[0], ".//gml:beginPosition/text()", self.namespaces),
            "end": self.extract_text(extent[0], ".//gml:endPosition/text()", self.namespaces)
        }
    
    def _extract_vertical_extent(self) -> Optional[Dict[str, Any]]:
        extent = self.root.xpath(".//gmd:EX_VerticalExtent", namespaces=self.namespaces)
        if not extent:
            return None
            
        return {
            "minimum": float(self.extract_text(extent[0], ".//gmd:minimumValue/gco:Real/text()", self.namespaces) or 0),
            "maximum": float(self.extract_text(extent[0], ".//gmd:maximumValue/gco:Real/text()", self.namespaces) or 0),
            "crs": self.extract_text(extent[0], ".//gmd:verticalCRS/@href", self.namespaces)
        }  

class QualityExtractor(InspireMetadataExtractor):
    """Extracts quality and lineage information"""
    
    def extract(self) -> Dict[str, Any]:
        return {
            "lineage": self._extract_lineage(),
            "quality_scope": self._extract_quality_scope(),
            "quality_conformity": self._extract_quality_conformity()
        }

    def _extract_lineage(self) -> Optional[str]:
        return self.extract_text(
            self.root,
            ".//gmd:lineage//gmd:statement/gco:CharacterString/text()",
            self.namespaces
        )
    
    def _extract_quality_scope(self) -> Optional[str]:
        return self.extract_text(
            self.root,
            ".//gmd:DQ_DataQuality/gmd:scope//gmd:level/gmd:MD_ScopeCode/@codeListValue",
            self.namespaces
        )
    
    def _extract_quality_conformity(self) -> List[Dict[str, Any]]:
        conformity_elements = self.root.xpath(".//gmd:report//gmd:DQ_ConformanceResult", namespaces=self.namespaces)
        results = []
        
        for element in conformity_elements:
            results.append({
                "specification": self.extract_text(element, ".//gmd:specification//gco:CharacterString/text()", self.namespaces),
                "degree": self.extract_text(element, ".//gmd:pass/gco:Boolean/text()", self.namespaces),
                "explanation": self.extract_text(element, ".//gmd:explanation/gco:CharacterString/text()", self.namespaces)
            })
        
        return results

class ConstraintsExtractor(InspireMetadataExtractor):
    """Extracts access and use constraints"""
    
    def extract(self) -> Dict[str, Any]:
        return {
            "limitations_public_access": self._extract_access_limitations(),
            "use_constraints": self._extract_use_constraints()
        }

    def _extract_access_limitations(self) -> List[Dict[str, str]]:
        limitations = self.root.xpath(
            ".//gmd:resourceConstraints//gmd:accessConstraints/gmd:MD_RestrictionCode/@codeListValue",
            namespaces=self.namespaces
        )
        return [{"type": limitation} for limitation in limitations]
    
    def _extract_use_constraints(self) -> List[Dict[str, str]]:
        constraints = self.root.xpath(
            ".//gmd:resourceConstraints//gmd:useConstraints//gco:CharacterString/text()",
            namespaces=self.namespaces
        )
        return [{"description": constraint} for constraint in constraints]
    

class ResponsiblePartyExtractor(InspireMetadataExtractor):
    """Extracts responsible party information"""
    
    def extract(self) -> Dict[str, Any]:
        return {
            "metadata_point_of_contact": self._extract_metadata_contact(),
            "responsible_organisation": self._extract_responsible_org()
        }

    def _extract_metadata_contact(self) -> Optional[Dict[str, str]]:
        if not self.metadata.contact:
            return None
        return {
            "organization": self.metadata.contact[0].organization,
            "email": self.metadata.contact[0].email,
            "role": self.metadata.contact[0].role
        }
    
    def _extract_responsible_org(self) -> List[Dict[str, str]]:
        parties = self.root.xpath(".//gmd:identificationInfo//gmd:pointOfContact//gmd:CI_ResponsibleParty", namespaces=self.namespaces)
        results = []
        
        for party in parties:
            results.append({
                "organization": self.extract_text(party, ".//gmd:organisationName/gco:CharacterString/text()", self.namespaces),
                "email": self.extract_text(party, ".//gmd:electronicMailAddress/gco:CharacterString/text()", self.namespaces),
                "role": self.extract_text(party, ".//gmd:role/gmd:CI_RoleCode/@codeListValue", self.namespaces)
            })
        
        return results

def _generate_metadata_inspire(xml_content: str) -> Dict[str, Any]:
    """Main function to extract all INSPIRE metadata elements"""
    try:
        root = etree.fromstring(xml_content)
        metadata = MD_Metadata(root)
        namespaces = root.nsmap
        
        extractors = [
            IdentificationExtractor(namespaces, root, metadata),
            ExtentExtractor(namespaces, root, metadata),
            QualityExtractor(namespaces, root, metadata),
            ConstraintsExtractor(namespaces, root, metadata),
            ResponsiblePartyExtractor(namespaces, root, metadata)
        ]
        
        result = {}
        for extractor in extractors:
            result.update(extractor.extract())
            
        return result
        
    except Exception as e:
        log.error(f"Error extracting INSPIRE metadata: {str(e)}")
        return {}