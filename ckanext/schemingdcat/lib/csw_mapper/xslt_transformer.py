import os
import tempfile
import logging
from saxonche import PySaxonProcessor
from rdflib import Graph

from ckanext.schemingdcat.config import (
    XLST_MAPPINGS_DIR,
    DEFAULT_XSLT_FILE
)

XML_FORMAT = 'xml'
RDF_FORMAT = 'xml'

log = logging.getLogger(__name__)

class XSLTTransformer:
    def __init__(self, xslt_file=None, debug_mode=False):
        if xslt_file is None:
            xslt_file = DEFAULT_XSLT_FILE

        log.debug(f"Initializing XSLTTransformer with xslt_file: {xslt_file}")

        xslt_path = xslt_file
        if not xslt_file.startswith('http://') and not xslt_file.startswith('https://'):
            xslt_path = os.path.join(XLST_MAPPINGS_DIR, xslt_file)
            if not os.path.isfile(xslt_path):
                raise FileNotFoundError(f"The file{xslt_path} does not exist in the mappings ({XLST_MAPPINGS_DIR}) directory.")
            xslt_path = os.path.abspath(xslt_path)

        self.xslt_path = xslt_path
        self.processor = PySaxonProcessor(license=False)
        self.xslt_processor = self.processor.new_xslt30_processor()
        self.debug_mode = debug_mode

        log.debug("XSLTTransformer initialized correctly.")

    def transform(self, xml_content):
        """Transforms XML content using XSLT and returns serialized RDF.

        Args:
            xml_content (str): The XML content to transform.

        Returns:
            str: The transformed RDF content serialized in RDF/XML format.

        Raises:
            Exception: If an error occurs during the transformation process.
        """
        log.debug("Starting XML transformation.")
        try:
            if isinstance(xml_content, bytes):
                xml_content = xml_content.decode('utf-8')
    
            with tempfile.NamedTemporaryFile(delete=False, suffix="." + XML_FORMAT, mode='w', encoding='utf-8') as temp_file:
                temp_file.write(xml_content)
                temp_file_path = temp_file.name
    
            result = self.xslt_processor.transform_to_string(
                stylesheet_file=self.xslt_path,
                source_file=temp_file_path
            )
            if self.xslt_processor.exception_occurred:
                for error in self.xslt_processor.get_error_message():
                    log.error(f"Error in XSLT transformation: {error}")
                raise Exception("Error in XSLT transformation")
    
            # Parse result as RDF and serialize in RDF/XML
            g = Graph()
            g.parse(data=result, format=XML_FORMAT)
            rdf_result = g.serialize(format=RDF_FORMAT)
    
            # Only for debugging purposes. Export the original XML content and the transformed RDF content.
            if self.debug_mode:
                self.debug_xml_and_rdf_output_files(rdf_result, xml_content)

            return rdf_result
        except Exception as e:
            log.error(f"Failure to transform XML content: {e}")
            raise

    def debug_xml_and_rdf_output_files(self, rdf_result, xml_content):
        """Debug XML and RDF output files by saving the last of them to the output directory for debugging purposes.
    
        Args:
            rdf_result (str): The transformed RDF content.
            xml_content (str): The original XML content.
        """
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
    
        files = {
            'transformed_output.rdf': rdf_result,
            'original_xml_content.xml': xml_content
        }
    
        for filename, content in files.items():
            file_path = os.path.join(output_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            log.debug(f"Content saved in {file_path}")
