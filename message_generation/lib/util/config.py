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

from dataclasses import dataclass
from enum import Enum
from lxml import etree
import os
from typing import Optional


@dataclass
class DocumentVersionStructureConfig:
    min_number: int
    max_number: int


@dataclass
class DocumentStructureConfig:
    min_number: int
    max_number: int
    version_structure: DocumentVersionStructureConfig


class ProcessEvaluationConfig(Enum):
    INHERIT = 1
    RANDOM = 2


@dataclass
class ProcessStructureConfig:
    min_number: int
    max_number: int
    process_evaluation: ProcessEvaluationConfig
    subprocess_structure: Optional["ProcessStructureConfig"] = None
    document_structure: Optional[DocumentStructureConfig] = None


class FileEvaluationConfig(Enum):
    ARCHIVE = 1
    RANDOM = 2


@dataclass
class FileStructureConfig:
    min_number: int
    max_number: int
    file_evaluation: FileEvaluationConfig
    subfile_structure: Optional["FileStructureConfig"] = None
    process_structure: Optional[ProcessStructureConfig] = None
    document_structure: Optional[DocumentStructureConfig] = None


@dataclass
class MessagePatternConfig:
    message_0501_path: str
    message_0503_path: str


@dataclass
class XdomeaConfig:
    version: str
    schema_path: str
    file_type_code_list_path: str
    pattern_config: MessagePatternConfig


@dataclass
class TestDataConfig:
    root_dir: str


@dataclass
class GeneratorConfig:
    structure: FileStructureConfig
    xdomea: XdomeaConfig
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
        output_dir = os.path.normpath(config_etree.findtext('/output_dir'))
        structure_etree = config_etree.find('./structure')
        config = GeneratorConfig(
            structure=ConfigParser.__read_structure_config(structure_etree),
            xdomea=ConfigParser.__read_xdomea_config(config_etree),
            test_data=ConfigParser.__read_test_data_config(config_etree),
            output_dir=output_dir,
        )
        ConfigParser.__validate_config(config)
        return config

    @staticmethod
    def __read_structure_config(structure_etree: etree.Element) -> FileStructureConfig:
        """
        Parses message structure config into object representation.
        :param structure_etree: structure element tree of xml config
        :return: file structure config
        """
        file_structure_etree = structure_etree.find('./files')
        return ConfigParser.__read_file_structure_config(file_structure_etree)

    @staticmethod
    def __read_file_structure_config(file_structure_etree: etree.Element) -> FileStructureConfig:
        """
        Parses file or subfile structure config into object representation.
        :param file_structure_etree: files or subfiles element tree of xml config
        :return: file structure config
        """
        min_number = int(file_structure_etree.findtext('./min_number'))
        max_number = int(file_structure_etree.findtext('./max_number'))
        evaluation = FileEvaluationConfig[file_structure_etree.findtext('./evaluation').upper()]

        subfile_structure_etree = file_structure_etree.find('./subfiles')
        if subfile_structure_etree is not None:
            subfile_structure = ConfigParser.__read_file_structure_config(subfile_structure_etree)
        else:
            subfile_structure = None

        process_structure_etree = file_structure_etree.find('./processes')
        if process_structure_etree is not None:
            process_structure = ConfigParser.__read_process_structure_config(process_structure_etree)
        else:
            process_structure = None

        document_structure_etree = file_structure_etree.find('./documents')
        if document_structure_etree is not None:
            document_structure = ConfigParser.__read_document_structure_config(document_structure_etree)
        else:
            document_structure = None

        return FileStructureConfig(
            min_number=min_number,
            max_number=max_number,
            file_evaluation=evaluation,
            subfile_structure=subfile_structure,
            process_structure=process_structure,
            document_structure=document_structure,
        )

    @staticmethod
    def __read_process_structure_config(process_structure_etree: etree.Element) -> ProcessStructureConfig:
        """
        Parses process or subprocess structure config into object representation.
        :param process_structure_etree: processes or subprocesses element tree of xml config
        :return: process structure config
        """
        min_number = int(process_structure_etree.findtext('./min_number'))
        max_number = int(process_structure_etree.findtext('./max_number'))
        evaluation = ProcessEvaluationConfig[process_structure_etree.findtext('./evaluation').upper()]

        subprocess_structure_etree = process_structure_etree.find('./subprocesses')
        if subprocess_structure_etree is not None:
            subprocess_structure = ConfigParser.__read_process_structure_config(subprocess_structure_etree)
        else:
            subprocess_structure = None

        document_structure_etree = process_structure_etree.find('./documents')
        if document_structure_etree is not None:
            document_structure = ConfigParser.__read_document_structure_config(document_structure_etree)
        else:
            document_structure = None

        return ProcessStructureConfig(
            min_number=min_number,
            max_number=max_number,
            process_evaluation=evaluation,
            subprocess_structure=subprocess_structure,
            document_structure=document_structure,
        )

    @staticmethod
    def __read_document_structure_config(document_structure_etree: etree.Element) -> DocumentStructureConfig:
        """
        Parses document structure config into object representation.
        :param document_structure_etree: documents element tree of xml config
        :return: document structure config
        """
        min_number = int(document_structure_etree.findtext('./min_number'))
        max_number = int(document_structure_etree.findtext('./max_number'))
        version_structure_etree = document_structure_etree.find('./versions')
        version_structure = ConfigParser.__read_version_structure_config(version_structure_etree)

        return DocumentStructureConfig(
            min_number=min_number,
            max_number=max_number,
            version_structure=version_structure
        )

    @staticmethod
    def __read_version_structure_config(version_structure_etree: etree.Element) -> DocumentVersionStructureConfig:
        """
        Parses document version structure config into object representation.
        :param version_structure_etree: versions element tree of xml config
        :return: document version structure config
        """
        min_number = int(version_structure_etree.findtext('./min_number'))
        max_number = int(version_structure_etree.findtext('./max_number'))
        return DocumentVersionStructureConfig(
            min_number=min_number,
            max_number=max_number,
        )

    @staticmethod
    def __read_xdomea_config(config_etree: etree.Element) -> XdomeaConfig:
        """
        Parses xdomea config into object representation.
        :param config_etree: element tree of xml config
        :return: xdomea config
        """
        xdomea_config_el = config_etree.find('/xdomea')
        target_version = xdomea_config_el.get('target_version')
        version_el_list = xdomea_config_el.xpath(
            './version/id[contains(text(), "' + target_version + '")]/..')
        assert version_el_list is not None,\
            'xdomea Konfiguration: angebene Konfiguration für Zielversion wurde nicht gefunden'
        assert len(version_el_list) == 1,\
            'xdomea Konfiguration: mehrere mögliche Konfigurationen für Zielversion gefunden'
        version_el = version_el_list[0]
        schema_path = version_el.findtext('./schema')
        file_type_code_list_path = version_el.findtext('./file_type_code_list')
        message_0501_path = version_el.findtext('./pattern/message_0501')
        message_0503_path = version_el.findtext('./pattern/message_0503')
        return XdomeaConfig(
            version=target_version,
            schema_path=schema_path,
            file_type_code_list_path=file_type_code_list_path,
            pattern_config=MessagePatternConfig(
                message_0501_path = message_0501_path,
                message_0503_path = message_0503_path,
            )
        )

    @staticmethod
    def __read_test_data_config(config_etree: etree.Element) -> TestDataConfig:
        """
        Parses test data config into object representation.
        :param config_etree: element tree of xml config
        :return: test data config
        """
        test_data_root_dir = os.path.normpath(config_etree.findtext('/test_data/root_dir'))
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