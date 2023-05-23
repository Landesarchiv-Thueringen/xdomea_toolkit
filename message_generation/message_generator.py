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
from enum import Enum
from lib.util.config import ConfigParser, FileEvaluationConfig, FileStructureConfig, ProcessStructureConfig,\
    DocumentStructureConfig
from lib.util.file import FileInfo, FileUtil
from lib.util.zip import ZipUtil
from lxml import etree
import os
from pathlib import Path
import random
from typing import Optional, Union
import uuid
import zipfile


@dataclass
class XdomeaRegexConfig:
    xdomea_0501_message_name: str
    xdomea_0502_message_name: str
    xdomea_0503_message_name: str
    xdomea_0504_message_name: str


class XdomeaEvaluation(str, Enum):
    EVALUATE = 'B'
    ARCHIVE = 'A'
    DISCARD = 'V'


class XdomeaMessageGenerator:

    def __init__(self):
        self.regex_config = XdomeaRegexConfig(
            xdomea_0501_message_name='_Aussonderung.Anbieteverzeichnis.0501',
            xdomea_0502_message_name='_Aussonderung.Bewertungsverzeichnis.0502',
            xdomea_0503_message_name='_Aussonderung.Aussonderung.0503',
            xdomea_0504_message_name='_Aussonderung.AnbietungEmpfangBestaetigen.0504',
        )
        self.record_object_evaluation = {}

    def read_config(self, config_path: str, config_schema_path: str):
        """
        Parses xml config file into object representation. Validates xml config file against schema.
        :param config_path: path of xml config file
        :param config_schema_path: path of xml schema for config file
        """
        self.config = ConfigParser.parse_config(config_path, config_schema_path)

    def generate_xdomea_messages(self):
        """
        Parses xdomea message patterns, validates against the pattern schema and generates and exports xdomea 0501,
        0502, 0503 and 0504 messages.
        """
        # generate message id
        generated_message_id = str(uuid.uuid4())

        # parse xdomea schema and assert correct version
        pattern_schema_tree = etree.parse(self.config.xdomea.schema_path)
        self.xdomea_schema_version = pattern_schema_tree.getroot().get('version')
        assert self.xdomea_schema_version == self.config.xdomea.version,\
            'konfigurierte Version und Version der xdomea Schemadatei sind ungleich'
        self.pattern_schema = etree.XMLSchema(pattern_schema_tree)
        self.xdomea_namespace = pattern_schema_tree.getroot().nsmap['xdomea']

        # generate messages
        xdomea_0501_message_etree = self.__generate_0501_message(generated_message_id)
        xdomea_0502_message_etree = self.__generate_0502_message(generated_message_id)
        xdomea_0503_message_etree = self.__generate_0503_message(generated_message_id, xdomea_0501_message_etree)
        #xdomea_0504_message_etree = self.__generate_0504_message(generated_message_id)

        # export messages
        print('\nexportiere Aussonderungsnachrichten:\n')
        self.__export_message(
            generated_message_id,
            xdomea_0501_message_etree,
            self.regex_config.xdomea_0501_message_name
        )
        self.__export_message(
            generated_message_id,
            xdomea_0502_message_etree,
            self.regex_config.xdomea_0502_message_name
        )
        self.__export_0503_message(
            generated_message_id,
            xdomea_0503_message_etree,
        )
        # self.__export_message(
        #     generated_message_id,
        #     xdomea_0504_message_etree,
        #     self.regex_config.xdomea_0504_message_name
        # )

        # clear record object evaluations for next message generation
        self.record_object_evaluation.clear()

    def __generate_0501_message(self, message_id: str) -> etree.ElementTree:
        """
        Generate a 0501 xdomea message
        :param message_id: generated uuid to use for the message
        :return: generated message element tree
        """
        xdomea_0501_pattern_etree = self.__get_message_pattern(self.config.xdomea.pattern_config.message_0501_path)

        xdomea_0501_pattern_root = xdomea_0501_pattern_etree.getroot()
        self.__set_xdomea_process_id(xdomea_0501_pattern_root, message_id)

        # get record object patterns from message pattern
        self.file_pattern_list = self.__get_file_patterns(xdomea_0501_pattern_root)
        self.process_pattern_list = self.__get_process_patterns(xdomea_0501_pattern_root)
        self.document_pattern_list = self.__get_document_patterns(xdomea_0501_pattern_root)

        # remove record object patterns from the template
        self.__remove_record_object_patterns(xdomea_0501_pattern_root)

        # generate xdomea 0501 file structure (recursively adds subfile, process, subprocess and document structures)
        self.__generate_0501_file_structure(xdomea_0501_pattern_root, self.config.structure)
        self.__replace_record_object_placeholder(xdomea_0501_pattern_root)

        # validate generate xdomea 0501 message against xml schema
        self.pattern_schema.assertValid(xdomea_0501_pattern_etree)

        return xdomea_0501_pattern_etree

    def __generate_0502_message(self, message_id: str) -> etree.ElementTree:
        """
        Generate a 0502 xdomea message (de: Aussonderung.Bewertungsverzeichnis)
        :param message_id: generated uuid to use for the message
        :return: generated message element tree
        """
        xdomea_0502_pattern_etree = self.__get_message_pattern(self.config.xdomea.pattern_config.message_0502_path)
        xdomea_0502_pattern_root = xdomea_0502_pattern_etree.getroot()

        self.__set_xdomea_process_id(xdomea_0502_pattern_root, message_id)
        self.__generate_0502_message_structure(xdomea_0502_pattern_root)
        self.pattern_schema.assertValid(xdomea_0502_pattern_root)

        return xdomea_0502_pattern_etree

    def __generate_0503_message(self, message_id: str,
                                xdomea_0501_message_etree: etree.ElementTree) -> etree.ElementTree:
        """
        Generate a 0503 xdomea message
        :param message_id: generated uuid to use for the message
        :param xdomea_0501_message_etree: 0501 message to base the 0503 message on
        :return: generated message element tree
        """
        xdomea_0503_pattern_etree = self.__get_message_pattern(self.config.xdomea.pattern_config.message_0503_path)

        xdomea_0501_message_root = xdomea_0501_message_etree.getroot()
        xdomea_0503_pattern_root = xdomea_0503_pattern_etree.getroot()

        self.__set_xdomea_process_id(xdomea_0503_pattern_root, message_id)
        self.__generate_0503_message_structure(xdomea_0501_message_root, xdomea_0503_pattern_root)
        self.__add_document_versions_to_0503_message(xdomea_0503_pattern_root)
        self.pattern_schema.assertValid(xdomea_0503_pattern_etree)

        return xdomea_0503_pattern_etree

    def __generate_0504_message(self, message_id: str) -> etree.ElementTree:
        """
        Generate a 0504 xdomea message
        :param message_id: generated uuid to use for the message
        :return: generated message element tree
        """
        xdomea_0504_pattern_etree = self.__get_message_pattern(self.config.xdomea.pattern_config.message_0504_path)
        xdomea_0504_pattern_root = xdomea_0504_pattern_etree.getroot()
        self.__set_xdomea_process_id(xdomea_0504_pattern_root, message_id)
        self.pattern_schema.assertValid(xdomea_0504_pattern_etree)
        return xdomea_0504_pattern_etree

    def __get_message_pattern(self, path: str) -> etree.ElementTree:
        """
        Get and verify a xdomea message pattern
        :param path: path to the message pattern
        :return: element tree of the message pattern
        """
        parser = etree.XMLParser(remove_blank_text=True)
        message_pattern_etree = etree.parse(
            path,
            parser,  # removes intendation from patterns, necessary for pretty print output
        )
        self.pattern_schema.assertValid(message_pattern_etree)
        return message_pattern_etree

    @staticmethod
    def __set_xdomea_process_id(xdomea_message_root: etree.Element, process_id: str):
        """
        Set process ID for xdomea process (not equal to  the structure element de:Vorgang).
        :param xdomea_message_root: root element of xdomea message
        :param process_id: id to set for the xdomea process
        """
        process_id_element = xdomea_message_root.find(
            './xdomea:Kopf/xdomea:ProzessID',
            namespaces=xdomea_message_root.nsmap,
        )
        assert process_id_element is not None
        process_id_element.text = process_id

    @classmethod
    def __remove_record_object_patterns(cls, xdomea_message_pattern_root: etree.Element):
        """
        Remove record object elements (xdomea:Schriftgutobjekt) from message pattern
        :param xdomea_message_pattern_root: xml tree of the message pattern
        """
        record_object_list = xdomea_message_pattern_root.findall('.//xdomea:Schriftgutobjekt',
                                                                 namespaces=xdomea_message_pattern_root.nsmap)
        for record_object in record_object_list:
            cls.__remove_element(record_object)

    @staticmethod
    def __get_file_patterns(xdomea_message_pattern_root: etree.Element) -> list[etree.Element]:
        """
        Get file pattern xml elements (xdomea:Akte) from message pattern
        :param xdomea_message_pattern_root: xml tree of the message pattern
        :return: list of file pattern xml elements
        """
        return xdomea_message_pattern_root.findall(
            './/xdomea:Akte', namespaces=xdomea_message_pattern_root.nsmap)

    @staticmethod
    def __get_process_patterns(xdomea_message_pattern_root: etree.Element) -> list[etree.Element]:
        """
        Get process pattern xml elements (xdomea:Vorgang) from message pattern
        :param xdomea_message_pattern_root: xml tree of the message pattern
        :return: list of process pattern xml elements
        """
        return xdomea_message_pattern_root.findall(
            './/xdomea:Vorgang', namespaces=xdomea_message_pattern_root.nsmap)

    @staticmethod
    def __get_document_patterns(xdomea_message_pattern_root: etree.Element) -> list[etree.Element]:
        """
        Get document pattern xml elements (xdomea:Dokument) from message pattern
        :param xdomea_message_pattern_root: xml tree of the message pattern
        :return: list of document pattern xml elements
        """
        return xdomea_message_pattern_root.findall(
            './/xdomea:Dokument', namespaces=xdomea_message_pattern_root.nsmap)

    @staticmethod
    def __get_record_object_patterns(xdomea_message_pattern_root: etree.Element) -> list[etree.Element]:
        """
        The elements will be removed from the pattern.
        :param xdomea_message_pattern_root: root element of message pattern
        :return: all record objects from the xdomea message pattern
        """
        record_object_pattern_list = xdomea_message_pattern_root.findall(
            './/xdomea:Schriftgutobjekt', namespaces=xdomea_message_pattern_root.nsmap)
        return record_object_pattern_list

    @classmethod
    def __get_random_pattern(cls, pattern_list: list[etree.Element]) -> etree.Element:
        """
        Randomly chooses pattern from list, creates a copy of the element and changes its ID.
        :param pattern_list: list of xdomea patterns
        :return: chosen xdomea pattern
        """
        # randomly choose pattern
        # deepcopy is necessary if a pattern is used multiple times
        pattern = deepcopy(random.choice(pattern_list))
        # randomize xdomea ID to prevent the same xdomea IDs in the same message
        cls.__randomize_xdomea_id(pattern)
        return pattern

    @staticmethod
    def __get_xdomea_object_id(xdomea_element: etree.Element):
        """
        Get the object id of an xdomea object
        :param xdomea_element: expected xdomea elements --> (de: Akte, de: Vorgang, de: Dokument)
        :return: xdomea object ID
        """
        # find the first ID tag
        id_element = xdomea_element.find(
            './/xdomea:Identifikation/xdomea:ID',
            namespaces=xdomea_element.nsmap,
        )
        assert id_element is not None
        return id_element.text

    @staticmethod
    def __randomize_xdomea_id(xdomea_element: etree.Element):
        """
        Randomizes ID from xdomea element.
        :param xdomea_element: expected xdomea elements --> (de: Akte, de: Vorgang, de: Dokument)
        """
        # change only the first ID tag that is found
        id_element = xdomea_element.find(
            './/xdomea:Identifikation/xdomea:ID',
            namespaces=xdomea_element.nsmap,
        )
        assert id_element is not None
        id_element.text = str(uuid.uuid4())

    def __generate_0501_file_structure(
        self,
        parent: etree.Element,
        file_structure_config: FileStructureConfig,
        is_subfile: bool = False,
    ):
        """
        Generates file or subfile structure for a 0501 xdomea message
        :param parent: parent element of the generated file structure
        :param file_structure_config: configuration for the file or subfile structure
        :param is_subfile: flag if a file or a subfile structure should get generated
        """
        file_number = self.__get_random_number(
            file_structure_config.min_number, file_structure_config.max_number)
        first_file = True
        for file_index in range(file_number):
            # randomly choose file pattern
            file_pattern = self.__get_random_pattern(self.file_pattern_list)
            file_evaluation = self.__set_file_evaluation(file_pattern, first_file)

            self.__clean_file_content(file_pattern)
            file_content = file_pattern.find('./xdomea:Akteninhalt', namespaces=file_pattern.nsmap)

            # generate documents
            if file_structure_config.document_structure:
                self.__generate_0501_document_structure(file_content, file_structure_config.document_structure)

            # generate processes
            if file_structure_config.process_structure:
                self.__generate_0501_process_structure(file_content,
                                                       file_structure_config.process_structure,
                                                       file_evaluation)

            # generate subfiles
            if file_structure_config.subfile_structure:
                # in XDOMEA 3.0.0 subfiles are in Akteninhalt, in 2.3.0 and 2.4.0 they are under the parent files root
                # element
                if self.xdomea_schema_version == "3.0.0":
                    self.__generate_0501_file_structure(file_content, file_structure_config.subfile_structure, True)
                else:
                    self.__generate_0501_file_structure(file_pattern, file_structure_config.subfile_structure, True)

            if is_subfile:
                file_pattern.tag = etree.QName(self.xdomea_namespace, 'Teilakte')
                parent.append(file_pattern)
            else:
                record_object = etree.SubElement(parent, etree.QName(self.xdomea_namespace, 'Schriftgutobjekt'))
                record_object.append(file_pattern)

            first_file = False

    def __clean_file_content(self, file_pattern: etree.Element):
        file_content = file_pattern.find('./xdomea:Akteninhalt', namespaces=file_pattern.nsmap)
        for content_object in list(file_content):
            file_content.remove(content_object)

        if self.xdomea_schema_version in ["2.3.0", "2.4.0"]:
            subfiles = file_pattern.findall('./xdomea:Teilakte', namespaces=file_pattern.nsmap)
            for subfile in subfiles:
                file_pattern.remove(subfile)

    def __set_file_evaluation(self, file_pattern: etree.Element, first_file: bool) -> XdomeaEvaluation:
        """
        Chooses file evaluation dependent on configuration.
        :param file_pattern: xdomea file element extracted from message pattern
        :param first_file: true if file pattern is the first file pattern
        """
        file_id = self.__get_xdomea_object_id(file_pattern)
        file_evaluation = XdomeaEvaluation.EVALUATE
        # first file is always archived to guarantee a valid message structure
        if self.config.structure.file_evaluation == FileEvaluationConfig.ARCHIVE or first_file:
            file_evaluation = XdomeaEvaluation.ARCHIVE
        else: # random evaluation
            file_evaluation = random.choice([XdomeaEvaluation.ARCHIVE, XdomeaEvaluation.DISCARD])
        self.record_object_evaluation[file_id] = file_evaluation
        return file_evaluation

    def __generate_0501_process_structure(self,
                                          parent: etree.Element,
                                          process_structure_config: ProcessStructureConfig,
                                          file_evaluation: XdomeaEvaluation,
                                          is_subprocess: bool = False):
        """
        Generates process or subprocess structure for a 0501 xdomea message.
        :param parent: parent element of the generated process structure
        :param process_structure_config: configuration for the process or subprocess structure
        :param file_evaluation: evaluation configuration of the parent file
        :param is_subprocess: flag if a process or a subprocess structure should get generated
        """
        # randomly choose process number
        process_number = self.__get_random_number(
            process_structure_config.min_number,
            process_structure_config.max_number,
        )

        first_process = True
        for process_index in range(process_number):
            # randomly choose process pattern
            process_pattern = self.__get_random_pattern(self.process_pattern_list)
            self.__set_process_evaluation(process_pattern, file_evaluation, first_process, process_structure_config)

            # clean process pattern
            subprocesses = process_pattern.findall('./xdomea:Teilvorgang', namespaces=process_pattern.nsmap)
            for subprocess in subprocesses:
                process_pattern.remove(subprocess)

            documents = process_pattern.findall('./xdomea:Dokument', namespaces=process_pattern.nsmap)
            for document in documents:
                process_pattern.remove(document)

            # generate documents
            if process_structure_config.document_structure:
                self.__generate_0501_document_structure(process_pattern,
                                                        process_structure_config.document_structure)

            # generate subprocesses
            if process_structure_config.subprocess_structure:
                self.__generate_0501_process_structure(process_pattern,
                                                       process_structure_config.subprocess_structure,
                                                       file_evaluation,
                                                       True)

            if is_subprocess:
                process_pattern.tag = etree.QName(self.xdomea_namespace, 'Teilvorgang')
            parent.append(process_pattern)
            first_process = False

    def __set_process_evaluation(
        self, 
        process_pattern: etree.Element, 
        file_evaluation: XdomeaEvaluation,
        first_process: bool,
        process_structure_config: ProcessStructureConfig
    ):
        """
        Sets process evaluation dependent on configuration and parent file evaluation.
        :param process_pattern: xdomea process element extracted from message pattern
        :param file_evaluation: parent file evaluation
        :param first_process: true if process pattern is the first processed pattern
        :param process_structure_config: configuration of the generated process structure
        """
        process_evaluation = XdomeaEvaluation.EVALUATE
        # first process is always archived to guarantee a valid message structure
        if first_process and file_evaluation == XdomeaEvaluation.ARCHIVE:
            process_evaluation = XdomeaEvaluation.ARCHIVE
        # process evaluation is equal to file evaluation if file evaluation is discard or evaluate
        # process evaluation is also equal to file evaluation if processes are configured to inherit
        elif file_evaluation != XdomeaEvaluation.ARCHIVE \
                or process_structure_config.process_evaluation == 'inherit':
            process_evaluation = file_evaluation
        else: # random evaluation
            process_evaluation = random.choice([XdomeaEvaluation.ARCHIVE, XdomeaEvaluation.DISCARD])
        process_id = self.__get_xdomea_object_id(process_pattern)
        self.record_object_evaluation[process_id] = process_evaluation

    def __generate_0501_document_structure(self,
                                           parent: etree.Element,
                                           document_structure_config: DocumentStructureConfig):
        """
        Generates document structure for a 0501 xdomea message.
        :param parent: parent element of the generated document structure
        :param document_structure_config: configuration for the document structure
        """
        # randomly choose document number for process pattern
        document_number = self.__get_random_number(
            document_structure_config.min_number,
            document_structure_config.max_number,
        )
        for document_index in range(document_number):
            # randomly choose document pattern
            document_pattern = self.__get_random_pattern(self.document_pattern_list)
            parent.append(document_pattern)

    @classmethod
    def __replace_record_object_placeholder(cls, xdomea_0501_pattern_root: etree.Element):
        """
        Replaces all placeholders in the 0501 message with corresponding numbers.
        :param xdomea_0501_pattern_root: root element of 0501 message
        """
        file_list = xdomea_0501_pattern_root.findall(
            './/xdomea:Schriftgutobjekt/xdomea:Akte',
            namespaces=xdomea_0501_pattern_root.nsmap,
        )
        for file_id, file in enumerate(file_list):
            file_plan = file.find(
                './xdomea:AllgemeineMetadaten/xdomea:Aktenplaneinheit/xdomea:Kennzeichen',
                namespaces=xdomea_0501_pattern_root.nsmap,
            )
            file_plan_id = '' if file_plan is None else file_plan.text
            cls.__replace_placeholder(file, '{AP}', file_plan_id)
            cls.__replace_placeholder(file, '{Ax}', str(file_id+1))
            process_list = file.findall(
                './xdomea:Akteninhalt/xdomea:Vorgang',
                namespaces=xdomea_0501_pattern_root.nsmap,
            )
            for process_id, process in enumerate(process_list):
                cls.__replace_placeholder(process, '{Vx}', str(process_id+1))
                document_list = process.findall(
                    './xdomea:Dokument',
                    namespaces=xdomea_0501_pattern_root.nsmap,
                )
                for document_id, document in enumerate(document_list):
                    cls.__replace_placeholder(document, '{Dx}', str(document_id+1))

    @staticmethod
    def __replace_placeholder(
        element: etree.Element,
        placeholder: str, 
        replacement: str,
    ):
        """
        Replaces all placeholders in element.
        :param element: element that contains placeholder
        :param placeholder: placeholder string
        :param replacement: text with which the placeholder is replaced
        """
        elements_with_placeholder = element.xpath(
            './/*[contains(text(), "' + placeholder + '")]',
            namespaces=element.nsmap,
        )
        for element in elements_with_placeholder:
            element.text = element.text.replace(placeholder, replacement)

    def __generate_0502_message_structure(self, xdomea_0502_pattern_root: etree.Element):
        record_object_evaluation_pattern_list = xdomea_0502_pattern_root.findall(
            './/xdomea:BewertetesObjekt', namespaces=xdomea_0502_pattern_root.nsmap)

        # remove all record object evaluation patterns from message pattern
        for evaluation_pattern in record_object_evaluation_pattern_list:
            xdomea_0502_pattern_root.remove(evaluation_pattern)

        # verify that there is at least one evaluation pattern
        assert len(record_object_evaluation_pattern_list) >= 1, \
            'Mindestens ein Bewertungspattern ist notwendig'

        for record_object_id, evaluation in self.record_object_evaluation.items():
            evaluation_pattern = deepcopy(record_object_evaluation_pattern_list[0])

            # set uuid
            id_element = evaluation_pattern.find('.//xdomea:ID', namespaces=evaluation_pattern.nsmap)
            id_element.text = record_object_id

            # set evaluation code
            evaluation_code_element = evaluation_pattern.find('.//code')
            evaluation_code_element.text = evaluation

            xdomea_0502_pattern_root.append(evaluation_pattern)

    def __generate_0503_message_structure(
        self, 
        xdomea_0501_pattern_root: etree.Element,
        xdomea_0503_pattern_root: etree.Element,
    ):
        """
        Generates xdomea 0503 message structure with the configured constraints.
        Extracts the document version patterns from 0503 message.
        The record objects from the 0501 message are copied in the 0503 message.
        The record objects from the 0503 message are discarded.
        :param xdomea_0501_pattern_root: root element of 0501 message
        :param xdomea_0503_pattern_root: root element of 0503 message
        """
        # extract document version pattern before removing record objects from 0503 message
        self.document_version_pattern_list = xdomea_0503_pattern_root.findall(
            './/xdomea:Dokument/xdomea:Version',
            namespaces=xdomea_0503_pattern_root.nsmap,
        )
        record_object_pattern_list_0501 = self.__get_record_object_patterns(
            xdomea_0501_pattern_root)
        record_object_pattern_list_0503 = self.__get_record_object_patterns(
            xdomea_0503_pattern_root)
        # remove all record objects from xdomea 0503 pattern
        for record_object_pattern in record_object_pattern_list_0503:
            self.__remove_element(record_object_pattern)
        # add all record objects from xdomea 0501 pattern to 0503 message
        for record_object_pattern in record_object_pattern_list_0501:
            xdomea_0503_pattern_root.append(deepcopy(record_object_pattern))
        self.__apply_object_evaluation_to_0503_message(xdomea_0503_pattern_root)

    @staticmethod
    def __get_record_object(
        xdomea_message_root: etree.Element,
        id: str,
    ) -> Optional[etree.Element]:
        """
        :param xdomea_message_root: root element of xdomea message
        :param id: ID of target record object
        :return: record object with given ID or None if object with ID doesn't exist
        """
        object_xpath = \
            './/xdomea:Identifikation/xdomea:ID[contains(text(), "' + id + '")]/../..'
        # xpath search is necessary for search with namespace and text content search
        record_object_list = xdomea_message_root.xpath(
            object_xpath,
            namespaces=xdomea_message_root.nsmap,
        )
        # the xdomea message is invalid if more than one object is found 
        assert len(record_object_list) < 2
        # if exactly one object is found, return it
        if len(record_object_list) == 1:
            return record_object_list[0]

    def __apply_object_evaluation_to_0503_message(self, xdomea_0503_pattern_root: etree.Element):
        """
        Sets evaluation that was chosen while generating the 0501 message.
        Record objects with a discard evaluation will be removed from 0503 message.
        :param xdomea_0503_pattern_root: root element of 0503 message
        """
        for object_id, evaluation in self.record_object_evaluation.items():
            record_object = self.__get_record_object(xdomea_0503_pattern_root, object_id)
            # record object can be null if parent record object was already removed
            if record_object is not None:
                if evaluation == XdomeaEvaluation.DISCARD:
                    self.__remove_record_object(record_object)
                else:
                    self.__set_xdomea_evaluation(record_object, evaluation)

    @staticmethod
    def __remove_element(element: etree.Element):
        """
        Removes element from xml tree.
        :param element: element from xml tree
        """
        parent = element.getparent()
        assert parent is not None
        parent.remove(element)

    @classmethod
    def __remove_elements(cls, element_list: list[etree.Element]):
        """
        Removes all elements in list from xml tree.
        :param element_list: list of elements from xml tree
        """
        for element in element_list:
            cls.__remove_element(element)

    @classmethod
    def __remove_record_object(cls, record_object: etree.Element):
        """
        Removes record object from xdomea message.
        :param record_object: record_object from xdomea message
        """
        xdomea_namespace = '{' + record_object.nsmap['xdomea'] + '}'
        parent = record_object.getparent()
        if parent.tag == xdomea_namespace + 'Schriftgutobjekt':
            cls.__remove_element(parent)
        else:
            cls.__remove_element(record_object)

    def __set_xdomea_evaluation(self, record_object: etree.Element, evaluation: XdomeaEvaluation):
        """
        Set the evaluation of the record object.
        Creates necessary structures if the pattern doesn't provide them.
        :param record_object: record_object from xdomea message
        """
        expected_tag_list = [etree.QName(self.xdomea_namespace, tag_name)
                             for tag_name in ['Akte', 'Vorgang', 'Teilakte', 'Teilvorgang']]

        assert record_object.tag in expected_tag_list
        metadata_archive_el = record_object.find(
            './xdomea:ArchivspezifischeMetadaten', 
            namespaces=record_object.nsmap,
        )
        if metadata_archive_el is None:
            predecessor_el = record_object.find(
                'xdomea:AllgemeineMetadaten', 
                namespaces=record_object.nsmap,
            )
            if predecessor_el is None:
                predecessor_el = record_object.find(
                    'xdomea:Identifikation', 
                    namespaces=record_object.nsmap,
                )
            metadata_archive_el = etree.Element(etree.QName(self.xdomea_namespace, 'ArchivspezifischeMetadaten'))
            predecessor_el.addnext(metadata_archive_el)
        self.__add_evaluation_element(metadata_archive_el, evaluation)

    def __add_evaluation_element(
        self, 
        metadata_archive_el: etree.Element, 
        evaluation: XdomeaEvaluation,
    ):
        xdomea_namespace = '{' + metadata_archive_el.nsmap['xdomea'] + '}'
        evaluation_el = metadata_archive_el.find(
            './xdomea:Aussonderungsart', 
            namespaces=metadata_archive_el.nsmap,
        )
        if evaluation_el is None:
            evaluation_el = etree.SubElement(
                metadata_archive_el, 
                etree.QName(self.xdomea_namespace, 'Aussonderungsart'),
            )
        evaluation_el = self.__get_version_dependent_evaluation_element(evaluation_el)
        evaluation_code_el = evaluation_el.find('code')
        if evaluation_code_el is None:
            evaluation_code_el = etree.SubElement(evaluation_el, 'code')
        evaluation_code_el.text = evaluation

    def __get_version_dependent_evaluation_element(self, evaluation_el: etree.Element):
        if self.xdomea_schema_version == '3.0.0':
            evaluation_predefined_el = evaluation_el.find(
                './xdomea:Aussonderungsart', 
                namespaces=evaluation_el.nsmap,
            )
            if evaluation_predefined_el is None:
                xdomea_namespace = '{' + evaluation_el.nsmap['xdomea'] + '}'
                evaluation_predefined_el = etree.SubElement(
                    evaluation_el, 
                    etree.QName(self.xdomea_namespace, 'Aussonderungsart'),
                    listURI='urn:xoev-de:xdomea:codeliste:aussonderungsart',
                    listVersionID='1.0'
                )
            return evaluation_predefined_el
        else:
            return evaluation_el

    def __add_document_versions_to_0503_message(
            self,
            xdomea_0503_pattern_root: etree.Element,
            structure_config: Union[FileStructureConfig, ProcessStructureConfig, DocumentStructureConfig] = None,
            xpath_prefix: str = './xdomea:Schriftgutobjekt/xdomea:Akte/xdomea:Akteninhalt',
    ):
        if structure_config is None:
            structure_config = self.config.structure

        if type(structure_config) is FileStructureConfig:
            if structure_config.subfile_structure:
                self.__add_document_versions_to_0503_message(xdomea_0503_pattern_root,
                                                             structure_config.subfile_structure,
                                                             xpath_prefix + '/xdomea:Teilakte/xdomea:Akteninhalt')

            if structure_config.process_structure:
                self.__add_document_versions_to_0503_message(xdomea_0503_pattern_root,
                                                             structure_config.process_structure,
                                                             xpath_prefix + '/xdomea:Vorgang')

            if structure_config.document_structure:
                self.__add_document_versions_to_0503_message(xdomea_0503_pattern_root,
                                                             structure_config.document_structure,
                                                             xpath_prefix)

        elif type(structure_config) is ProcessStructureConfig:
            if structure_config.subprocess_structure:
                self.__add_document_versions_to_0503_message(xdomea_0503_pattern_root,
                                                             structure_config.subprocess_structure,
                                                             xpath_prefix + '/xdomea:Teilvorgang')

            if structure_config.document_structure:
                self.__add_document_versions_to_0503_message(xdomea_0503_pattern_root,
                                                             structure_config.document_structure,
                                                             xpath_prefix)

        elif type(structure_config) is DocumentStructureConfig:
            FileUtil.extract_xdomea_file_format_list(
                self.config.xdomea.file_type_code_list_path,
                self.config.xdomea.version,
            )
            FileUtil.init_file_pool(self.config.test_data.root_dir)
            document_list = xdomea_0503_pattern_root.findall(
                xpath_prefix + '/xdomea:Dokument',
                namespaces=xdomea_0503_pattern_root.nsmap,
            )
            self.document_version_info_list = []
            for document in document_list:
                version_list = document.findall(
                    './xdomea:Version',
                    namespaces=xdomea_0503_pattern_root.nsmap,
                )
                self.__remove_elements(version_list)
                # randomly choose document version number for document pattern
                version_number = self.__get_random_number(
                    structure_config.version_structure.min_number,
                    structure_config.version_structure.max_number,
                )
                for version_index in range(version_number):
                    self.__add_document_version(document)

    def __add_document_version(self, document_el: etree.Element):
        if len(self.document_version_pattern_list) > 0:
            pattern = deepcopy(random.choice(self.document_version_pattern_list))
        else:
            pattern = etree.Element(
                etree.QName(self.xdomea_namespace, 'Version'),
                nsmap=document_el.nsmap,
            )
        self.__find_version_predecessor(document_el).addnext(pattern)
        version_number_el = pattern.find('xdomea:Nummer', namespaces=document_el.nsmap)
        if version_number_el is None:
            version_number_el = etree.SubElement(
                pattern,
                etree.QName(self.xdomea_namespace, 'Nummer'),
                nsmap=document_el.nsmap,
            )
        version_number_el.text = self.__get_random_version_number();
        format_el = pattern.find('xdomea:Format', namespaces=document_el.nsmap)
        if format_el is None:
            format_el = etree.Element(
                etree.QName(self.xdomea_namespace, 'Format'),
                nsmap=document_el.nsmap,
            )
            version_number_el.addnext(format_el)
        file_info = FileUtil.get_file_info(FileUtil.next_file())
        self.document_version_info_list.append(file_info)
        self.__add_format_info(format_el, file_info)
        self.__add_primary_file(format_el, file_info)

    @staticmethod
    def __find_version_predecessor(document_el: etree.Element) -> etree.Element:
        predecessor_tag_list = [
            'xdomea:InternerGeschaeftsgang',
            'xdomea:HistorienProtokollInformation',
            'xdomea:Typ',
            'xdomea:Bearbeiter',
            'xdomea:Hier',
            'xdomea:Bezug',
            'xdomea:DatumDesSchreibens',
            'xdomea:Postausgangsdatum',
            'xdomea:Posteingangsdatum',
            'xdomea:FremdesGeschaeftszeichen',
            'xdomea:AllgemeineMetadaten',
            'xdomea:Identifikation',
        ]
        for predecessor_tag in predecessor_tag_list:
            predecessor = document_el.find(predecessor_tag, namespaces=document_el.nsmap)
            if predecessor is not None:
                return predecessor
        raise Exception('Vorgänger Element von Dokumentenversion nicht gefunden')

    def __add_format_info(self, format_el: etree.Element, file_info: FileInfo):
        format_name_el = format_el.find('xdomea:Name', namespaces=format_el.nsmap)
        if format_name_el is None:
            format_name_el = etree.SubElement(
                format_el,
                etree.QName(self.xdomea_namespace, 'Name'),
                nsmap=format_el.nsmap,
            )
        code_el = format_name_el.find('code')
        if code_el is None:
            code_el = etree.Element('code')
            format_name_el.insert(0, code_el)
        code_el.text = file_info.xdomea_file_format.code
        # ToDo: research reason why name element in code element for format name is prohibited
        #       concerns only xdomea 3.0.0
        if self.xdomea_schema_version != '3.0.0':
            name_el = format_name_el.find('name')
            if name_el is None:
                name_el = etree.Element('name')
                code_el.addnext(name_el)
            name_el.text = file_info.xdomea_file_format.name
        if file_info.xdomea_file_format.name == 'Sonstiges':
            other_name_el = format_el.find('xdomea:SonstigerName', namespaces=format_el.nsmap)
            if other_name_el is None:
                other_name_el = etree.Element(
                    etree.QName(self.xdomea_namespace, 'SonstigerName'),
                    nsmap=format_el.nsmap,
                )
                format_name_el.addnext(other_name_el)
            other_name_el.text = file_info.detected_format_name
            self.__add_format_version(format_el, other_name_el, file_info)
        else:
            self.__add_format_version(format_el, format_name_el, file_info)

    def __add_format_version(
        self,
        format_el: etree.Element,
        predecessor_el: etree.Element,
        file_info: FileInfo,
    ):
        version_el = format_el.find('xdomea:Version', namespaces=format_el.nsmap)
        if version_el is None:
            version_el = etree.Element(
                etree.QName(self.xdomea_namespace, 'Version'),
                nsmap=format_el.nsmap,
            )
            predecessor_el.addnext(version_el)
        version_el.text = file_info.detected_format_version

    def __add_primary_file(
        self,
        format_el: etree.Element,
        file_info: FileInfo,
    ):
        file_el = format_el.find('xdomea:Primaerdokument', namespaces=format_el.nsmap)
        if file_el is None:
            file_el = etree.Element(
                etree.QName(self.xdomea_namespace, 'Primaerdokument'),
                nsmap=format_el.nsmap,
            )
            format_el.append(file_el)
        file_name_el = file_el.find('xdomea:Dateiname', namespaces=format_el.nsmap)
        if file_name_el is None:
            file_name_el = etree.Element(
                etree.QName(self.xdomea_namespace, 'Dateiname'),
                nsmap=format_el.nsmap,
            )
            file_el.insert(0, file_name_el)
        file_name_el.text = file_info.xdomea_file_name

    def __export_message(
        self,
        process_id: str,
        message_etree: etree,
        message_name: str
    ):
        """
        Export a xdomea message as zip archive
        :param process_id: uuid of the message
        :param message_etree: xml element tree of the message
        :param message_name: name pattern for the message
        """
        export_dir = os.path.join(self.config.output_dir, process_id)
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        message_name = process_id + message_name
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
            for version_info in self.document_version_info_list:
                z.write(version_info.path, version_info.xdomea_file_name)
                # set original ntfs timestamps on windows systems
                if os.name == 'nt':
                    ZipUtil.add_ntfs_info(z, version_info.path, version_info.xdomea_file_name)
        print(message_path)

    @staticmethod
    def __get_random_number(min: int, max: int) -> int:
        """
        Necessary because range function fails if min equals max.
        :param min: min number of random range
        :param max: max number of random range
        :return random number in range
        """
        # max + 1 is necessary so that max is included in the range
        return min if min == max else random.choice(range(min, max+1))

    @staticmethod
    def __get_random_version_number() -> str:
        version_format = '{:4.2f}'
        version_number = random.random() * 10
        return version_format.format(version_number)


def main():
    message_generator = XdomeaMessageGenerator()
    message_generator.read_config('config/generator_config.xml', 'config/generator_config.xsd')
    message_generator.generate_xdomea_messages()
    # pause until user confirmation on windows
    if os.name == 'nt':
        print('\n')
        os.system("pause")


if __name__ == '__main__':
    main()
