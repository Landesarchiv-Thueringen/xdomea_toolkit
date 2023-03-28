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

import os
import uuid
import zipfile

from lxml import etree
from pathlib import Path

from .config import GeneratorConfig
from .xdomea_0501_message_generator import Xdomea0501MessageGenerator
from .xdomea_0503_message_generator import Xdomea0503MessageGenerator
from .types import XdomeaRegexConfig
from .zip import ZipUtil


class XdomeaMessageGenerator:

    def __init__(self, config: GeneratorConfig):
        self.regex_config = XdomeaRegexConfig(
            xdomea_0501_message_name='_Aussonderung.Anbieteverzeichnis.0501',
            xdomea_0503_message_name='_Aussonderung.Aussonderung.0503',
        )
        self.record_object_evaluation = {}
        self.config = config

        # load xdomea schema
        self.xdomea_schema_version = self.config.xdomea.version

        xdomea_schema_etree = etree.parse(self.config.xdomea.schema_path)
        self.__verify_schema_version(xdomea_schema_etree, self.xdomea_schema_version)
        self.xdomea_namespace = xdomea_schema_etree.getroot().nsmap['xdomea']
        self.xdomea_schema = etree.XMLSchema(xdomea_schema_etree)

    @staticmethod
    def __verify_schema_version(schema: etree.ElementTree, configured_version: str):
        xdomea_schema_version = schema.getroot().get('version')
        assert xdomea_schema_version == configured_version, \
            'konfigurierte Version und Version der xdomea Schemadatei sind ungleich'

    def generate_xdomea_messages(self):
        """
        Parses xdomea message patterns, validates against the pattern schema and generates and exports xdomea 0501 and
        0503 messages.
        """
        # generate message id
        generated_message_id = str(uuid.uuid4())

        # generate messages
        xdomea_0501_generator = Xdomea0501MessageGenerator(self.config, self.xdomea_schema)
        xdomea_0501_message_etree = xdomea_0501_generator.generate_message(generated_message_id)

        xdomea_0503_generator = Xdomea0503MessageGenerator(xdomea_0501_message_etree,
                                                           xdomea_0501_generator.record_object_evaluation,
                                                           self.config, self.xdomea_schema)
        xdomea_0503_message_etree = xdomea_0503_generator.generate_message(generated_message_id)

        # export messages
        print('\nexportiere Aussonderungsnachrichten:\n')
        self.__export_0501_message(
            generated_message_id,
            xdomea_0501_message_etree,
        )
        self.__export_0503_message(
            generated_message_id,
            xdomea_0503_message_etree,
            xdomea_0503_generator.document_version_info_list
        )

        # clear record object evaluations for next message generation
        self.record_object_evaluation.clear()

    def __export_0501_message(
        self,
        process_id: str,
        message_etree: etree,
    ):
        export_dir = os.path.join(self.config.output_dir, process_id)
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        message_name = process_id + self.regex_config.xdomea_0501_message_name
        xml_name = message_name + '.xml'
        zip_name = message_name + '.zip'
        message_path = os.path.join(export_dir, zip_name)
        with zipfile.ZipFile(message_path, 'w') as z:
            with z.open(xml_name, 'w') as f:
                message_etree.write(f, encoding='UTF-8', xml_declaration=True, pretty_print=True)
        print(message_path)

    def __export_0503_message(
        self,
        process_id: str,
        message_etree: etree,
        document_version_info_list
    ):
        export_dir = os.path.join(self.config.output_dir, process_id)
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        message_name = process_id + self.regex_config.xdomea_0503_message_name
        xml_name = message_name + '.xml'
        zip_name = message_name + '.zip'
        message_path = os.path.join(export_dir, zip_name)
        with zipfile.ZipFile(message_path, 'w') as z:
            with z.open(xml_name, 'w') as f:
                message_etree.write(f, encoding='UTF-8', xml_declaration=True, pretty_print=True)
            for version_info in document_version_info_list:
                z.write(version_info.path, version_info.xdomea_file_name)
                # set original ntfs timestamps on windows systems
                if os.name == 'nt':
                    ZipUtil.add_ntfs_info(z, version_info.path, version_info.xdomea_file_name)
        print(message_path)






