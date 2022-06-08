from dataclasses import dataclass
from enum import Enum
from lxml import etree
import random


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


class XdomeaMessageGenerator:
    config: GeneratorConfig
    file_pattern_list: list[etree.Element]
    process_pattern_list: list[etree.Element]
    document_pattern_list: list[etree.Element]

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
        self.config = GeneratorConfig(
            structure=self.__read_structure_config(config_etree),
            message_pattern=self.__read_message_pattern_config(config_etree),
            test_data=self.__read_test_data_config(config_etree),
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
        pattern_schema_root = etree.parse(self.config.message_pattern.schema_path)
        pattern_schema = etree.XMLSchema(pattern_schema_root)
        xdomea_0501_pattern_etree = etree.parse(self.config.message_pattern.xdomea_0501_path)
        pattern_schema.assertValid(xdomea_0501_pattern_etree)
        xdomea_0503_pattern_etree = etree.parse(self.config.message_pattern.xdomea_0503_path)
        pattern_schema.assertValid(xdomea_0503_pattern_etree)
        xdomea_0501_pattern_root = xdomea_0501_pattern_etree.getroot()
        self.__extract_structure_patterns(xdomea_0501_pattern_root)
        self.__generate_0501_message_structure(xdomea_0501_pattern_root)

    def __extract_structure_patterns(self, xdomea_0501_pattern_root: etree.Element):
        """
        Extracts all file, process and document elements from the xdomea 0501 message pattern.
        The structure elements will be removed from the pattern.
        The sequence of extraction is important because some structure elements can contain other.
        """
        # find all document elements in 0501 message
        self.document_pattern_list = xdomea_0501_pattern_root.findall(
            './/xdomea:Dokument', namespaces=xdomea_0501_pattern_root.nsmap)
        # remove all documents from xdomea 0501 pattern
        for document_pattern in self.document_pattern_list:
            document_pattern.getparent().remove(document_pattern)
        # find all process elements in 0501 message
        self.process_pattern_list = xdomea_0501_pattern_root.findall(
            './/xdomea:Vorgang', namespaces=xdomea_0501_pattern_root.nsmap)
        # remove all processes from xdomea 0501 pattern
        for process_pattern in self.process_pattern_list:
            process_pattern.getparent().remove(process_pattern)
        # find file document elements in 0501 message
        self.file_pattern_list = xdomea_0501_pattern_root.findall(
            './/xdomea:Akte', namespaces=xdomea_0501_pattern_root.nsmap)
        # remove all files from xdomea 0501 pattern
        for file_pattern in self.file_pattern_list:
            file_pattern.getparent().remove(file_pattern)

    def __generate_0501_message_structure(self, xdomea_0501_pattern_root: etree.Element):
        """
        Generates xdomea 0501 message structure with the configured constraints.
        """
        # randomly choose file number
        file_number = self.__get_random_number(
            self.config.structure.min_number, self.config.structure.max_number)
        for file_index in range(file_number):
            # randomly choose file pattern
            file_pattern = random.choice(self.file_pattern_list)
            xdomea_0501_pattern_root.append(file_pattern)

    def __get_random_number(self, min: int, max: int):
        """
        Necessary because range function fails if min equals max.
        :return random number in range
        """
        return min if min == max else random.choice(range(min, max))


def main():
    message_generator = XdomeaMessageGenerator()
    message_generator.read_config('config/generator_config.xml', 'config/generator_config.xsd')
    message_generator.generate_xdomea_messages()


if __name__ == '__main__':
    main()
