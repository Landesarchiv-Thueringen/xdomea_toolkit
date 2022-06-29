from dataclasses import dataclass
from enum import Enum
from lxml import etree

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

class ConfigParser:

    @staticmethod
    def parse_config(config_path: str, config_schema_path: str) -> GeneratorConfig:
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
        config = GeneratorConfig(
            structure=ConfigParser.__read_structure_config(config_etree),
            message_pattern=ConfigParser.__read_message_pattern_config(config_etree),
            test_data=ConfigParser.__read_test_data_config(config_etree),
            output_dir=output_dir,
        )
        ConfigParser.__validate_config(config)
        return config

    @staticmethod
    def __read_structure_config(config_etree: etree.Element) -> FileStructureConfig:
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

    @staticmethod
    def __read_message_pattern_config(config_etree: etree.Element) -> MessagePatternConfig:
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

    @staticmethod
    def __read_test_data_config(config_etree: etree.Element) -> TestDataConfig:
        """
        Parses test data config into object representation.
        :param config_etree: element tree of xml config
        :return: test data config
        """
        test_data_root_dir = config_etree.findtext('/test_data/root_dir')
        return TestDataConfig(
            root_dir=test_data_root_dir,
        )

    @staticmethod
    def __validate_config(config: GeneratorConfig):
        """
        Validates parsed config. Checks the conditions which the schema validation couldn't check.
        Checks cross field conditions.
        """
        assert config.structure.min_number <= config.structure.max_number,\
            'Strukturkonfiguration: maximale Aktenzahl ist kleiner als minimale Aktenzahl'
        assert config.structure.process_structure.min_number <=\
            config.structure.process_structure.max_number,\
            'Strukturkonfiguration: maximale Vorgangszahl ist kleiner als minimale Vorgangszahl'
        assert config.structure.process_structure.\
            document_structure.min_number <= config.structure.\
            process_structure.document_structure.max_number,\
            'Strukturkonfiguration: maximale Dokumentenzahl ist kleiner als minimale Dokumentenzahl'