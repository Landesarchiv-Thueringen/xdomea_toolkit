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
    document_structure_config: DocumentStructureConfig


class FileEvaluationConfig(Enum):
    ARCHIVE = 1
    RANDOM = 2


@dataclass
class FileStructureConfig:
    min_number: int
    max_number: int
    file_evaluation: FileEvaluationConfig
    process_structure_config: ProcessStructureConfig


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
    structure_config: FileStructureConfig
    message_pattern_config: MessagePatternConfig
    test_data_config: TestDataConfig


class XdomeaMessageGenerator:
    config: GeneratorConfig

    def read_config(self, config_path: str, config_schema_path: str):
        config_doc = etree.parse(config_path)
        config_schema_doc = etree.parse(config_schema_path)
        config_schema = etree.XMLSchema(config_schema_doc)
        assert config_schema.validate(config_doc)
        config = GeneratorConfig(
            structure_config=self.__read_structure_config(config_doc),
            message_pattern_config=self.__read_message_pattern_config(config_doc),
            test_data_config=self.__read_test_data_config(config_doc),
        )

    def __read_structure_config(self, config_doc) -> FileStructureConfig:
        files_min_number = int(config_doc.findtext('/structure/files/min_number'))
        files_max_number = int(config_doc.findtext('/structure/files/max_number'))
        files_evaluation = FileEvaluationConfig[config_doc.findtext(
            '/structure/files/evaluation').upper()]
        processes_min_number = int(config_doc.findtext('/structure/files/processes/min_number'))
        processes_max_number = int(config_doc.findtext('/structure/files/processes/max_number'))
        processes_evaluation = ProcessEvaluationConfig[config_doc.findtext(
            '/structure/files/processes/evaluation').upper()]
        documents_min_number = int(config_doc.findtext(
            '/structure/files/processes/documents/min_number'))
        documents_max_number = int(config_doc.findtext(
            '/structure/files/processes/documents/max_number'))
        document_structure_config = DocumentStructureConfig(
            min_number=documents_min_number,
            max_number=documents_max_number,
        )
        process_structure_config = ProcessStructureConfig(
            min_number=processes_min_number,
            max_number=processes_max_number,
            process_evaluation=processes_evaluation,
            document_structure_config=document_structure_config,
        )
        return FileStructureConfig(
            min_number=files_min_number,
            max_number=files_max_number,
            file_evaluation=files_evaluation,
            process_structure_config=process_structure_config,
        )

    def __read_message_pattern_config(self, config_doc) -> MessagePatternConfig:
        xdomea_0501_path = config_doc.findtext('/message_pattern/xdomea_0501_path')
        xdomea_0503_path = config_doc.findtext('/message_pattern/xdomea_0503_path')
        schema_path = config_doc.findtext('/message_pattern/schema_path')
        return MessagePatternConfig(
            xdomea_0501_path=xdomea_0501_path,
            xdomea_0503_path=xdomea_0503_path,
            schema_path=schema_path,
        )

    def __read_test_data_config(self, config_doc) -> TestDataConfig:
        test_data_root_dir = config_doc.findtext('/test_data/root_dir')
        return TestDataConfig(
            root_dir=test_data_root_dir,
        )


def main():
    message_generator = XdomeaMessageGenerator()
    message_generator.read_config('config/generator_config.xml', 'config/generator_config.xsd')


if __name__ == '__main__':
    main()