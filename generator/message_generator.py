from lxml import etree
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


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

    def read_config(self, config_path: str, config_schema_path: str):
        """
        Parses xml config file into object representation. Validates xml config file against schema.
        :param config_path: path of xml config file
        :param config_schema_path: path of xml schema for config file
        """
        config_root = etree.parse(config_path)
        config_schema_root = etree.parse(config_schema_path)
        config_schema = etree.XMLSchema(config_schema_root)
        config_schema.assertValid(config_root)
        self.config = GeneratorConfig(
            structure=self.__read_structure_config(config_root),
            message_pattern=self.__read_message_pattern_config(config_root),
            test_data=self.__read_test_data_config(config_root),
        )
        self.__validate_config()

    def __read_structure_config(self, config_root: etree.Element) -> FileStructureConfig:
        """
        Parses message structure config into object representation.
        :param config_root: xml root of config
        :return: file structure config
        """
        files_min_number = int(config_root.findtext('/structure/files/min_number'))
        files_max_number = int(config_root.findtext('/structure/files/max_number'))
        files_evaluation = FileEvaluationConfig[config_root.findtext(
            '/structure/files/evaluation').upper()]
        processes_min_number = int(config_root.findtext('/structure/files/processes/min_number'))
        processes_max_number = int(config_root.findtext('/structure/files/processes/max_number'))
        processes_evaluation = ProcessEvaluationConfig[config_root.findtext(
            '/structure/files/processes/evaluation').upper()]
        documents_min_number = int(config_root.findtext(
            '/structure/files/processes/documents/min_number'))
        documents_max_number = int(config_root.findtext(
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

    def __read_message_pattern_config(self, config_root: etree.Element) -> MessagePatternConfig:
        """
        Parses message pattern config into object representation.
        :param config_root: xml root of config
        :return: message pattern config
        """
        xdomea_0501_path = config_root.findtext('/message_pattern/xdomea_0501_path')
        xdomea_0503_path = config_root.findtext('/message_pattern/xdomea_0503_path')
        schema_path = config_root.findtext('/message_pattern/schema_path')
        return MessagePatternConfig(
            xdomea_0501_path=xdomea_0501_path,
            xdomea_0503_path=xdomea_0503_path,
            schema_path=schema_path,
        )

    def __read_test_data_config(self, config_root: etree.Element) -> TestDataConfig:
        """
        Parses test data config into object representation.
        :param config_root: xml root of config
        :return: test data config
        """
        test_data_root_dir = config_root.findtext('/test_data/root_dir')
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
        xdomea_0501_pattern_root = etree.parse(self.config.message_pattern.xdomea_0501_path)
        pattern_schema.assertValid(xdomea_0501_pattern_root)
        xdomea_0503_pattern_root = etree.parse(self.config.message_pattern.xdomea_0503_path)
        pattern_schema.assertValid(xdomea_0503_pattern_root)


def main():
    message_generator = XdomeaMessageGenerator()
    message_generator.read_config('config/generator_config.xml', 'config/generator_config.xsd')
    message_generator.generate_xdomea_messages()


if __name__ == '__main__':
    main()
