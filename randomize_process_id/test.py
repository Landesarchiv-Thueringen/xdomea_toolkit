from typing import NamedTuple
import os

class XMLNamespace(NamedTuple):
    short_name: str
    full_name:str

class Config(NamedTuple):
    generic_message_path: str
    generic_xml_path: str
    xdomea_501_name_pattern: str
    xdomea_503_name_pattern: str
    xdomea_namespace: XMLNamespace
    optional_appraisal_file_pattern: str

class XdomeaMessageEditor:
    config: Config

    def __init__(self):
        config = Config(
            generic_message_path = '**\\*Aussonderung*.zip',
            generic_xml_path = '**\\*Aussonderung*.xml',
            xdomea_501_name_pattern = '_Aussonderung.Anbieteverzeichnis.0501',
            xdomea_503_name_pattern = '_Aussonderung.Aussonderung.0503',
            xdomea_namespace = XMLNamespace(
                short_name = 'xdomea',
                full_name = "urn:xoev-de:xdomea:schema:2.3.0",
            ),
            optional_appraisal_file_pattern = '_Bewertungsentscheidung.txt',
        )

def main():
    print('fucker')
    editor = XdomeaMessageEditor()

if __name__== '__main__' :
    main()
