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
from lib.util.config import ConfigParser, FileEvaluationConfig
from lib.util.file import FileInfo, FileUtil
from lib.util.zip import ZipUtil
from lxml import etree
import os
from pathlib import Path
import random
from typing import Optional
import uuid
import zipfile


@dataclass
class XdomeaRegexConfig:
    xdomea_0501_message_name: str
    xdomea_0503_message_name: str


class XdomeaEvaluation(str, Enum):
    EVALUATE = 'B'
    ARCHIVE = 'A'
    DISCARD = 'V'


class XdomeaMessageGenerator:

    def __init__(self):
        self.regex_config = XdomeaRegexConfig(
            xdomea_0501_message_name='_Aussonderung.Anbieteverzeichnis.0501',
            xdomea_0503_message_name='_Aussonderung.Aussonderung.0503',
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
        Parses xdomea message patterns and validates against the pattern schema.
        """
        generated_message_ID = str(uuid.uuid4())
        pattern_schema_tree = etree.parse(self.config.xdomea.schema_path)
        self.xdomea_schema_version = pattern_schema_tree.getroot().get('version')
        assert self.xdomea_schema_version == self.config.xdomea.version,\
            'konfigurierte Version und Version der xdomea Schemadatei sind ungleich'
        pattern_schema = etree.XMLSchema(pattern_schema_tree)
        parser = etree.XMLParser(remove_blank_text=True)
        xdomea_0501_pattern_etree = etree.parse(
            self.config.xdomea.pattern_config.message_0501_path, 
            parser, # removes indentation from patterns, necessary for pretty print output
        )
        pattern_schema.assertValid(xdomea_0501_pattern_etree)
        xdomea_0503_pattern_etree = etree.parse(
            self.config.xdomea.pattern_config.message_0503_path,
            parser, # removes indentation from patterns, necessary for pretty print output
        )
        pattern_schema.assertValid(xdomea_0503_pattern_etree)
        xdomea_0501_pattern_root = xdomea_0501_pattern_etree.getroot()
        self.__set_xdomea_process_id(xdomea_0501_pattern_root, generated_message_ID)
        # de: record object - Schriftgutobjekt
        record_object_pattern_list = self.__get_record_object_patterns(xdomea_0501_pattern_root)
        # remove all record objects from xdomea 0501 pattern
        for record_object_pattern in record_object_pattern_list:
            self.__remove_element(record_object_pattern)
        self.__generate_0501_file_structure(
            xdomea_0501_pattern_root,
            record_object_pattern_list,
        )
        self.__replace_record_object_placeholder(xdomea_0501_pattern_root);
        pattern_schema.assertValid(xdomea_0501_pattern_etree)
        xdomea_0503_pattern_root = xdomea_0503_pattern_etree.getroot()
        self.__set_xdomea_process_id(xdomea_0503_pattern_root, generated_message_ID)
        self.__generate_0503_message_structure(xdomea_0501_pattern_root, xdomea_0503_pattern_root)
        self.__add_document_versions_to_0503_message(xdomea_0503_pattern_root)
        pattern_schema.assertValid(xdomea_0503_pattern_etree)
        # export messages
        print('\nexportiere Aussonderungsnachrichten:\n')
        self.__export_0501_message(
            generated_message_ID,
            xdomea_0501_pattern_etree,
        )
        self.__export_0503_message(
            generated_message_ID,
            xdomea_0503_pattern_etree,
        )
        # clear record object evaluations for next message generation
        self.record_object_evaluation.clear()

    def __set_xdomea_process_id(self, xdomea_message_root: etree.Element, process_id: str):
        """
        Set process ID for xdomea process (not equal to  the structure element de:Vorgang).
        :param xdomea_message_root: root element of xdomea message
        """
        process_id_element = xdomea_message_root.find(
            './xdomea:Kopf/xdomea:ProzessID',
            namespaces=xdomea_message_root.nsmap,
        )
        assert process_id_element is not None
        process_id_element.text = process_id

    def __get_record_object_patterns(
        self, 
        xdomea_message_pattern_root: etree.Element,
    ) -> list[etree.Element]:
        """
        The elements will be removed from the pattern.
        :param xdomea_message_pattern_root: root element of message pattern
        :return: all record objects from the xdomea message pattern
        """
        record_object_pattern_list = xdomea_message_pattern_root.findall(
            './/xdomea:Schriftgutobjekt', namespaces=xdomea_message_pattern_root.nsmap)
        return record_object_pattern_list

    def __get_random_pattern(self, pattern_list: list[etree.Element]) -> etree.Element:
        """
        Randomly chooses pattern from list, creates a copy of the element and changes its ID.
        :param pattern_list: list of xdomea patterns
        :return: chosen xdomea pattern
        """
        # randomly choose pattern
        # deepcopy is necessary if a pattern is used multiple times
        pattern = deepcopy(random.choice(pattern_list))
        # randomize xdomea ID to prevent the same xdomea IDs in the same message
        self.__randomize_xdomea_id(pattern)
        return pattern

    def __get_xdomea_object_id(self, xdomea_element: etree.Element):
        """
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

    def __randomize_xdomea_id(self, xdomea_element: etree.Element):
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
        xdomea_0501_pattern_root: etree.Element,
        record_object_pattern_list: list[etree.Element],
    ):
        """
        Generates xdomea 0501 message structure with the configured constraints.
        :param xdomea_0501_pattern_root: root element of 0501 message
        """
        # check if necessary structure exists in 0501 pattern
        xpath = './xdomea:Akte/xdomea:Akteninhalt/xdomea:Vorgang/xdomea:Dokument'
        file_pattern_list = [p for p in record_object_pattern_list 
            if p.find(xpath, namespaces=xdomea_0501_pattern_root.nsmap) is not None]
        assert file_pattern_list, 'kein Muster für Struktur Akte/Vorgang/Dokument definiert'
        # randomly choose file number for xdomea 0501 message
        file_number = self.__get_random_number(
            self.config.structure.min_number, self.config.structure.max_number)
        first_file = True
        for file_index in range(file_number):
            # randomly choose file pattern
            file_pattern = self.__get_random_pattern(file_pattern_list)
            self.__set_file_evaluation(file_pattern, first_file)
            self.__generate_0501_process_structure(file_pattern)
            # add file pattern to message
            xdomea_0501_pattern_root.append(file_pattern)
            first_file = False

    def __set_file_evaluation(self, file_pattern: etree.Element, first_file: bool):
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
            file_evaluation = random.choice(list(XdomeaEvaluation))
        self.record_object_evaluation[file_id] = file_evaluation

    def __generate_0501_process_structure(self, file_pattern: etree.Element):
        """
        Sets process structure for file pattern with the configured constraints.
        :param file_pattern: xdomea file element extracted from message pattern
        """
        file_content_element = file_pattern.find(
            './xdomea:Akte/xdomea:Akteninhalt',
            namespaces=file_pattern.nsmap,
        )
        process_pattern_list = file_content_element.findall(
            './xdomea:Vorgang',
            namespaces=file_content_element.nsmap,
        )
        # remove all process elements from file pattern
        for process_pattern in process_pattern_list:
            self.__remove_element(process_pattern)
        # randomly choose process number for file pattern
        process_number = self.__get_random_number(
            self.config.structure.process_structure.min_number, 
            self.config.structure.process_structure.max_number,
        )
        # get parent file info
        file_id = self.__get_xdomea_object_id(file_pattern)
        file_evaluation = self.record_object_evaluation[file_id]
        first_process = True
        for process_index in range(process_number):
            # randomly choose process pattern
            process_pattern = self.__get_random_pattern(process_pattern_list)
            self.__set_process_evaluation(process_pattern, file_evaluation, first_process)
            self.__generate_0501_document_structure(process_pattern)
            file_content_element.append(process_pattern)
            first_process = False

    def __set_process_evaluation(
        self, 
        process_pattern: etree.Element, 
        file_evaluation: XdomeaEvaluation,
        first_process: bool,
    ):
        """
        Sets process evaluation dependent on configuration and parent file evaluation.
        :param process_pattern: xdomea process element extracted from message pattern
        :param file_evaluation: parent file evaluation
        :param first_process: true if process pattern is the first processed pattern
        """
        process_evaluation = XdomeaEvaluation.EVALUATE
        # first process is always archived to guarantee a valid message structure
        if first_process and file_evaluation == XdomeaEvaluation.ARCHIVE:
            process_evaluation = XdomeaEvaluation.ARCHIVE
        # process evaluation is equal to file evaluation if file evaluation is discard or evaluate
        # process evaluation is also equal to file evaluation if processes are configured to inherit
        elif file_evaluation != XdomeaEvaluation.ARCHIVE or\
        self.config.structure.process_structure.process_evaluation == 'inherit':
            process_evaluation = file_evaluation
        else: # random evaluation
            process_evaluation = random.choice(list(XdomeaEvaluation))
        process_id = self.__get_xdomea_object_id(process_pattern)
        self.record_object_evaluation[process_id] = process_evaluation

    def __generate_0501_document_structure(self, process_pattern: etree.Element):
        """
        Generates document structure for process pattern with the configured constraints.
        :param process_pattern: xdomea process element extracted from message pattern
        """
        document_pattern_list = process_pattern.findall(
            './xdomea:Dokument',
            namespaces=process_pattern.nsmap,
        )
        # remove all document elements from process pattern
        for document_pattern in document_pattern_list:
            self.__remove_element(document_pattern)
        # randomly choose document number for process pattern
        document_number = self.__get_random_number(
            self.config.structure.process_structure.document_structure.min_number, 
            self.config.structure.process_structure.document_structure.max_number,
        )
        for document_index in range(document_number):
            # randomly choose document pattern
            document_pattern = self.__get_random_pattern(document_pattern_list)
            process_pattern.append(document_pattern)

    def __replace_record_object_placeholder(self, xdomea_0501_pattern_root: etree.Element):
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
            self.__replace_placeholder(file, '{AP}', file_plan_id)
            self.__replace_placeholder(file, '{Ax}', str(file_id+1))
            process_list = file.findall(
                './xdomea:Akteninhalt/xdomea:Vorgang',
                namespaces=xdomea_0501_pattern_root.nsmap,
            )
            for process_id, process in enumerate(process_list):
                self.__replace_placeholder(process, '{Vx}', str(process_id+1))
                document_list = process.findall(
                    './xdomea:Dokument',
                    namespaces=xdomea_0501_pattern_root.nsmap,
                )
                for document_id, document in enumerate(document_list):
                    self.__replace_placeholder(document, '{Dx}', str(document_id+1))

    def __replace_placeholder(
        self, 
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

    def __get_record_object(
        self, 
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

    def __remove_element(self, element: etree.Element):
        """
        Removes element from xml tree.
        :param element: element from xml tree
        """
        parent = element.getparent()
        assert parent is not None
        parent.remove(element)

    def __remove_elements(self, element_list: list[etree.Element]):
        """
        Removes all elements in list from xml tree.
        :param element_list: list of elements from xml tree
        """
        for element in element_list:
            self.__remove_element(element)

    def __remove_record_object(self, record_object: etree.Element):
        """
        Removes record object from xdomea message.
        :param record_object: record_object from xdomea message
        """
        xdomea_namespace = '{' + record_object.nsmap['xdomea'] + '}'
        parent = record_object.getparent()
        if parent.tag == xdomea_namespace + 'Schriftgutobjekt':
            self.__remove_element(parent)
        else:
            self.__remove_element(record_object)

    def __set_xdomea_evaluation(self, record_object: etree.Element, evaluation: XdomeaEvaluation):
        """
        Set the evaluation of the record object.
        Creates necessary structures if the pattern doesn't provide them.
        :param record_object: record_object from xdomea message
        """
        xdomea_namespace = '{' + record_object.nsmap['xdomea'] + '}'
        expected_tag_list = [xdomea_namespace + 'Akte', xdomea_namespace + 'Vorgang']
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
            metadata_archive_el = etree.Element(xdomea_namespace+'ArchivspezifischeMetadaten')
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
                xdomea_namespace+'Aussonderungsart',
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
                    xdomea_namespace+'Aussonderungsart',
                    listURI='urn:xoev-de:xdomea:codeliste:aussonderungsart',
                    listVersionID='1.0'
                )
            return evaluation_predefined_el
        else:
            return evaluation_el

    def __add_document_versions_to_0503_message(self, xdomea_0503_pattern_root: etree.Element):
        FileUtil.extract_xdomea_file_format_list(
            self.config.xdomea.file_type_code_list_path,
            self.config.xdomea.version,
        )
        FileUtil.init_file_pool(self.config.test_data.root_dir)
        document_list = xdomea_0503_pattern_root.findall(
            './/xdomea:Dokument',
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
                self.config.structure.process_structure.document_structure\
                    .version_structure.min_number, 
                self.config.structure.process_structure.document_structure\
                    .version_structure.max_number,
            )
            for version_index in range(version_number):
                self.__add_document_version(document)

    def __add_document_version(self, document_el: etree.Element):
        xdomea_namespace = '{' + document_el.nsmap['xdomea'] + '}'
        if len(self.document_version_pattern_list) > 0:
            pattern = deepcopy(random.choice(self.document_version_pattern_list))
        else:
            pattern = etree.Element(
                xdomea_namespace+'Version', 
                nsmap=document_el.nsmap,
            )
        self.__find_version_predecessor(document_el).addnext(pattern)
        version_number_el = pattern.find('xdomea:Nummer', namespaces=document_el.nsmap)
        if version_number_el is None:
            version_number_el = etree.SubElement(
                pattern,
                xdomea_namespace+'Nummer',
                nsmap=document_el.nsmap,
            )
        version_number_el.text = self.__get_random_version_number();
        format_el = pattern.find('xdomea:Format', namespaces=document_el.nsmap)
        if format_el is None:
            format_el = etree.Element(
                xdomea_namespace+'Format',
                nsmap=document_el.nsmap,
            )
            version_number_el.addnext(format_el)
        file_info = FileUtil.get_file_info(FileUtil.next_file())
        self.document_version_info_list.append(file_info)
        self.__add_format_info(format_el, file_info)
        self.__add_primary_file(format_el, file_info)

    def __find_version_predecessor(self, document_el: etree.Element) -> etree.Element:
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
        xdomea_namespace = '{' + format_el.nsmap['xdomea'] + '}'
        format_name_el = format_el.find('xdomea:Name', namespaces=format_el.nsmap)
        if format_name_el is None:
            format_name_el = etree.SubElement(
                format_el,
                xdomea_namespace+'Name',
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
                    xdomea_namespace+'SonstigerName',
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
        xdomea_namespace = '{' + format_el.nsmap['xdomea'] + '}'
        version_el = format_el.find('xdomea:Version', namespaces=format_el.nsmap)
        if version_el is None:
            version_el = etree.Element(
                xdomea_namespace+'Version',
                nsmap=format_el.nsmap,
            )
            predecessor_el.addnext(version_el)
        version_el.text = file_info.detected_format_version

    def __add_primary_file(
        self,
        format_el: etree.Element,
        file_info: FileInfo,
    ):
        xdomea_namespace = '{' + format_el.nsmap['xdomea'] + '}'
        file_el = format_el.find('xdomea:Primaerdokument', namespaces=format_el.nsmap)
        if file_el is None:
            file_el = etree.Element(
                xdomea_namespace+'Primaerdokument',
                nsmap=format_el.nsmap,
            )
            format_el.append(file_el)
        file_name_el = file_el.find('xdomea:Dateiname', namespaces=format_el.nsmap)
        if file_name_el is None:
            file_name_el = etree.Element(
                xdomea_namespace+'Dateiname',
                nsmap=format_el.nsmap,
            )
            file_el.insert(0, file_name_el)
        file_name_el.text = file_info.xdomea_file_name

    def __export_0501_message(
        self,
        process_ID: str,
        message_etree: etree, 
    ):
        export_dir = os.path.join(self.config.output_dir, process_ID) 
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        message_name = process_ID + self.regex_config.xdomea_0501_message_name
        xml_name = message_name + '.xml'
        zip_name = message_name + '.zip'
        message_path = os.path.join(export_dir, zip_name)
        with zipfile.ZipFile(message_path, 'w') as z:
            with z.open(xml_name, 'w') as f:
                message_etree.write(f, encoding='UTF-8', xml_declaration=True, pretty_print=True)
        print(message_path)

    def __export_0503_message(
        self,
        process_ID: str,
        message_etree: etree, 
    ):
        export_dir = os.path.join(self.config.output_dir, process_ID) 
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        message_name = process_ID + self.regex_config.xdomea_0503_message_name
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
        
    def __get_random_number(self, min: int, max: int) -> int:
        """
        Necessary because range function fails if min equals max.
        :param min: min number of random range
        :param max: max number of random range
        :return random number in range
        """
        # max + 1 is necessary so that max is included in the range
        return min if min == max else random.choice(range(min, max+1))

    def __get_random_version_number(self) -> str:
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
