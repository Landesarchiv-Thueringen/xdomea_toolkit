import random

from copy import deepcopy
from lxml import etree
from typing import Optional, Union

from .abstract_message_generator import AbstractMessageGenerator
from .config import FileStructureConfig, ProcessStructureConfig, DocumentStructureConfig, SubfileStructureConfig
from .helper import get_record_object_patterns, remove_element, remove_record_object, remove_elements, \
    get_random_number, get_random_version_number
from .file import FileInfo, FileUtil
from .types import XdomeaEvaluation


class Xdomea0503MessageGenerator(AbstractMessageGenerator):

    def __init__(self, xdomea_x0501_message: etree.ElementTree, record_object_evaluation, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xdomea_0501_message_root = xdomea_x0501_message.getroot()
        self.record_object_evaluation = record_object_evaluation
        self.document_version_info_list = []

    def generate_message(self, message_id: str) -> etree.ElementTree:
        self._load_message_pattern(self.config.xdomea.pattern_config.message_0503_path)

        self._set_process_id(message_id)
        self.__generate_message_structure()
        self.__add_document_versions_to_message()

        self.xdomea_schema.assertValid(self.message_pattern_etree)
        return self.message_pattern_etree

    def __generate_message_structure(self):
        # extract document version pattern before removing record objects from 0503 message
        self.document_version_pattern_list = self.message_pattern_root.findall(
            './/xdomea:Dokument/xdomea:Version',
            namespaces=self.message_pattern_root.nsmap,
        )
        record_object_pattern_list_0501 = get_record_object_patterns(self.xdomea_0501_message_root)
        record_object_pattern_list_0503 = self._get_record_object_patterns()

        # remove all record objects from xdomea 0503 pattern
        for record_object_pattern in record_object_pattern_list_0503:
            remove_element(record_object_pattern)

        # add all record objects from xdomea 0501 pattern to 0503 message
        for record_object_pattern in record_object_pattern_list_0501:
            self.message_pattern_root.append(deepcopy(record_object_pattern))
        self.__apply_object_evaluation_to_message()

    def __apply_object_evaluation_to_message(self):
        """
        Sets evaluation that was choosen while generating the 0501 message.
        Record objects with a discard evaluation will be removed from 0503 message.
        """
        for object_id, evaluation in self.record_object_evaluation.items():
            record_object = self._get_record_object(object_id)
            # record object can be null if parent record object was already removed
            if record_object is not None:
                if evaluation == XdomeaEvaluation.DISCARD:
                    remove_record_object(record_object)
                else:
                    self._set_xdomea_evaluation(record_object, evaluation)

    def __add_document_versions_to_message(
            self,
            structure_config: Union[FileStructureConfig, ProcessStructureConfig, DocumentStructureConfig,
                SubfileStructureConfig] = None,
            xpath_prefix: Optional[str] = './xdomea:Schriftgutobjekt/xdomea:Akte',
    ):
        if structure_config is None:
            structure_config = self.config.structure

        if type(structure_config) in [FileStructureConfig, SubfileStructureConfig]:
            if structure_config.subfile_structure:
                if self.xdomea_schema_version == '3.0.0':
                    new_xpath_prefix = xpath_prefix + '/xdomea:Akteninhalt/xdomea:Teilakte'
                    self.__add_document_versions_to_message(structure_config.subfile_structure,
                                                                 new_xpath_prefix)
                else:
                    new_xpath_prefix = xpath_prefix + '/xdomea:Teilakte'
                    self.__add_document_versions_to_message(structure_config.subfile_structure,
                                                                 new_xpath_prefix)

            if structure_config.process_structure:
                new_xpath_prefix = xpath_prefix + '/xdomea:Akteninhalt/xdomea:Vorgang'
                self.__add_document_versions_to_message(structure_config.process_structure,
                                                             new_xpath_prefix)

            if structure_config.document_structure:
                self.__add_document_versions_to_message(structure_config.document_structure,
                                                             xpath_prefix)

        elif type(structure_config) is ProcessStructureConfig:
            if structure_config.subprocess_structure:
                self.__add_document_versions_to_message(structure_config.subprocess_structure,
                                                             xpath_prefix + '/xdomea:Teilvorgang')

            if structure_config.document_structure:
                self.__add_document_versions_to_message(structure_config.document_structure,
                                                             xpath_prefix)

        elif type(structure_config) is DocumentStructureConfig:
            FileUtil.extract_xdomea_file_format_list(
                self.config.xdomea.file_type_code_list_path,
                self.config.xdomea.version,
            )
            FileUtil.init_file_pool(self.config.test_data.root_dir)
            document_list = self.message_pattern_root.findall(
                xpath_prefix + '//xdomea:Dokument',
                namespaces=self.message_pattern_root.nsmap,
            )
            self.document_version_info_list = []
            for document in document_list:
                version_list = document.findall(
                    './xdomea:Version',
                    namespaces=self.message_pattern_root.nsmap,
                )
                remove_elements(version_list)
                # randomly choose document version number for document pattern
                version_number = get_random_number(
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
        version_number_el.text = get_random_version_number()
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