from   xml.etree import cElementTree
from   copy      import deepcopy
import random
import uuid
import glob
import zipfile
import os

class XdomeaMessageGenerator :

  def __init__(self) :

    #config
    self.xdomea_file_range       = range(1, 10)
    self.xdomea_process_range    = range(1, 4)
    self.xdomea_document_range   = range(1, 4)
    self.evaluation_random       = False
    self.test_data_path          = "Z:\\Projekt Digitales Magazin\\Testdaten\\" + \
                                   "Testdaten Vorbereitung\\Einzeldateien\\"    + \
                                   "valide\\zugelassen\\Archivierungsformat\\PDF-A\\1b\\"

    self.config_path             = "xdomea_2_3_generation_config.xml"
    self.input_config()

    self.xdomea_501_pattern_path = "xdomea_2_3_pattern/xx_Aussonderung.Anbieteverzeichnis.0501.xml"
    self.xdomea_503_pattern_path = "xdomea_2_3_pattern/xx_Aussonderung.Aussonderung.0503.xml"
    self.xdomea_target_path      = "xdomea_2_3_generated_messages/"
    self.xdomea_501_name_pattern = "_Aussonderung.Anbieteverzeichnis.0501"
    self.xdomea_503_name_pattern = "_Aussonderung.Aussonderung.0503"

    self.xdomea_process_id       = str(uuid.uuid4())
    self.xdomea_file_type_dict   = self.extract_xdomea_file_type_list()
    self.xdomea_503_file_list    = []
    self.xdomea_evaluation_desc  = ["V","A"]

    self.scheme_namespace        = "{urn:xoev-de:xdomea:schema:2.3.0}"
    self.xdomea_script_object    = self.scheme_namespace + "Schriftgutobjekt"
    self.xdomea_file             = self.scheme_namespace + "Akte"
    self.xdomea_file_content     = self.scheme_namespace + "Akteninhalt"
    self.xdomea_process          = self.scheme_namespace + "Vorgang"
    self.xdomea_document         = self.scheme_namespace + "Dokument"
    self.xdomea_document_version = self.scheme_namespace + "Version"
    self.xdomea_document_format  = self.scheme_namespace + "Format"
    self.xdomea_object_id_parent = self.scheme_namespace + "Identifikation"
    self.xdomea_object_id        = self.scheme_namespace + "ID"

    cElementTree.register_namespace("xdomea", "urn:xoev-de:xdomea:schema:2.3.0")

    self.et_501               = cElementTree.parse(self.xdomea_501_pattern_path)
    self.et_503               = cElementTree.parse(self.xdomea_503_pattern_path)
    self.et_501_script_object = None
    self.et_501_file          = None
    self.et_501_process       = None
    self.et_501_document      = None
    self.et_503_version       = None

    for script_object in self.et_501.iter(self.xdomea_script_object) :
      if self.et_501_script_object == None :
        self.et_501_script_object = script_object
      self.et_501.getroot().remove(script_object)

    for file in self.et_501_script_object.iter(self.xdomea_file) :
      if self.et_501_file == None :
        self.et_501_file = file
      self.et_501_script_object.remove(file)

    for process in self.et_501_file.iter(self.xdomea_process) :
      if self.et_501_process == None :
        self.et_501_process = process
      self.et_501_file.find(self.xdomea_file_content).remove(process)

    for document in self.et_501_process.iter(self.xdomea_document) :
      if self.et_501_document == None :
        self.et_501_document = document
      self.et_501_process.remove(document)

    et_503_document = list(self.et_503.iter(self.xdomea_document))[0]
    self.et_503_version = list(et_503_document.iter(self.xdomea_document_version))[0]

    for script_object in self.et_503.iter(self.xdomea_script_object) :
      self.et_503.getroot().remove(script_object)

  def input_config(self) :

    config_et = cElementTree.parse(self.config_path)

    file_number_string     = (config_et.find("file_number").text).split("-")
    process_number_string  = (config_et.find("process_number").text).split("-")
    document_number_string = (config_et.find("document_number").text).split("-")
    evaluation_method      = (config_et.find("evaluation").text)
    data_root              = (config_et.find("test_root").text)
    test_folder            = (config_et.find("test_folder").text)
    test_data_folder       = os.path.join(data_root, test_folder)

    if os.path.isdir(test_data_folder) :
      self.test_data_path = test_data_folder

    if evaluation_method == "random" :
      self.evaluation_random = True

    if len(file_number_string) == 1 :
      self.xdomea_file_range = [int(file_number_string[0])]
    elif len(file_number_string) == 2 :
      self.xdomea_file_range = \
        range(int(file_number_string[0]), int(file_number_string[1]))

    if len(process_number_string) == 1 :
      self.xdomea_process_range = [int(process_number_string[0])]
    elif len(process_number_string) == 2 :
      self.xdomea_process_range = \
        range(int(process_number_string[0]), int(process_number_string[1]))

    if len(document_number_string) == 1 :
      self.xdomea_document_range = [int(document_number_string[0])]
    elif len(document_number_string) == 2 :
      self.xdomea_document_range = \
        range(int(document_number_string[0]), int(document_number_string[1]))


  def export_xdomea_message(self) :

    message_path_501   = self.xdomea_process_id + self.xdomea_501_name_pattern + ".xml"
    container_path_501 = self.xdomea_target_path + self.xdomea_process_id +\
                         self.xdomea_501_name_pattern + ".zip"
    message_path_503   = self.xdomea_process_id + self.xdomea_503_name_pattern + ".xml"
    container_path_503 = self.xdomea_target_path + self.xdomea_process_id +\
                         self.xdomea_503_name_pattern + ".zip"

    self.et_501.write(message_path_501, xml_declaration = True, encoding = 'utf-8', method = "xml")
    self.et_503.write(message_path_503, xml_declaration = True, encoding = 'utf-8', method = "xml")

    zip_501 = zipfile.ZipFile(container_path_501, "w")
    zip_501.write(message_path_501)
    zip_501.close()

    zip_503 = zipfile.ZipFile(container_path_503, "w")

    zip_503.write(message_path_503)
    for file in self.xdomea_503_file_list :
      zip_503.write(file[0], file[1])
    zip_503.close()

    os.remove(message_path_501)
    os.remove(message_path_503)


  def generate_xdomea_structure(self) :

    # 501: set xdomea process id
    self.set_xdomea_process_id(self.et_501)

    # 501: generate script objects in root node
    for file_index in range(random.choice(self.xdomea_file_range)) :
      self.et_501.getroot().append(self.get_xdomea_script_object_node())

    # 501: generate file nodes per script object
    for script_object in self.et_501.iter(self.xdomea_script_object) :
      script_object.append(self.get_xdomea_file_node())

    # 501: generate process nodes per file object
    for file in self.et_501.iter(self.xdomea_file) :
      for process_index in range(random.choice(self.xdomea_process_range)) :
        (file.find(self.xdomea_file_content)).append(self.get_xdomea_process_node())

    # 501: generate document nodes per process
    for process in self.et_501.iter(self.xdomea_process) :
      for document_index in range(random.choice(self.xdomea_document_range)) :
        process.append(deepcopy(self.get_xdomea_document_node()))

    # 501: write readable metadata
    self.set_xdomea_metadata(self.et_501, random.randint(1000, 9999))

    # 503: set xdomea process id
    self.set_xdomea_process_id(self.et_503)

    # 503: copy 501 message structure to 503
    for script_object in self.et_501.iter(self.xdomea_script_object) :
      self.et_503.getroot().append(deepcopy(script_object))

    # 503: set evaluation decision
    if self.evaluation_random :
      self.set_random_evaluation_decision(self.et_503)
    else :
      self.set_positiv_evaluation_decision(self.et_503)

    # 503: write evaluation decision info
    self.write_evaluation_decision_info(self.et_503)

    # 503: remove all xdomea objects with evaluation decision V
    self.remove_destroyed_objects(self.et_503)

    # 503: insert document version in document nodes
    for process in self.et_503.iter(self.xdomea_process) :
      for document in process.iter(self.xdomea_document) :
        if self.get_evaluation_decision(process) == self.xdomea_evaluation_desc[1] :
          document.append(self.get_xdomea_document_version_node())

  def get_xdomea_script_object_node(self) :
    script_object_node = deepcopy(self.et_501_script_object)
    return script_object_node

  def get_xdomea_file_node(self) :
    file_node = deepcopy(self.et_501_file)
    self.set_new_xdomea_object_id(file_node)
    return file_node

  def get_xdomea_process_node(self) :
    process_node = deepcopy(self.et_501_process)
    self.set_new_xdomea_object_id(process_node)
    return process_node

  def get_xdomea_document_node(self) :
    document_node = deepcopy(self.et_501_document)
    self.set_new_xdomea_object_id(document_node)
    return document_node

  def get_xdomea_document_version_node(self) :
    # extract xdomea xml nodes
    document_version_node = deepcopy(self.et_503_version)
    format_node           = document_version_node.find(self.xdomea_document_format);
    format_name_node      = format_node.find(self.scheme_namespace + "Name");
    format_version_node   = format_node.find(self.scheme_namespace + "Version");
    format_file_node      = format_node.find(self.scheme_namespace + "Primaerdokument");
    format_file_path_node = format_file_node.find(self.scheme_namespace + "Dateiname")

    # get random file from testset
    file_name        = self.get_random_file_version()
    xdomea_file_name = str(uuid.uuid4()) + "_" + os.path.basename(file_name)
    file_extension   = os.path.splitext(file_name)[1][1:]
    file_hint        = file_extension

    # choose correct pdf version dependent on path
    if file_extension == "pdf" and "PDF-A" in file_name :
      file_hint = "Archival"

    xdomea_format_info = self.get_xdomea_format_info(file_hint)

    # set correct version node metadata
    (format_name_node.find("code")).text = xdomea_format_info[0]
    (format_name_node.find("name")).text = xdomea_format_info[1]
    format_version_node.text             = "Formatversion (Testdaten)"
    format_file_path_node.text           = xdomea_file_name

    self.xdomea_503_file_list.append([file_name, xdomea_file_name])

    return document_version_node

  def get_xdomea_object_id(self, xdomea_object) :
    xdomea_object_id_parent = xdomea_object.find(self.xdomea_object_id_parent)
    xdomea_object_id        = xdomea_object_id_parent.find(self.xdomea_object_id)
    return xdomea_object_id.text

  def set_xdomea_process_id(self, xdomea_root_element) :
    xdomea_header_node          = xdomea_root_element.find(self.scheme_namespace + "Kopf")
    xdomea_process_id_node      = xdomea_header_node.find(self.scheme_namespace + "ProzessID")
    xdomea_process_id_node.text = self.xdomea_process_id

  def set_new_xdomea_object_id(self, xdomea_object) :
    xdomea_object_id_parent = xdomea_object.find(self.xdomea_object_id_parent)
    xdomea_object_id        = xdomea_object_id_parent.find(self.xdomea_object_id)
    xdomea_object_id.text   = str(uuid.uuid4())

  def set_positiv_evaluation_decision(self, xdomea_root_element) :
    for evaluation in xdomea_root_element.iter(self.scheme_namespace + "Aussonderungsart") :
      (evaluation.find("code")).text = "A"

  def set_random_evaluation_decision(self, xdomea_root_element) :

    first_file = True
    for file in xdomea_root_element.iter(self.xdomea_file) :
      file_evaluation = self.xdomea_evaluation_desc[1]
      if first_file :
        first_file = False
      else :
        file_evaluation = random.choice(self.xdomea_evaluation_desc)
      first_process   = True
      self.set_evaluation_decision(file, file_evaluation)
      for process in file.iter(self.xdomea_process) :
        # currently the evaluation decision of a process must be equal to that of the parent file
        process_evaluation = file_evaluation
        # process_evaluation = self.xdomea_evaluation_desc[1]
        # # if parent object is not archivable
        # if file_evaluation == self.xdomea_evaluation_desc[0] :
        #   process_evaluation = self.xdomea_evaluation_desc[0]
        # # if parent is archivable and the current process is the first child
        # elif first_process :
        #   first_process = False
        #   process_evaluation = self.xdomea_evaluation_desc[1]
        # else :
        #   process_evaluation = random.choice(self.xdomea_evaluation_desc)
        self.set_evaluation_decision(process, process_evaluation)

  def write_evaluation_decision_info(self, xdomea_root_element) :
    evaluation_info_name =  self.xdomea_process_id + "_Bewertungsentscheidung.txt"
    evaluation_info_path = os.path.join(self.xdomea_target_path, evaluation_info_name)

    evaluation_dec_text  = ""
    file_number          = 1

    for file in xdomea_root_element.iter(self.xdomea_file) :
      process_number = 1
      evaluation_dec_text += "[Akte " + str(file_number) +  " xdomeaID: "
      evaluation_dec_text += self.get_xdomea_object_id(file)
      evaluation_dec_text += "] -> "
      evaluation_dec_text += self.get_evaluation_decision_description(file)
      evaluation_dec_text += "\n"

      for process in file.iter(self.xdomea_process) :
        evaluation_dec_text += "  [Vorgang " + str(file_number ) + "." + str(process_number)
        evaluation_dec_text += " xdomeaID: "
        evaluation_dec_text += self.get_xdomea_object_id(process)
        evaluation_dec_text += "] -> "
        evaluation_dec_text += self.get_evaluation_decision_description(process)
        evaluation_dec_text += "\n"
        process_number += 1

      file_number += 1
      evaluation_dec_text += "\n"

    file_object = open(evaluation_info_path,'w')
    file_object.write(evaluation_dec_text)
    file_object.close()

  def get_evaluation_decision_description(self, xdomea_object) :

    evaluation_decision = self.get_xdomea_object_id(xdomea_object)

    if self.get_evaluation_decision(xdomea_object) == "A" :
      description = "archivieren"

    elif self.get_evaluation_decision(xdomea_object) == "V" :
      description = "vernichten"

    elif self.get_evaluation_decision(xdomea_object) == "B" :
      description = "bewerten"

    else :
      description = "unbekannt"

    return description

  def set_xdomea_metadata(self, xdomea_root_element, file_plan_indicator) :

    # change xdomea subject and indicator
    file_number = 1

    for file_node in xdomea_root_element.iter(self.scheme_namespace + "Akte") :

      file_subject = "Akte " + str(file_number)
      file_indicator = str(file_plan_indicator) + "-" + str(file_number)
      self.set_object_subject(file_node, file_subject)
      self.set_file_plan_indicator(file_node, file_plan_indicator)
      self.set_object_indicator(file_node, file_indicator)
      process_number = 1

      for process_node in file_node.iter(self.scheme_namespace + "Vorgang") :

        process_subject = "Vorgang " + str(file_number) + "." + str(process_number)
        process_indicator = file_indicator + "." + str(process_number)
        self.set_object_subject(process_node, process_subject)
        self.set_object_indicator(process_node, process_indicator)
        document_number = 1

        for document_node in process_node.iter(self.scheme_namespace + "Dokument") :

          document_subject = "Dokument " + str(file_number) + "." + str(process_number) \
                                         + "-" + str(document_number)
          document_indicator = process_indicator + "-" + str(document_number)
          self.set_object_subject(document_node, document_subject)
          self.set_object_indicator(document_node, document_indicator)
          document_number += 1
        process_number += 1
      file_number += 1

  def remove_destroyed_objects(self, xdomea_root_element) :

    removable_script_object_list = []
    removable_process_list       = []
    process_parent_list          = []

    for script_object in xdomea_root_element.iter(self.xdomea_script_object) :

      for file in script_object.iter(self.xdomea_file) :

        for process in file.iter(self.xdomea_process) :

          if self.get_evaluation_decision(process) == self.xdomea_evaluation_desc[0] :
            file_content = file.find(self.scheme_namespace + "Akteninhalt")
            removable_process_list.append(process)
            process_parent_list.append(file_content)

        if self.get_evaluation_decision(file) == self.xdomea_evaluation_desc[0] :
          removable_script_object_list.append(script_object)

    for process, process_parent in zip(removable_process_list, process_parent_list) :
      process_parent.remove(process)

    for script_object in removable_script_object_list :
      xdomea_root_element.getroot().remove(script_object)

  def get_evaluation_decision(self, xdomea_object) :
    archive_metadate_node = xdomea_object.find(self.scheme_namespace + "ArchivspezifischeMetadaten")
    evaluation_node       = archive_metadate_node.find(self.scheme_namespace + "Aussonderungsart")
    evaluation_code_node  = evaluation_node.find("code")

    return evaluation_code_node.text

  def set_evaluation_decision(self, xdomea_object, evaluation) :
    archive_metadate_node = xdomea_object.find(self.scheme_namespace + "ArchivspezifischeMetadaten")
    evaluation_node       = archive_metadate_node.find(self.scheme_namespace + "Aussonderungsart")
    evaluation_code_node  = evaluation_node.find("code")

    evaluation_code_node.text = evaluation

  def set_object_subject(self, xdomea_object, subject) :
    metadata_node = xdomea_object.find(self.scheme_namespace + "AllgemeineMetadaten")
    subject_node = metadata_node.find(self.scheme_namespace + "Betreff")
    subject_node.text = subject

  def set_file_plan_indicator(self, xdomea_file, file_plan_indicator) :
    metadata_node = xdomea_file.find(self.scheme_namespace + "AllgemeineMetadaten")
    file_plan_indicator_node = metadata_node.find(self.scheme_namespace + "Aktenplaneinheit")
    indicator_node = file_plan_indicator_node.find(self.scheme_namespace + "Kennzeichen")
    indicator_node.text = str(file_plan_indicator)

  def set_object_indicator(self, xdomea_object, indicator) :
    metadata_node = xdomea_object.find(self.scheme_namespace + "AllgemeineMetadaten")
    indicator_node = metadata_node.find(self.scheme_namespace + "Kennzeichen")
    indicator_node.text = indicator

  def get_random_file_version(self) :

    full_path = os.path.join(self.test_data_path,"**\\*.*")

    file_path_list = list(glob.iglob(full_path, recursive = True))
    file_list      = []

    for file_path in file_path_list :
      if os.path.isfile(file_path) :
        file_list.append(deepcopy(file_path))

    random_file_index = random.randint(0, len(file_list) - 1)

    return file_list[random_file_index]

  def get_xdomea_format_info(self, format_hint) :

    for file_type_code, file_type_name in self.xdomea_file_type_dict.items() :
      if format_hint in file_type_name :
        return (file_type_code, file_type_name)
    # prevent endless loop
    return None if "Sonstiges" in format_hint else self.get_xdomea_format_info("Sonstiges")

  def extract_xdomea_file_type_list(self) :

    xdomea_types_scheme_path = "xdomea_2_3_schemes/xdomea-Datentypen.xsd"

    scheme_namespace = "{http://www.w3.org/2001/XMLSchema}"

    et = cElementTree.parse(xdomea_types_scheme_path)

    file_type_code_list = []
    file_type_name_list = []

    for code_list in et.iter(scheme_namespace + "complexType") :

      if code_list.attrib["name"] == "DateiformatCodeType" :

        for code_list_element in code_list.iter(scheme_namespace + "enumeration") :
          file_type_code_list.append(code_list_element.attrib["value"])

          for code_name in code_list_element.iter("codeName") :
            file_type_name_list.append(code_name.text)

    return dict(zip(file_type_code_list, file_type_name_list))

  def print_xdomea_file_type_list(self, file_type_list) :

    for file_type_code, file_type_name in file_type_list.items() :
      print(file_type_code + " : " + file_type_name)


def main() :

  xmg = XdomeaMessageGenerator()
  xmg.generate_xdomea_structure()
  xmg.export_xdomea_message()

if __name__== "__main__" :
  main()
