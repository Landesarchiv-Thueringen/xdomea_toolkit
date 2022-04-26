from glob import glob
from typing import NamedTuple
import os
import re
import shutil
import tempfile
import uuid
import xml.etree.ElementTree as ET
import zipfile

class XMLNamespace(NamedTuple):
    short_name: str
    full_name:str

class Config(NamedTuple):
    generic_message_path: str
    generic_xml_path: str
    xdomea_message_type_prefix: str
    xdomea_501_name_pattern: str
    xdomea_503_name_pattern: str
    xdomea_namespace: XMLNamespace
    uuid_regex: str
    optional_appraisal_file_pattern: str

class XdomeaMessageEditor:
    config: Config

    def __init__(self):
        uuid_pattern = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        message_type_prefix = '_Aussonderung.'
        self.config = Config(
            generic_message_path = '**/*' + message_type_prefix + '*.zip',
            generic_xml_path = '**/*' + message_type_prefix + '*.xml',
            uuid_regex = uuid_pattern,
            xdomea_message_type_prefix = message_type_prefix,
            xdomea_501_name_pattern =
                uuid_pattern + message_type_prefix + 'Anbieteverzeichnis.0501.',
            xdomea_503_name_pattern = uuid_pattern + message_type_prefix + 'Aussonderung.0503.',
            xdomea_namespace = XMLNamespace(
                short_name = 'xdomea',
                full_name = "{urn:xoev-de:xdomea:schema:2.3.0}",
            ),
            optional_appraisal_file_pattern = '_Bewertungsentscheidung.txt',
        )
        ET.register_namespace(
            self.config.xdomea_namespace.short_name,
            self.config.xdomea_namespace.full_name
        )

    def get_message_path_list(self, target_dir: str):
        message_path = os.path.join(target_dir, self.config.generic_message_path)
        return glob(message_path, recursive = True)

    def get_message_ID(self, message_path: str):
        message_name = os.path.basename(message_path)
        return re.search(self.config.uuid_regex, message_name)

    def get_message_name(self, message_path: str):
        return os.path.basename(os.path.splitext(message_path)[0])

    def get_temp_message_path(self, message_path: str):
        temp_dir = tempfile.gettempdir()
        message_name = self.get_message_name(message_path)
        return os.path.join(temp_dir, message_name)

    def delete_temp_message_folder(self, message_path: str):
        # assert message path is in the temporary directory
        assert os.path.commonprefix([tempfile.gettempdir(), message_path]) == tempfile.gettempdir()
        shutil.rmtree(message_path)

    def extract_message_archive(self, message_path: str):
        zip_message = zipfile.ZipFile(message_path, 'r')
        temp_message_path = self.get_temp_message_path(message_path)
        zip_message.extractall(temp_message_path)
        zip_message.close()
        return temp_message_path

    def set_xml_process_id(self, xdomea_xml_path, process_ID) :
        xdomea_root_element = ET.parse(xdomea_xml_path)
        xdomea_header_node = xdomea_root_element.find('{urn:xoev-de:xdomea:schema:2.3.0}Kopf')
        xdomea_process_id_node = xdomea_header_node.find('{urn:xoev-de:xdomea:schema:2.3.0}ProzessID')
        xdomea_process_id_node.text = process_ID
        xdomea_root_element.write(
            xdomea_xml_path,
            xml_declaration = True,
            encoding = 'utf-8',
            method = "xml"
        )

    def rename_xdomea_file(self, xdomea_xml_path: str, new_message_ID: str):
        print(xdomea_xml_path)
        xml_message_file_name = os.path.basename(xdomea_xml_path)
        new_xml_message_file_name = re.sub(self.config.uuid_regex, new_message_ID,
            xml_message_file_name)
        print(new_xml_message_file_name)

    def set_new_message_ID(self, temp_message_path: str, message_ID: str, new_message_ID: str):
        generic_xml_path = os.path.join(temp_message_path, self.config.generic_xml_path)
        xdomea_xml_path_list = glob(generic_xml_path, recursive = True)
        # filter out all paths that don't contain the current message ID
        target_xdomea_path_list = [path for path in xdomea_xml_path_list if message_ID in path]
        # assert that only one target message exists
        assert len(target_xdomea_path_list) == 1
        target_xdomea_path = target_xdomea_path_list[0]
        self.set_xml_process_id(target_xdomea_path, new_message_ID)
        self.rename_xdomea_file(target_xdomea_path, new_message_ID)


    def randomize_all_message_IDs(self, target_dir: str):
        message_path_list = self.get_message_path_list(target_dir)
        for message_path in message_path_list:
            #print(message_path)
            message_ID_match = self.get_message_ID(message_path)
            if message_ID_match is None:
                continue
            message_ID = message_ID_match[0] # get matched string (uuid)
            new_message_ID = str(uuid.uuid4())
            temp_message_path = ''
            try :
                temp_message_path = self.extract_message_archive(message_path)
            except zip_extract_exception:
                print(zip_extract_exception)
                continue
            self.set_new_message_ID(temp_message_path, message_ID, new_message_ID)
            #self.delete_temp_message_folder(temp_message_path)


def main():
    editor = XdomeaMessageEditor()
    editor.randomize_all_message_IDs(os.getcwd())

if __name__== '__main__' :
    main()
