from   distutils.dir_util    import copy_tree
from   glob                  import iglob
from   xml.etree             import cElementTree
from   xml.etree.ElementTree import ParseError
import shutil
import os
import zipfile


transmitter_list = ["Abgebende Stelle", "AAEF", "AAGTH", "TMIK", "LPD", "AAJ", "TMMJV", "LATh",    \
                    "LFD", "TMIL", "TSK", "TMUEN","TMBJS", "TMASGFF", "AANDH", "TFM", "TLVwA",     \
                    "AASHL", "LKA", "TMWWDG", "PIGRZ", "AGGRZ", "JVAHL", "JCHBN", "JCSON", "HZAEF",\
                    "THW", "XDOMEA"]

data_path = "C:\\Users\\Grochow.TSA\\Desktop\\LATh"
target    = "C:\\Users\\Grochow.TSA\\Desktop\\E-Akten"

scheme_namespace = "{urn:xoev-de:xdomea:schema:2.3.0}"
cElementTree.register_namespace("xdomea", "urn:xoev-de:xdomea:schema:2.3.0")

def delete_message_folder(path) :
  if os.path.exists(path) :
    # security check important for critical operation
    if os.path.commonprefix([target, path]) == target :
      shutil.rmtree(path)

for transmitter in transmitter_list :

  transmitter_root_path = os.path.join(target, transmitter)
  copy_tree(data_path, transmitter_root_path)
  generic_message_path = os.path.join(transmitter_root_path, "**\\*.zip")
  message_path_list = list(iglob(generic_message_path, recursive = True))

  for message_path in message_path_list :
    print(message_path)
    try :
      zip_message = zipfile.ZipFile(message_path, 'r')
      message_folder = os.path.splitext(message_path)[0]
      zip_message.extractall(message_folder)
      zip_message.close()

    # damaged zip file
    except zipfile.BadZipfile :
      delete_message_folder(message_folder)
      continue
    # damaged zip file
    except OSError:
      delete_message_folder(message_folder)
      continue

    generic_xml_path = os.path.join(message_folder, "**\\*Aussonderung*.xml")
    xdomea_xml_path_list = list(iglob(generic_xml_path, recursive = True))

    try :
      et_message = cElementTree.parse(xdomea_xml_path_list[0])

    # invalid xml message
    except ParseError:
      delete_message_folder(message_folder)
      continue

    for message_transmitter in et_message.iter(scheme_namespace + "Absender") :

      agency_node       = message_transmitter.find(scheme_namespace + "Behoerdenkennung")
      if agency_node is None:
        continue
      agency_id_node    = agency_node.find(scheme_namespace + "Kennung")
      if agency_id_node is None:
        continue
      id_code_node      = agency_id_node.find("code")
      id_code_node.text = transmitter

    et_message.write(xdomea_xml_path_list[0], \
                     xml_declaration = True, encoding = 'utf-8', method = "xml")

    os.remove(message_path)

    generic_message_file_path = os.path.join(message_folder, "**\\*.*")
    xdomea_file_path_list     = list(iglob(generic_message_file_path, recursive = True))

    zip_corrected = zipfile.ZipFile(message_path, "w")
    for file_path in xdomea_file_path_list :
      zip_corrected.write(file_path, os.path.relpath(file_path, message_folder))
    zip_corrected.close()

    delete_message_folder(message_folder)
