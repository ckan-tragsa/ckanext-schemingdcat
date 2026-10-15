from ckanext.schemingdcat.lib.csw.processor import SchemingDCATCatalogueServiceWeb
from ckanext.schemingdcat.lib.csw_mapper.xslt_transformer import XSLTTransformer

csw_url = "https://svjc-des-ckan.ttec.es:8486/catalogo/dataset/"
record_id = "MITECO_ESMAGRAMAATLASMANUALHABITATS20110616000"

csw_client = SchemingDCATCatalogueServiceWeb(url=csw_url)
transformer = XSLTTransformer("iso-19139-to-dcat-ap.xsl", True)

csw_record_xml = csw_client.get_metadata_record(record_id)[1]

rdf = transformer.transform(csw_record_xml)

print(rdf)


from ckanext.schemingdcat.lib.csw_mapper.xslt_transformer import XSLTTransformer

# XML de prueba (guárdalo o pégalo aquí)
with open("test.xml") as f:
    csw_record_xml = f.read()

transformer = XSLTTransformer("iso-19139-to-dcat-ap.xsl", True)

rdf = transformer.transform(csw_record_xml)

print(rdf)