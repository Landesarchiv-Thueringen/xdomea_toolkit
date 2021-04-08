from   glob      import iglob
from   xml.etree import cElementTree
import os
import shutil
import tempfile
import uuid
import zipfile

def delete_message_folder(path) :
  # security check important for critical operation
  if os.path.commonprefix([tempfile.gettempdir(), path]) == tempfile.gettempdir() :
    shutil.rmtree(path)

def set_xdomea_process_id(xdomea_root_element, process_id) :
  scheme_namespace            = "{urn:xoev-de:xdomea:schema:2.3.0}"
  xdomea_header_node          = xdomea_root_element.find(scheme_namespace + "Kopf")
  xdomea_process_id_node      = xdomea_header_node.find(scheme_namespace + "ProzessID")
  xdomea_process_id_node.text = process_id

def main() :

  xdomea_501_name_pattern = "_Aussonderung.Anbieteverzeichnis.0501"
  xdomea_503_name_pattern = "_Aussonderung.Aussonderung.0503"

  cElementTree.register_namespace("xdomea", "urn:xoev-de:xdomea:schema:2.3.0")

  generic_message_path = os.path.join(os.getcwd(), "**\\*Aussonderung*.zip")
  message_path_list    = list(iglob(generic_message_path, recursive = True))

  prev_message_path = ""

  success_count = 0
  fail_count  = 0
  ignore_count = 0

  # important message_path_list must be sorted
  for message_path in message_path_list :

    print(message_path)

    if "Container_invalide" in message_path or "Nachrichten_invalide" in message_path :
      ignore_count += 1
      continue

    common_dir = os.path.commonprefix([os.path.dirname(prev_message_path), \
                                       os.path.dirname(message_path)])
    if common_dir != os.path.dirname(message_path) :
      new_process_id = str(uuid.uuid4())
      prev_message_path = message_path

    try :
      zip_message = zipfile.ZipFile(message_path, 'r')
      message_folder = os.path.join(tempfile.gettempdir(), \
        os.path.basename(os.path.dirname(os.path.splitext(message_path)[0])))
      zip_message.extractall(message_folder)
      zip_message.close()

    # damaged zip file
    except zipfile.BadZipfile :
      fail_count += 1
      delete_message_folder(message_folder)
      continue

    generic_xml_path = os.path.join(message_folder, "**\\*Aussonderung*.xml")
    xdomea_xml_path_list = list(iglob(generic_xml_path, recursive = True))
    xdomea_xml_path = xdomea_xml_path_list[0]

    xml_filename = os.path.basename(xdomea_xml_path)

    if xdomea_501_name_pattern in xml_filename :
      xdomea_name_pattern = xdomea_501_name_pattern

    elif xdomea_503_name_pattern in xml_filename :
      xdomea_name_pattern = xdomea_503_name_pattern

    else :
      continue

    try :
      et_message = cElementTree.parse(xdomea_xml_path)

    # invalid xml message
    except ParseError:
      fail_count += 1
      delete_message_folder(message_folder)
      continue

    set_xdomea_process_id(et_message, new_process_id)

    new_message_name = new_process_id + xdomea_name_pattern + ".xml"
    new_message_path = os.path.join(message_folder, new_message_name)
    et_message.write(new_message_path, \
                     xml_declaration = True, encoding = 'utf-8', method = "xml")
    os.remove(xdomea_xml_path)

    new_container_name = new_process_id + xdomea_name_pattern + ".zip"
    new_container_path = os.path.join(os.path.dirname(message_path), new_container_name)

    generic_message_file_path = os.path.join(message_folder, "**\\*.*")
    xdomea_file_path_list     = list(iglob(generic_message_file_path, recursive = True))

    zip_corrected = zipfile.ZipFile(new_container_path, "w", zipfile.ZIP_DEFLATED)
    for file_path in xdomea_file_path_list :
      zip_corrected.write(file_path, os.path.relpath(file_path, message_folder))
    zip_corrected.close();

    os.remove(message_path)
    delete_message_folder(message_folder)

    evaluation_generic_file_name = "_Bewertungsentscheidung.txt"
    evaluation_generic_file_path = os.path.join(os.path.dirname(message_path), \
    "*" + evaluation_generic_file_name)
    new_evaluation_name = new_process_id + evaluation_generic_file_name
    new_evaluation_path = os.path.join(os.path.dirname(message_path), new_evaluation_name)
    evaluation_file_path_list = list(iglob(evaluation_generic_file_path))

    for evaluation_file_path in evaluation_file_path_list :

      os.rename(evaluation_file_path, new_evaluation_path)

    success_count += 1

  print("\n\n")
  print("UUID-Wechsel Ergebnis")
  print("\n")
  print("erfolgreich:\t" + str(success_count))
  print("fehlgeschlagen:\t" + str(fail_count))
  print("ignoriert:\t" + str(ignore_count))
  print("\n\n")

  os.system("PAUSE")


if __name__== "__main__" :
  main()
