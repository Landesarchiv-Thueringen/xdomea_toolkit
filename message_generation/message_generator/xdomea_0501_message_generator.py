import random

from lxml import etree
from typing import Union, Optional

from .abstract_message_generator import AbstractMessageGenerator
from .config import FileStructureConfig, SubfileStructureConfig, ProcessStructureConfig, DocumentStructureConfig, \
    FileEvaluationConfig, InheritableEvaluationConfig
from .helper import get_random_number, get_random_pattern, get_xdomea_object_id
from .types import XdomeaEvaluation


class Xdomea0501MessageGenerator(AbstractMessageGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_pattern_list = []
        self.process_pattern_list = []
        self.document_pattern_list = []
        self.record_object_evaluation = {}

    def _load_message_pattern(self, pattern_path: str):
        super()._load_message_pattern(pattern_path)
        self.file_pattern_list = self.message_pattern_root.findall('.//xdomea:Akte',
                                                                   namespaces=self.message_pattern_root.nsmap)
        self.process_pattern_list = self.message_pattern_root.findall('.//xdomea:Vorgang',
                                                                      namespaces=self.message_pattern_root.nsmap)
        self.document_pattern_list = self.message_pattern_root.findall('.//xdomea:Dokument',
                                                                       namespaces=self.message_pattern_root.nsmap)

    def generate_message(self, message_id: str) -> etree.ElementTree:
        self._load_message_pattern(self.config.xdomea.pattern_config.message_0501_path)
        self._set_process_id(message_id)

        # remove record object patterns from the template
        self._remove_record_object_patterns()

        # generate xdomea 0501 file structure (recursively adds subfile, process, subprocess and document structures)
        self.__generate_file_structure(self.message_pattern_root, self.config.structure)
        self._replace_record_object_placeholder()

        self.xdomea_schema.assertValid(self.message_pattern_etree)
        return self.message_pattern_etree

    def __generate_file_structure(self,
                                  parent: etree.Element,
                                  file_structure_config: Union[FileStructureConfig, SubfileStructureConfig],
                                  parent_file_evaluation: Optional[XdomeaEvaluation] = None):
        """
        Generates file or subfile structure for a 0501 xdomea message
        :param parent: parent element of the generated file structure
        :param file_structure_config: configuration for the file or subfile structure
        :param parent_file_evaluation: evaluation of the parent file if the generated file is a subfile
        """
        file_number = get_random_number(file_structure_config.min_number, file_structure_config.max_number)
        first_file = True
        for file_index in range(file_number):
            # randomly choose file pattern
            file_pattern = get_random_pattern(self.file_pattern_list)

            file_evaluation = self.__set_file_evaluation(file_pattern, first_file, file_structure_config,
                                                         parent_file_evaluation)

            self.__clean_file_content(file_pattern)
            file_content = file_pattern.find('./xdomea:Akteninhalt', namespaces=file_pattern.nsmap)

            # generate documents
            if file_structure_config.document_structure:
                self.__generate_document_structure(file_content, file_structure_config.document_structure)

            # generate processes
            if file_structure_config.process_structure:
                self.__generate_process_structure(file_content,
                                                  file_structure_config.process_structure,
                                                  file_evaluation)

            # generate subfiles
            if file_structure_config.subfile_structure:
                # in XDOMEA 3.0.0 subfiles are in Akteninhalt, in 2.3.0 and 2.4.0 they are under the parent files root
                # element
                if self.xdomea_schema_version == "3.0.0":
                    self.__generate_file_structure(file_content, file_structure_config.subfile_structure,
                                                   file_evaluation)
                else:
                    self.__generate_file_structure(file_pattern, file_structure_config.subfile_structure,
                                                   file_evaluation)

            if type(file_structure_config) is SubfileStructureConfig:
                file_pattern.tag = etree.QName(self.xdomea_namespace, 'Teilakte')
                parent.append(file_pattern)
            else:
                record_object = etree.SubElement(parent, etree.QName(self.xdomea_namespace, 'Schriftgutobjekt'))
                record_object.append(file_pattern)

            first_file = False

    def __generate_process_structure(self,
                                     parent: etree.Element,
                                     process_structure_config: ProcessStructureConfig,
                                     file_evaluation: XdomeaEvaluation,
                                     is_subprocess: bool = False):
        """
        Generates process or subprocess structure for a 0501 xdomea message.
        :param parent: parent element of the generated process structure
        :param process_structure_config: configuration for the process or subprocess structure
        :param file_evaluation: evaluation configuration of the parent file
        :param is_subprocess: flag if a process or a subprocess structure should get generated
        """
        # randomly choose process number
        process_number = get_random_number(process_structure_config.min_number, process_structure_config.max_number)

        first_process = True
        for process_index in range(process_number):
            # randomly choose process pattern
            process_pattern = get_random_pattern(self.process_pattern_list)
            self.__set_process_evaluation(process_pattern, file_evaluation, first_process, process_structure_config)

            # clean process pattern
            subprocesses = process_pattern.findall('./xdomea:Teilvorgang', namespaces=process_pattern.nsmap)
            for subprocess in subprocesses:
                process_pattern.remove(subprocess)

            documents = process_pattern.findall('./xdomea:Dokument', namespaces=process_pattern.nsmap)
            for document in documents:
                process_pattern.remove(document)

            # generate documents
            if process_structure_config.document_structure:
                self.__generate_document_structure(process_pattern,
                                                   process_structure_config.document_structure)

            # generate subprocesses
            if process_structure_config.subprocess_structure:
                self.__generate_process_structure(process_pattern,
                                                  process_structure_config.subprocess_structure,
                                                  file_evaluation,
                                                  True)

            if is_subprocess:
                process_pattern.tag = etree.QName(self.xdomea_namespace, 'Teilvorgang')
            parent.append(process_pattern)
            first_process = False

    def __generate_document_structure(self,
                                      parent: etree.Element,
                                      document_structure_config: DocumentStructureConfig):
        """
        Generates document structure for a 0501 xdomea message.
        :param parent: parent element of the generated document structure
        :param document_structure_config: configuration for the document structure
        """
        # randomly choose document number for process pattern
        document_number = get_random_number(document_structure_config.min_number, document_structure_config.max_number)
        for document_index in range(document_number):
            # randomly choose document pattern
            document_pattern = get_random_pattern(self.document_pattern_list)
            parent.append(document_pattern)

    def __set_file_evaluation(self,
                              file_pattern: etree.Element,
                              first_file: bool,
                              file_structure_config: Union[FileStructureConfig, SubfileStructureConfig],
                              parent_file_evaluation: XdomeaEvaluation = None) -> XdomeaEvaluation:
        """
        Chooses file evaluation dependent on configuration.
        :param file_pattern: xdomea file element extracted from message pattern
        :param first_file: true if file pattern is the first file pattern
        """
        file_id = get_xdomea_object_id(file_pattern)

        # first file is always archived to guarantee a valid message structure
        if first_file:
            file_evaluation = XdomeaEvaluation.ARCHIVE
        else:
            # set file evaluation
            if type(file_structure_config) is FileStructureConfig:
                if file_structure_config.file_evaluation == FileEvaluationConfig.ARCHIVE:
                    file_evaluation = XdomeaEvaluation.ARCHIVE
                else:  # random evaluation
                    file_evaluation = random.choice(list(XdomeaEvaluation))
            # set subfile evaluation
            else:
                if file_structure_config.file_evaluation == InheritableEvaluationConfig.INHERIT:
                    file_evaluation = parent_file_evaluation
                else:
                    file_evaluation = random.choice(list(XdomeaEvaluation))

        self.record_object_evaluation[file_id] = file_evaluation
        return file_evaluation

    def __set_process_evaluation(
        self,
        process_pattern: etree.Element,
        file_evaluation: XdomeaEvaluation,
        first_process: bool,
        process_structure_config: ProcessStructureConfig
    ):
        """
        Sets process evaluation dependent on configuration and parent file evaluation.
        :param process_pattern: xdomea process element extracted from message pattern
        :param file_evaluation: parent file evaluation
        :param first_process: true if process pattern is the first processed pattern
        :param process_structure_config: configuration of the generated process structure
        """
        # first process is always archived to guarantee a valid message structure
        if first_process and file_evaluation == XdomeaEvaluation.ARCHIVE:
            process_evaluation = XdomeaEvaluation.ARCHIVE
        # process evaluation is equal to file evaluation if file evaluation is discard or evaluate
        # process evaluation is also equal to file evaluation if processes are configured to inherit
        elif file_evaluation != XdomeaEvaluation.ARCHIVE \
                or process_structure_config.process_evaluation == 'inherit':
            process_evaluation = file_evaluation
        # random evaluation
        else:
            process_evaluation = random.choice(list(XdomeaEvaluation))
        process_id = get_xdomea_object_id(process_pattern)
        self.record_object_evaluation[process_id] = process_evaluation

    def __clean_file_content(self, file_pattern: etree.Element):
        file_content = file_pattern.find('./xdomea:Akteninhalt', namespaces=file_pattern.nsmap)
        for content_object in list(file_content):
            file_content.remove(content_object)

        if self.xdomea_schema_version in ["2.3.0", "2.4.0"]:
            subfiles = file_pattern.findall('./xdomea:Teilakte', namespaces=file_pattern.nsmap)
            for subfile in subfiles:
                file_pattern.remove(subfile)