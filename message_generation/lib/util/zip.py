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

from datetime import datetime
import os
import sys
import time
from zipfile import ZipFile


class ZipUtil:

    @staticmethod
    def convert_to_windows_timestamp(unix_timestamp):
        windows_epoch = datetime(1601, 1, 1)
        unix_date_time = datetime.utcfromtimestamp(unix_timestamp)
        windows_timestamp = (unix_date_time - windows_epoch).total_seconds()
        return int(windows_timestamp * 10000000).to_bytes(8, byteorder='little')

    @staticmethod
    def get_ntfs_zip_info(path):
        ntfs_block_tag = bytes.fromhex('0a 00')
        ntfs_block_size = bytes.fromhex('20 00')
        ntfs_reserved = bytes.fromhex('00 00 00 00')
        ntfs_tag1 = bytes.fromhex('01 00')
        ntfs_tag1_size = bytes.fromhex('18 00')
        ntfs_mtime = os.path.getmtime(path)
        ntfs_atime = os.path.getatime(path)
        ntfs_ctime = os.path.getctime(path)
        ntfs_mtime_windows_timestamp = ZipUtil.convert_to_windows_timestamp(ntfs_mtime)
        ntfs_atime_windows_timestamp = ZipUtil.convert_to_windows_timestamp(ntfs_atime)
        ntfs_ctime_windows_timestamp = ZipUtil.convert_to_windows_timestamp(ntfs_ctime)
        ntfs_block = ntfs_block_tag                 \
                   + ntfs_block_size                \
                   + ntfs_reserved                  \
                   + ntfs_tag1                      \
                   + ntfs_tag1_size                 \
                   + ntfs_mtime_windows_timestamp   \
                   + ntfs_atime_windows_timestamp   \
                   + ntfs_ctime_windows_timestamp
        return ntfs_block

    @staticmethod
    def add_ntfs_info(zip_file, system_file_path, zip_file_path):
        info = zip_file.getinfo(zip_file_path)
        info.extra = ZipUtil.get_ntfs_zip_info(system_file_path)
