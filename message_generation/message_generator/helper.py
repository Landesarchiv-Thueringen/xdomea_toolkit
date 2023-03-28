import random
from lxml import etree
from copy import deepcopy
import uuid


def get_random_number(min: int, max: int) -> int:
    """
    Necessary because range function fails if min equals max.
    :param min: min number of random range
    :param max: max number of random range
    :return random number in range
    """
    # max + 1 is necessary so that max is included in the range
    return min if min == max else random.choice(range(min, max + 1))


def get_random_pattern(pattern_list: list[etree.Element]) -> etree.Element:
    """
    Randomly chooses pattern from list, creates a copy of the element and changes its ID.
    :param pattern_list: list of xdomea patterns
    :return: choosen xdomea pattern
    """
    # randomly choose pattern
    # deepcopy is necessary if a pattern is used multiple times
    pattern = deepcopy(random.choice(pattern_list))
    # randomize xdomea ID to prevent the same xdomea IDs in the same message
    randomize_xdomea_id(pattern)
    return pattern


def randomize_xdomea_id(xdomea_element: etree.Element):
    """
            Randomizes ID from xdomea element.
            :param xdomea_element: expected xdomea elements --> (de: Akte, de: Vorgang, de: Dokument)
            """
    # change only the first ID tag that is found
    id_element = xdomea_element.find(
        './/xdomea:Identifikation/xdomea:ID',
        namespaces=xdomea_element.nsmap,
    )
    assert id_element is not None
    id_element.text = str(uuid.uuid4())


def get_xdomea_object_id(xdomea_element: etree.Element) -> str:
    """
    Get the object id of an xdomea object
    :param xdomea_element: expected xdomea elements --> (de: Akte, de: Vorgang, de: Dokument)
    :return: xdomea object ID
    """
    # find the first ID tag
    id_element = xdomea_element.find(
        './/xdomea:Identifikation/xdomea:ID',
        namespaces=xdomea_element.nsmap,
    )
    assert id_element is not None
    return id_element.text


def remove_elements(elements: list[etree.Element]):
    """
    Removes elements from xml tree.
    :param elements: element list from xml tree
    """
    for element in elements:
        remove_element(element)


def remove_element(element: etree.Element):
    """
    Removes element from xml tree.
    :param element: element from xml tree
    """
    parent = element.getparent()
    assert parent is not None
    parent.remove(element)


def replace_placeholder(element: etree.Element, placeholder: str, replacement: str):
    """
    Replaces all placeholders in element.
    :param element: element that contains placeholder
    :param placeholder: placeholder string
    :param replacement: text with which the placeholder is replaced
    """
    elements_with_placeholder = element.xpath(
        './/*[contains(text(), "' + placeholder + '")]',
        namespaces=element.nsmap,
    )
    for element in elements_with_placeholder:
        element.text = element.text.replace(placeholder, replacement)


def get_record_object_patterns(xdomea_message_pattern: etree.Element) -> list[etree.Element]:
    """
    The elements will be removed from the pattern.
    :param xdomea_message_pattern: root element of message pattern
    :return: all record objects from the xdomea message pattern
    """
    record_object_pattern_list = xdomea_message_pattern.findall(
        './/xdomea:Schriftgutobjekt', namespaces=xdomea_message_pattern.nsmap)
    return record_object_pattern_list


def remove_record_object(record_object: etree.Element):
    """
    Removes record object from xdomea message.
    :param record_object: record_object from xdomea message
    """
    xdomea_namespace = '{' + record_object.nsmap['xdomea'] + '}'
    parent = record_object.getparent()
    if parent.tag == xdomea_namespace + 'Schriftgutobjekt':
        remove_element(parent)
    else:
        remove_element(record_object)


def get_random_version_number() -> str:
    version_format = '{:4.2f}'
    version_number = random.random() * 10
    return version_format.format(version_number)
