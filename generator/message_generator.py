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


class XdomeaMessageGenerator:
    config: GeneratorConfig
    regex_config: XdomeaRegexConfig
    record_object_pattern_list: list[etree.Element] # de: record object - Schriftgutobjekt

    def __init__(self):
        self.regex_config = XdomeaRegexConfig(
            uuid='[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            xdomea_0501_message_name='_Aussonderung.Anbieteverzeichnis.0501.xml',
            xdomea_0503_message_name='_Aussonderung.Aussonderung.0503.xml',
        )

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
        self.__extract_record_object_patterns(xdomea_0501_pattern_root)
        self.__generate_0501_message_structure(xdomea_0501_pattern_root)
        pattern_schema.assertValid(xdomea_0501_pattern_etree)
        self.__export_xdomea_0501_message(generated_message_ID, xdomea_0501_pattern_etree)

    def __extract_record_object_patterns(self, xdomea_0501_pattern_root: etree.Element):
        """
        Extracts all record objects from the xdomea 0501 message pattern.
        The elements will be removed from the pattern.
        :param xdomea_0501_pattern_root: root element of 0501 message
        """
        self.record_object_pattern_list = xdomea_0501_pattern_root.findall(
            './/xdomea:Schriftgutobjekt', namespaces=xdomea_0501_pattern_root.nsmap)
        # remove all record objects from xdomea 0501 pattern
        for record_object_pattern in self.record_object_pattern_list:
            record_object_pattern.getparent().remove(record_object_pattern)


    def __generate_0501_message_structure(self, xdomea_0501_pattern_root: etree.Element):
        """
        Generates xdomea 0501 message structure with the configured constraints.
        :param xdomea_0501_pattern_root: root element of 0501 message
        """
        # check if necessary structure exists in 0501 pattern
        xpath = './xdomea:Akte/xdomea:Akteninhalt/xdomea:Vorgang/xdomea:Dokument'
        file_pattern_list = [p for p in self.record_object_pattern_list 
            if p.find(xpath, namespaces=xdomea_0501_pattern_root.nsmap) is not None]
        assert file_pattern_list, 'kein Muster für Struktur Akte/Vorgang/Dokument definiert'
        # randomly choose file number for xdomea 0501 message
        file_number = self.__get_random_number(
            self.config.structure.min_number, self.config.structure.max_number)
        for file_index in range(file_number):
            # randomly choose file pattern
            # deepcopy is necessary if a pattern is used multiple times
            file_pattern = deepcopy(random.choice(file_pattern_list))
            self.__generate_0501_process_structure(file_pattern)
            # add file pattern to message
            xdomea_0501_pattern_root.append(file_pattern)

    def __generate_0501_process_structure(self, file_pattern: etree.Element):
        """
        Generates process structure for file pattern with the configured constraints.
        :param file_pattern: xdomea file element extracted from pattern
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
        for process_index in range(process_number):
            # randomly choose process pattern
            # deepcopy is necessary if a pattern is used multiple times
            process_pattern = deepcopy(random.choice(process_pattern_list))
            self.__generate_0501_document_structure(process_pattern)
            file_content_element.append(process_pattern)

    def __generate_0501_document_structure(self, process_pattern: etree.Element):
        """
        Generates document structure for process pattern with the configured constraints.
        :param process_pattern: xdomea process element extracted from pattern
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
            # deepcopy is necessary if a pattern is used multiple times
            document_pattern = deepcopy(random.choice(document_pattern_list))
            process_pattern.append(document_pattern)

    def __export_xdomea_0501_message(
        self, 
        generated_message_ID: str, 
        xdomea_0501_pattern_etree: etree,
    ):
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        xml_0501_name = generated_message_ID + self.regex_config.xdomea_0501_message_name
        xml_0501_path = os.path.join(self.config.output_dir, xml_0501_name)
        xdomea_0501_pattern_etree.write(
            xml_0501_path, 
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
        return min if min == max else random.choice(range(min, max))


def main():
    message_generator = XdomeaMessageGenerator()
    message_generator.read_config('config/generator_config.xml', 'config/generator_config.xsd')
    message_generator.generate_xdomea_messages()


if __name__ == '__main__':
    main()
