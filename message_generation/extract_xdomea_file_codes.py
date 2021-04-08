from xml.etree import cElementTree


def extract_xdomea_file_type_list(xdomea_types_scheme_path) :

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


def print_xdomea_file_type_list(file_type_list) :

  for file_type_code, file_type_name in file_type_list.items() :
    print(file_type_code + " : " + file_type_name)


def main() :

  xdomea_types_scheme_path = "xdomea_2_3_schemes/xdomea-Datentypen.xsd"
  xdoemea_file_type_list   = extract_xdomea_file_type_list(xdomea_types_scheme_path)

  print_xdomea_file_type_list(xdoemea_file_type_list)

if __name__== "__main__" :
  main()