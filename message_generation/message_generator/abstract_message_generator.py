from lxml import etree
from typing import Optional

from .config import GeneratorConfig
from .helper import remove_element, replace_placeholder, get_record_object_patterns
from .types import XdomeaEvaluation


class AbstractMessageGenerator:
    def __init__(self, config: GeneratorConfig, xdomea_schema: etree.XMLSchema):
        self.xdomea_schema = xdomea_schema
        self.message_pattern_etree = None
        self.message_pattern_root = None
        self.xdomea_namespace = None
        self.config = config
        self.xdomea_schema_version = config.xdomea.version

    def generate_message(self, message_id: str) -> etree.ElementTree:
        raise NotImplementedError()

    def _load_message_pattern(self, pattern_path: str):
        parser = etree.XMLParser(remove_blank_text=True)
        pattern_etree = etree.parse(pattern_path, parser)
        self.xdomea_schema.assertValid(pattern_etree)
        self.message_pattern_etree = pattern_etree
        self.message_pattern_root = pattern_etree.getroot()
        self.xdomea_namespace = self.message_pattern_root.nsmap['xdomea']

    def _set_process_id(self, message_id: str):
        """
        Set process ID for xdomea process (not equal to the structure element de:Vorgang).
        :param message_id: id to set for the xdomea process
        """
        process_id_element = self.message_pattern_root.find(
            './xdomea:Kopf/xdomea:ProzessID',
            namespaces=self.message_pattern_root.nsmap,
        )
        assert process_id_element is not None
        process_id_element.text = message_id

    def _remove_record_object_patterns(self):
        record_object_list = self.message_pattern_root.findall('.//xdomea:Schriftgutobjekt',
                                                               namespaces=self.message_pattern_root.nsmap)
        for record_object in record_object_list:
            remove_element(record_object)

    def _replace_record_object_placeholder(self):
        """
        Replaces all placeholders in the 0501 message with corresponding numbers.
        """
        file_list = self.message_pattern_root.findall(
            './/xdomea:Schriftgutobjekt/xdomea:Akte',
            namespaces=self.message_pattern_root.nsmap,
        )

        # TODO: replace placeholders for complex structures

        for file_id, file in enumerate(file_list):
            file_plan = file.find(
                './xdomea:AllgemeineMetadaten/xdomea:Aktenplaneinheit/xdomea:Kennzeichen',
                namespaces=self.message_pattern_root.nsmap,
            )
            file_plan_id = '' if file_plan is None else file_plan.text
            replace_placeholder(file, '{AP}', file_plan_id)
            replace_placeholder(file, '{Ax}', str(file_id + 1))
            process_list = file.findall(
                './xdomea:Akteninhalt/xdomea:Vorgang',
                namespaces=self.message_pattern_root.nsmap,
            )
            for process_id, process in enumerate(process_list):
                replace_placeholder(process, '{Vx}', str(process_id + 1))
                document_list = process.findall(
                    './xdomea:Dokument',
                    namespaces=self.message_pattern_root.nsmap,
                )
                for document_id, document in enumerate(document_list):
                    replace_placeholder(document, '{Dx}', str(document_id + 1))

    def _get_record_object_patterns(self) -> list[etree.Element]:
        return get_record_object_patterns(self.message_pattern_root)

    def _get_record_object(self, id: str) -> Optional[etree.Element]:
        """
        :param id: ID of target record object
        :return: record object with given ID or None if object with ID doesn't exist
        """
        object_xpath = \
            './/xdomea:Identifikation/xdomea:ID[contains(text(), "' + id + '")]/../..'
        # xpath search is necessary for search with namespace and text content search
        record_object_list = self.message_pattern_root.xpath(
            object_xpath,
            namespaces=self.message_pattern_root.nsmap,
        )
        # the xdomea message is invalid if more than one object is found
        assert len(record_object_list) < 2
        # if exactly one object is found, return it
        if len(record_object_list) == 1:
            return record_object_list[0]

    def _set_xdomea_evaluation(self, record_object: etree.Element, evaluation: XdomeaEvaluation):
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
                evaluation_predefined_el = etree.SubElement(
                    evaluation_el,
                    etree.QName(self.xdomea_namespace, 'Aussonderungsart'),
                    listURI='urn:xoev-de:xdomea:codeliste:aussonderungsart',
                    listVersionID='1.0'
                )
            return evaluation_predefined_el
        else:
            return evaluation_el