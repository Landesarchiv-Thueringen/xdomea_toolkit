from dataclasses import dataclass
import glob
from lxml import etree
import magic
import os
import random


@dataclass
class XdomeaFileFormat:
    code: str
    name: str


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
		if xdomea_version == '3.0.0':
			FileUtil.__extract_xdomea_file_format_version_3_0_0(code_list_root_el)
		else:
			FileUtil.__extract_xdomea_file_format_pre_version_3_0_0(code_list_root_el)

	@staticmethod
	def __extract_xdomea_file_format_pre_version_3_0_0(code_list_root_el: str):
		code_list = code_list_root_el.findall(
			'xs:complexType[@name="DateiformatCodeType"]//xs:enumeration',
			namespaces=code_list_root_el.nsmap)
		FileUtil.file_format_list = []
		for code_el in code_list:
			code = code_el.get('value')
			name = code_el.findtext('.//codeName')
			FileUtil.file_format_list.append(XdomeaFileFormat(
				code=code,
				name=name,
			))

	@staticmethod
	def __extract_xdomea_file_format_version_3_0_0(code_list_root_el: str):
		code_list = code_list_root_el.findall(
			'.//SimpleCodeList/Row')
		FileUtil.file_format_list = []
		for code_el in code_list:
			code = code_el.findtext('./Value[@ColumnRef="Code"]/SimpleValue')
			name = code_el.findtext('./Value[@ColumnRef="Beschreibung"]/SimpleValue')
			FileUtil.file_format_list.append(XdomeaFileFormat(
				code=code,
				name=name,
			))

	@staticmethod
	def detect_file_format(file_path: str):
		print(magic.from_file(file_path))