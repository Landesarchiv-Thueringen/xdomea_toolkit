from dataclasses import dataclass
import glob
from lxml import etree
import magic
import os
import random
import uuid


@dataclass
class XdomeaFileFormat:
    code: str
    name: str
    suffix: str


@dataclass
class FileInfo:
    xdomea_file_format: XdomeaFileFormat
    detected_file_info: str
    detected_format_name: str
    detected_format_version: str
    xdomea_uuid: str
    original_file_name: str
    xdomea_file_name: str
    path: str


class FileUtil:

	file_pool: list[str]
	path_wildcard: str
	file_format_list: list[XdomeaFileFormat]

	@staticmethod
	def init_file_pool(test_data_path: str):
		FileUtil.path_wildcard = os.path.join(test_data_path, '**/*')
		FileUtil.__init_file_pool()

	@staticmethod
	def __init_file_pool():
		assert FileUtil.path_wildcard is not None
		path_list = glob.glob(FileUtil.path_wildcard, recursive=True)
		FileUtil.file_pool = [path for path in path_list if os.path.isfile(path)]
		assert len(FileUtil.file_pool) > 0

	@staticmethod
	def next_file() -> str:
		if len(FileUtil.file_pool) == 0:
			FileUtil.__init_file_pool()
		file_path = random.choice(FileUtil.file_pool)
		FileUtil.file_pool.remove(file_path)
		return file_path

	@staticmethod
	def extract_xdomea_file_format_list(code_list_path: str, xdomea_version: str):
		code_list_etree = etree.parse(code_list_path)
		code_list_root_el = code_list_etree.getroot()
		if xdomea_version == '2.3.0':
			FileUtil.__extract_xdomea_file_format_version_2_3_0(code_list_root_el)
		else:
			FileUtil.__extract_xdomea_file_format_post_version_2_3_0(code_list_root_el)

	@staticmethod
	def extract_format_suffix_from_name(xdomea_format_name: str) -> str:
		format_name_parts = xdomea_format_name.split('-')
		return '' if len(format_name_parts) == 1 else format_name_parts[0].strip()

	@staticmethod
	def __extract_xdomea_file_format_version_2_3_0(code_list_root_el: str):
		code_list = code_list_root_el.findall(
			'xs:complexType[@name="DateiformatCodeType"]//xs:enumeration',
			namespaces=code_list_root_el.nsmap)
		FileUtil.file_format_list = []
		for code_el in code_list:
			code = code_el.get('value')
			name = code_el.findtext('.//codeName')
			suffix = FileUtil.extract_format_suffix_from_name(name)
			FileUtil.file_format_list.append(XdomeaFileFormat(
				code=code,
				name=name,
				suffix=suffix,
			))

	@staticmethod
	def __extract_xdomea_file_format_post_version_2_3_0(code_list_root_el: str):
		code_list = code_list_root_el.findall(
			'.//SimpleCodeList/Row')
		FileUtil.file_format_list = []
		for code_el in code_list:
			code = code_el.findtext('./Value[@ColumnRef="Code"]/SimpleValue')
			name = code_el.findtext('./Value[@ColumnRef="Beschreibung"]/SimpleValue')
			suffix = FileUtil.extract_format_suffix_from_name(name)
			FileUtil.file_format_list.append(XdomeaFileFormat(
				code=code,
				name=name,
				suffix=suffix,
			))

	@staticmethod
	def detect_file_format(file_path: str) -> str:
		return magic.from_file(file_path)

	@staticmethod
	def extract_format_name(detected_file_info: str) -> str:
		info_list = detected_file_info.split(',')
		return info_list[0]

	@staticmethod
	def extract_format_version(detected_file_info: str) -> str:
		info_list = detected_file_info.split(',')
		version_info_list = [info for info in info_list if 'version' in info]
		if len(version_info_list) == 0:
			return ''
		version_info = version_info_list[0].replace('version', '')
		return version_info.strip()

	@staticmethod
	def get_file_info(file_path: str):
		assert FileUtil.file_format_list is not None
		file_suffix = os.path.splitext(file_path)[1]
		# remove "." from file suffix for mapping with extracted xdomea formats
		if len(file_suffix) > 0 :
			file_suffix = file_suffix[1:]
		possible_format_list = [f for f in FileUtil.file_format_list if file_suffix == f.suffix]
		if len(possible_format_list) > 0:
			xdomea_format = possible_format_list[0]
		else:
			xdomea_format = FileUtil.file_format_list[-1]
		xdomea_uuid = str(uuid.uuid4())
		original_file_name = os.path.basename(file_path)
		xdomea_file_name = xdomea_uuid + '_' + original_file_name
		detected_file_info = FileUtil.detect_file_format(file_path)
		detected_format_name = FileUtil.extract_format_name(detected_file_info)
		detected_format_version = FileUtil.extract_format_version(detected_file_info)
		return FileInfo(
			xdomea_file_format=xdomea_format,
			detected_file_info=detected_file_info,
			detected_format_name=detected_format_name,
			detected_format_version=detected_format_version,
			xdomea_uuid=xdomea_uuid,
			original_file_name=original_file_name,
			xdomea_file_name=xdomea_file_name,
			path=file_path,
		)
		