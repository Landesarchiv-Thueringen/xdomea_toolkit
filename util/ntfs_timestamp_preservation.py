from datetime import datetime
import os
import sys
import time
from zipfile import ZipFile

def convert_to_windows_timestamp(unix_timestamp):
    windows_epoch = datetime(1601, 1, 1)
    unix_date_time = datetime.utcfromtimestamp(unix_timestamp)
    windows_timestamp = (unix_date_time - windows_epoch).total_seconds()
    return int(windows_timestamp * 10000000).to_bytes(8, byteorder='little')

def get_ntfs_zip_info(path):
    ntfs_block_tag = bytes.fromhex('0a 00')
    ntfs_block_size = bytes.fromhex('20 00')
    ntfs_reserved = bytes.fromhex('00 00 00 00')
    ntfs_tag1 = bytes.fromhex('01 00')
    ntfs_tag1_size = bytes.fromhex('18 00')
    ntfs_mtime = os.path.getmtime(path)
    ntfs_atime = os.path.getatime(path)
    ntfs_ctime = os.path.getctime(path)
    ntfs_mtime_windows_timestamp = convert_to_windows_timestamp(ntfs_mtime)
    ntfs_atime_windows_timestamp = convert_to_windows_timestamp(ntfs_atime)
    ntfs_ctime_windows_timestamp = convert_to_windows_timestamp(ntfs_ctime)
    ntfs_block = ntfs_block_tag                 \
               + ntfs_block_size                \
               + ntfs_reserved                  \
               + ntfs_tag1                      \
               + ntfs_tag1_size                 \
               + ntfs_mtime_windows_timestamp   \
               + ntfs_atime_windows_timestamp   \
               + ntfs_ctime_windows_timestamp
    return ntfs_block

def add_ntfs_info(zip_file, file_path):
    info = zip_file.getinfo(file_path)
    info.extra = get_ntfs_zip_info(file_path)
