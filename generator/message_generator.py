from lxml import etree
from io import StringIO

def main():
    config_doc = etree.parse('config/generator_config.xml')
    config_schema_doc = etree.parse('config/generator_config.xsd')
    config_schema = etree.XMLSchema(config_schema_doc)
    print(config_schema.validate(config_doc))

if __name__== '__main__' :
    main()
