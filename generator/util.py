import glob
import magic
import os
import random


class FileUtil:

	file_pool: list[str]
	path_wildcard: str

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
	def get_file_format(file_path: str):
		print(magic.from_file(file_path))