# MIT License
#
# Copyright (c) 2022 Landesarchiv Thüringen 
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from copy import deepcopy
from dataclasses import dataclass
from glob import glob
import os
import re
import shutil
import tempfile
from typing import Dict, List, NamedTuple
import uuid
import xml.etree.ElementTree as ET
import zipfile


class Config(NamedTuple):
    generic_message_path: str
    generic_xml_path: str
    uuid_regex: str
    ignore_path_regex_list: List[str]


@dataclass
class Statistic:
    count_messages_total: int
    count_messages_ignored: int
    count_messages_success: int


class XdomeaMessageEditor:
    config: Config
    statistic: Statistic

    def __init__(self):
        message_type_prefix = '_Aussonderung.'
        self.config = Config(
            generic_message_path='**/*' + message_type_prefix + '*.zip',
            generic_xml_path='**/*' + message_type_prefix + '*.xml',
            uuid_regex='[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            ignore_path_regex_list=[
                'Container_invalide'
            ]
        )

    def get_message_path_list(self, target_dir: str):
        message_path = os.path.join(target_dir, self.config.generic_message_path)
        full_message_list = glob(message_path, recursive=True)
        filtered_message_list = full_message_list
        for ignore_path_regex in self.config.ignore_path_regex_list:
            regex = re.compile(ignore_path_regex)
            filtered_message_list = \
                [message for message in filtered_message_list if regex.search(message) is None]
        self.statistic = Statistic(
            count_messages_total=len(full_message_list),
            count_messages_ignored=len(full_message_list) - len(filtered_message_list),
            count_messages_success=0
        )
        return filtered_message_list

    def get_message_ID(self, message_path: str):
        message_name = os.path.basename(message_path)
        return re.search(self.config.uuid_regex, message_name)

    def get_message_name(self, message_path: str):
        return os.path.basename(os.path.splitext(message_path)[0])

    def get_temp_message_path(self, message_path: str):
        temp_dir = tempfile.gettempdir()
        message_name = self.get_message_name(message_path)
        # add a random part to dir name to secure that directory doesn't already exists
        dir_name = message_name + '_' + str(uuid.uuid4())
        return os.path.join(temp_dir, dir_name)

    def delete_temp_message_folder(self, message_path: str):
        # assert message path is in the temporary directory
        assert os.path.commonprefix([tempfile.gettempdir(), message_path]) == tempfile.gettempdir()
        shutil.rmtree(message_path)

    def extract_message_archive(self, message_path: str):
        with zipfile.ZipFile(message_path, 'r') as zip_message:
            temp_message_path = self.get_temp_message_path(message_path)
            zip_message.extractall(temp_message_path)
        return temp_message_path

    def get_xml_namespace_dict(self, xml_path: str):
        return dict([
            node for _, node in ET.iterparse(
                xml_path, events=['start-ns']
            )
        ])

    def set_xml_process_id(self, xdomea_xml_path: str, process_ID: str):
        xml_tree = ET.parse(xdomea_xml_path)
        xdomea_namespace_dict = self.get_xml_namespace_dict(xdomea_xml_path)
        xdomea_header_node = \
            xml_tree.find('xdomea:Kopf', xdomea_namespace_dict)
        xdomea_process_id_node = \
            xdomea_header_node.find('xdomea:ProzessID', xdomea_namespace_dict)
        xdomea_process_id_node.text = process_ID
        # register xdomea namespace for serialization
        for prefix, uri in xdomea_namespace_dict.items():
            ET.register_namespace(prefix, uri)
        xml_tree.write(
            xdomea_xml_path,
            xml_declaration=True,
            encoding='utf-8',
            method='xml'
        )

    def rename_xdomea_file(self, xdomea_xml_path: str, new_message_ID: str):
        xml_message_file_name = os.path.basename(xdomea_xml_path)
        new_xml_message_file_name = re.sub(
            self.config.uuid_regex,
            new_message_ID,
            xml_message_file_name
        )
        new_xml_file_path = os.path.join(
            os.path.dirname(xdomea_xml_path),
            new_xml_message_file_name
        )
        os.rename(xdomea_xml_path, new_xml_file_path)
        self.xdomea_file_mapping = (
            os.path.basename(xdomea_xml_path), 
            os.path.basename(new_xml_file_path),
        )

    def set_new_message_ID(self, temp_message_path: str, message_ID: str, new_message_ID: str):
        generic_xml_path = os.path.join(temp_message_path, self.config.generic_xml_path)
        xdomea_xml_path_list = glob(generic_xml_path, recursive=True)
        # filter out all paths that don't contain the current message ID
        target_xdomea_path_list = [path for path in xdomea_xml_path_list if message_ID in path]
        # assert that only one target message exists
        assert len(target_xdomea_path_list) == 1
        target_xdomea_path = target_xdomea_path_list[0]
        self.set_xml_process_id(target_xdomea_path, new_message_ID)
        self.rename_xdomea_file(target_xdomea_path, new_message_ID)

    def create_new_message(self, message_path: str, temp_message_path: str, new_message_ID: str):
        target_dir = os.path.dirname(message_path)
        old_message_name = os.path.basename(message_path)
        new_message_name = re.sub(self.config.uuid_regex, new_message_ID, old_message_name)
        new_message_path = os.path.join(target_dir, new_message_name)
        generic_temp_file_path = os.path.join(temp_message_path, '*')
        temp_file_list = glob(generic_temp_file_path, recursive=False)
        with zipfile.ZipFile(message_path, 'r', zipfile.ZIP_DEFLATED) as message_zip:
            with zipfile.ZipFile(new_message_path, 'w', zipfile.ZIP_DEFLATED) as new_message_zip:
                for file_path in temp_file_list:
                    new_file_name = os.path.relpath(file_path, temp_message_path)
                    new_message_zip.write(file_path, new_file_name)
                    # preserve timestamp file info
                    new_file_info = new_message_zip.getinfo(new_file_name)
                    old_file_name = self.xdomea_file_mapping[0] \
                        if new_file_name == self.xdomea_file_mapping[1] else new_file_name
                    old_file_info = message_zip.getinfo(old_file_name)
                    new_file_info.date_time = deepcopy(old_file_info.date_time)
                    new_file_info.extra = deepcopy(old_file_info.extra)
        return new_message_path

    def print_ID_change_general_info(self, target_dir: str):
        print('\nBeginne Wechsel aller Prozess-IDs in Ordner: ' + target_dir)

    def print_ID_change_info(self, message_path: str, message_ID: str, new_message_ID: str):
        print('\n\nWechsel Prozess-ID der Nachricht: ' + self.get_message_name(message_path))
        print('\n\t' + message_ID + '\t--->\t' + new_message_ID)

    def print_ID_change_error_message(self):
        print('\nWechel der Prozess-ID ist fehlgeschlagen')

    def print_ID_change_statistic(self):
        count_message_failed = \
            self.statistic.count_messages_total - self.statistic.count_messages_success
        print('\n\nProzess-ID-Wechsel Gesamtergebnis\n')
        print('\terfolgreich:\t', self.statistic.count_messages_success)
        print('\tfehlgeschlagen:\t', count_message_failed)
        print('\tignoriert:\t', self.statistic.count_messages_ignored)
        print('\n')

    def randomize_all_message_IDs(self, target_dir: str):
        id_mapping = {}
        message_path_list = self.get_message_path_list(target_dir)
        self.print_ID_change_general_info(target_dir)
        for message_path in message_path_list:
            message_ID_match = self.get_message_ID(message_path)
            if message_ID_match is None:
                self.print_ID_change_error_message()
                continue
            message_ID = message_ID_match[0]  # get matched string (uuid)
            new_message_ID = ''
            if message_ID in id_mapping:
                new_message_ID = id_mapping[message_ID]
            else:
                new_message_ID = str(uuid.uuid4())
                id_mapping[message_ID] = new_message_ID
            self.print_ID_change_info(message_path, message_ID, new_message_ID)
            try:
                temp_message_path = self.extract_message_archive(message_path)
                self.set_new_message_ID(temp_message_path, message_ID, new_message_ID)
                new_message_path = \
                    self.create_new_message(message_path, temp_message_path, new_message_ID)
                #self.sync_zip_info(message_path, new_message_path, message_ID, new_message_ID)
                self.delete_temp_message_folder(temp_message_path)
                os.remove(message_path)
            except Exception as e:
                print(e)
                self.print_ID_change_error_message()
                continue
            self.statistic.count_messages_success += 1
        self.print_ID_change_statistic()


def main():
    editor = XdomeaMessageEditor()
    editor.randomize_all_message_IDs(os.getcwd())
    # pause until user confirmation on windows
    if os.name == 'nt':
        print('\n')
        os.system("pause")


if __name__ == '__main__':
    main()
