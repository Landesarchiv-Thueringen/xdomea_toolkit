from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from lxml import etree
from pathlib import Path
import os
import random
import uuid


@dataclass
class DocumentStructureConfig:
    min_number: int
    max_number: int


class ProcessEvaluationConfig(Enum):
    INHERIT = 1
    RANDOM = 2


@dataclass
class ProcessStructureConfig:
    min_number: int
    max_number: int
    process_evaluation: ProcessEvaluationConfig
    document_structure: DocumentStructureConfig


class FileEvaluationConfig(Enum):
    ARCHIVE = 1
    RANDOM = 2


@dataclass
class FileStructureConfig:
    min_number: int
    max_number: int
    file_evaluation: FileEvaluationConfig
    process_structure: ProcessStructureConfig


@dataclass
class MessagePatternConfig:
    xdomea_0501_path: str
    xdomea_0503_path: str
    schema_path: str


@dataclass
class TestDataConfig:
    root_dir: str


@dataclass
class GeneratorConfig:
    structure: FileStructureConfig
    message_pattern: MessagePatternConfig
    test_data: TestDataConfig
    output_dir: str


@dataclass
class XdomeaRegexConfig:
    uuid: str
    xdomea_0501_message_name: str
    xdomea_0503_message_name: str


class XdomeaEvaluation(str, Enum):
    EVALUATE = 'B'
    ARCHIVE = 'A'
    DISCARD = 'V'


class XdomeaMessageGenerator:
    config: GeneratorConfig
    regex_config: XdomeaRegexConfig
    record_object_evaluation: dict[str, str]

    def __init__(self):
        self.regex_config = XdomeaRegexConfig(
            uuid='[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            xdomea_0501_message_name='_Aussonderung.Anbieteverzeichnis.0501.xml',
            xdomea_0503_message_name='_Aussonderung.Aussonderung.0503.xml',
        )
        self.record_object_evaluation = {}

    def read_config(self, config_path: str, config_schema_path: str):
        """
        Parses xml config file into object representation. Validates xml config file against schema.
        :param config_path: path of xml config file
        :param config_schema_path: path of xml schema for config file
        """
        config_etree = etree.parse(config_path)
        config_schema_root = etree.parse(config_schema_path)
        config_schema = etree.XMLSchema(config_schema_root)
        config_schema.assertValid(config_etree)
        output_dir = config_etree.findtext('/output_dir')
        self.config = GeneratorConfig(
            structure=self.__read_structure_config(config_etree),
            message_pattern=self.__read_message_pattern_config(config_etree),
            test_data=self.__read_test_data_config(config_etree),
            output_dir=output_dir,
        )
        self.__validate_config()

    def __read_structure_config(self, config_etree: etree.Element) -> FileStructureConfig:
        """
        Parses message structure config into object representation.
        :param config_etree: element tree of xml config
        :return: file structure config
        """
        files_min_number = int(config_etree.findtext('/structure/files/min_number'))
        files_max_number = int(config_etree.findtext('/structure/files/max_number'))
        files_evaluation = FileEvaluationConfig[config_etree.findtext(
            '/structure/files/evaluation').upper()]
        processes_min_number = int(config_etree.findtext('/structure/files/processes/min_number'))
        processes_max_number = int(config_etree.findtext('/structure/files/processes/max_number'))
        processes_evaluation = ProcessEvaluationConfig[config_etree.findtext(
            '/structure/files/processes/evaluation').upper()]
        documents_min_number = int(config_etree.findtext(
            '/structure/files/processes/documents/min_number'))
        documents_max_number = int(config_etree.findtext(
            '/structure/files/processes/documents/max_number'))
        document_structure_config = DocumentStructureConfig(
            min_number=documents_min_number,
            max_number=documents_max_number,
        )
        process_structure_config = ProcessStructureConfig(
            min_number=processes_min_number,
            max_number=processes_max_number,
            process_evaluation=processes_evaluation,
            document_structure=document_structure_config,
        )
        return FileStructureConfig(
            min_number=files_min_number,
            max_number=files_max_number,
            file_evaluation=files_evaluation,
            process_structure=process_structure_config,
        )

    def __read_message_pattern_config(self, config_etree: etree.Element) -> MessagePatternConfig:
        """
        Parses message pattern config into object representation.
        :param config_etree: element tree of xml config
        :return: message pattern config
        """
        xdomea_0501_path = config_etree.findtext('/message_pattern/xdomea_0501_path')
        xdomea_0503_path = config_etree.findtext('/message_pattern/xdomea_0503_path')
        schema_path = config_etree.findtext('/message_pattern/schema_path')
        return MessagePatternConfig(
            xdomea_0501_path=xdomea_0501_path,
            xdomea_0503_path=xdomea_0503_path,
            schema_path=schema_path,
        )

    def __read_test_data_config(self, config_etree: etree.Element) -> TestDataConfig:
        """
        Parses test data config into object representation.
        :param config_etree: element tree of xml config
        :return: test data config
        """
        test_data_root_dir = config_etree.findtext('/test_data/root_dir')
        return TestDataConfig(
            root_dir=test_data_root_dir,
        )

    def __validate_config(self):
        """
        Validates parsed config. Checks the conditions which the schema validation couldn't check.
        Checks cross field conditions.
        """
        assert self.config.structure.min_number <= self.config.structure.max_number,\
            'Strukturkonfiguration: maximale Aktenzahl ist kleiner als minimale Aktenzahl'
        assert self.config.structure.process_structure.min_number <=\
            self.config.structure.process_structure.max_number,\
            'Strukturkonfiguration: maximale Vorgangszahl ist kleiner als minimale Vorgangszahl'
        assert self.config.structure.process_structure.\
            document_structure.min_number <= self.config.structure.\
            process_structure.document_structure.max_number,\
            'Strukturkonfiguration: maximale Dokumentenzahl ist kleiner als minimale Dokumentenzahl'

    def generate_xdomea_messages(self):
        """
        Parses xdomea message patterns and validates against the pattern schema.
        """
        generated_message_ID = str(uuid.uuid4())
        pattern_schema_root = etree.parse(self.config.message_pattern.schema_path)
        pattern_schema = etree.XMLSchema(pattern_schema_root)
        parser = etree.XMLParser(remove_blank_text=True) 
        xdomea_0501_pattern_etree = etree.parse(
            self.config.message_pattern.xdomea_0501_path, 
            parser, # removes intendation from patterns, necessary for pretty print output
        )
        pattern_schema.assertValid(xdomea_0501_pattern_etree)
        xdomea_0503_pattern_etree = etree.parse(
            self.config.message_pattern.xdomea_0503_path,
            parser, # removes intendation from patterns, necessary for pretty print output
        )
        pattern_schema.assertValid(xdomea_0503_pattern_etree)
        xdomea_0501_pattern_root = xdomea_0501_pattern_etree.getroot()
        self.__set_xdomea_process_id(xdomea_0501_pattern_root, generated_message_ID)
        # de: record object - Schriftgutobjekt
        record_object_pattern_list = self.__get_record_object_patterns(xdomea_0501_pattern_root)
        # remove all record objects from xdomea 0501 pattern
        for record_object_pattern in record_object_pattern_list:
            record_object_pattern.getparent().remove(record_object_pattern)
        self.__generate_0501_file_structure(
            xdomea_0501_pattern_root,
            record_object_pattern_list,
        )
        pattern_schema.assertValid(xdomea_0501_pattern_etree)
        xdomea_0503_pattern_root = xdomea_0503_pattern_etree.getroot()
        self.__generate_0503_message_structure(xdomea_0501_pattern_root, xdomea_0503_pattern_root)
        pattern_schema.assertValid(xdomea_0503_pattern_etree)
        # export messages
        self.__export_xdomea_message(
            generated_message_ID, 
            self.regex_config.xdomea_0501_message_name,
            xdomea_0501_pattern_etree,
        )
        self.__export_xdomea_message(
            generated_message_ID, 
            self.regex_config.xdomea_0503_message_name,
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
        :return: choosen xdomea pattern
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
        for file_index in range(file_number):
            # randomly choose file pattern
            file_pattern = self.__get_random_pattern(file_pattern_list)
            self.__set_file_evaluation(file_pattern)
            self.__generate_0501_process_structure(file_pattern)
            # add file pattern to message
            xdomea_0501_pattern_root.append(file_pattern)

    def __set_file_evaluation(self, file_pattern: etree.Element):
        """
        Chooses file evaluation dependent on configuration.
        :param file_pattern: xdomea file element extracted from message pattern
        """
        file_id = self.__get_xdomea_object_id(file_pattern)
        file_evaluation = XdomeaEvaluation.EVALUATE
        if self.config.structure.file_evaluation == 'archive':
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
            process_pattern.getparent().remove(process_pattern)
        # randomly choose process number for file pattern
        process_number = self.__get_random_number(
            self.config.structure.process_structure.min_number, 
            self.config.structure.process_structure.max_number,
        )
        # get parent file info
        file_id = self.__get_xdomea_object_id(file_pattern)
        file_evaluation = self.record_object_evaluation[file_id]
        for process_index in range(process_number):
            # randomly choose process pattern
            process_pattern = self.__get_random_pattern(process_pattern_list)
            self.__set_process_evaluation(process_pattern, file_evaluation)
            self.__generate_0501_document_structure(process_pattern)
            file_content_element.append(process_pattern)

    def __set_process_evaluation(
        self, 
        process_pattern: etree.Element, 
        file_evaluation: XdomeaEvaluation,
    ):
        """
        Sets process evaluation dependent on configuration and parent file evaluation.
        :param process_pattern: xdomea process element extracted from message pattern
        :param file_evaluation: parent file evaluation
        """
        process_evaluation = XdomeaEvaluation.EVALUATE
        if file_evaluation == XdomeaEvaluation.DISCARD:
            process_evaluation = XdomeaEvaluation.DISCARD
        elif self.config.structure.process_structure.process_evaluation == 'inherit':
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
            document_pattern.getparent().remove(document_pattern)
        # randomly choose document number for process pattern
        document_number = self.__get_random_number(
            self.config.structure.process_structure.document_structure.min_number, 
            self.config.structure.process_structure.document_structure.max_number,
        )
        for document_index in range(document_number):
            # randomly choose document pattern
            document_pattern = self.__get_random_pattern(document_pattern_list)
            process_pattern.append(document_pattern)

    def __generate_0503_message_structure(
        self, 
        xdomea_0501_pattern_root: etree.Element,
        xdomea_0503_pattern_root: etree.Element,
    ):
        """
        Generates xdomea 0503 message structure with the configured constraints.
        The record objects from the 0501 message are copied in the 0503 message.
        The record objects from the 0503 message are discarded.
        :param xdomea_0501_pattern_root: root element of 0501 message
        :param xdomea_0503_pattern_root: root element of 0503 message
        """
        record_object_pattern_list_0501 = self.__get_record_object_patterns(
            xdomea_0501_pattern_root)
        record_object_pattern_list_0503 = self.__get_record_object_patterns(
            xdomea_0503_pattern_root)
        # remove all record objects from xdomea 0503 pattern
        for record_object_pattern in record_object_pattern_list_0503:
            record_object_pattern.getparent().remove(record_object_pattern)
        # add all record objects from xdomea 0501 pattern to 0503 message
        for record_object_pattern in record_object_pattern_list_0501:
            xdomea_0503_pattern_root.append(record_object_pattern)
        self.__apply_object_evaluation_to_0503_message(xdomea_0503_pattern_root)

    def __apply_object_evaluation_to_0503_message(self, xdomea_0503_pattern_root: etree.Element):
        for object_id, evaluation in self.record_object_evaluation.items():
            object_xpath = \
                './/xdomea:Identifikation/xdomea:ID[contains(text(), "' + object_id + '")]/../..'
            # xpath search is necessary for search with namespace and text content search
            record_object = xdomea_0503_pattern_root.xpath(
                object_xpath,
                namespaces=xdomea_0503_pattern_root.nsmap,
            )
            assert len(record_object) == 1
            self.__set_xdomea_evaluation(record_object[0], evaluation)

    def __set_xdomea_evaluation(self, record_object: etree.Element, evaluation: XdomeaEvaluation):
        xdomea_namespace = '{' + record_object.nsmap['xdomea'] + '}'
        expected_tag_list = [xdomea_namespace + 'Akte', xdomea_namespace + 'Vorgang']
        assert record_object.tag in expected_tag_list
        metadata_archive_el = record_object.find(
            './xdomea:ArchivspezifischeMetadaten', 
            namespaces=record_object.nsmap,
        )
        if metadata_archive_el is None:
            metadata_archive_el = etree.SubElement(
                record_object, xdomea_namespace+'ArchivspezifischeMetadaten')
        evaluation_el = metadata_archive_el.find(
            './xdomea:Aussonderungsart', 
            namespaces=record_object.nsmap,
        )
        if evaluation_el is None:
            evaluation_el = etree.SubElement(record_object, xdomea_namespace+'Aussonderungsart')
        evaluation_code_el = evaluation_el.find(
            './xdomea:Aussonderungsart', 
            namespaces=record_object.nsmap,
        )
        if evaluation_code_el is None:
            evaluation_code_el = etree.SubElement(record_object, xdomea_namespace+'Aussonderungsart')
        evaluation_code_el.text = evaluation

    def __export_xdomea_message(
        self, 
        generated_message_ID: str,
        message_name_suffix: str,
        xdomea_pattern_etree: etree,
    ):
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        message_name = generated_message_ID + message_name_suffix
        message_path = os.path.join(self.config.output_dir, message_name)
        xdomea_pattern_etree.write(
            message_path, 
            xml_declaration=True,
            pretty_print=True, 
            encoding='utf-8', 
        )
        
    def __get_random_number(self, min: int, max: int) -> int:
        """
        Necessary because range function fails if min equals max.
        :param min: min number of random range
        :param max: max number of random range
        :return random number in range
        """
        # max + 1 is necessary so that max is included in the range
        return min if min == max else random.choice(range(min, max+1))


def main():
    message_generator = XdomeaMessageGenerator()
    message_generator.read_config('config/generator_config.xml', 'config/generator_config.xsd')
    message_generator.generate_xdomea_messages()


if __name__ == '__main__':
    main()
