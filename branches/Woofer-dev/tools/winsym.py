# -*- coding: utf-8 -*-

"""
Creates symbolic link on Windows Vista and newer
"""

__version__ = "$Id$"

import sys
import os

import win32file
import pywintypes

FILE_SYM = 0
FOLDER_SYM = 1

# import win32com.shell.shell as shell
# winsym_path = os.path.join(self.root_path, "tools", 'winsym.pyc')
# winsym_result = os.path.join(self.root_path, "tools", 'winsym.txt')
# type = '1'    # folder
# source_folder = r"D:\MP3"
# target_folder = os.path.join(self.medialib_path, 'MP3')
# params = ' '.join([winsym_path, type, source_folder, target_folder, winsym_result])
#
# shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)

if __name__ == "__main__":
    file_path = sys.argv[0]
    type = sys.argv[1]
    source = sys.argv[2]
    target = sys.argv[3]
    result = sys.argv[4]

    try:
        status = win32file.CreateSymbolicLink(target, source, int(type))
    except pywintypes.error, details:
        err_code = details[0]
    else:
        err_code = 0
        details = ""

    with open(os.path.join(os.path.dirname(__file__), "winsym.txt"), 'w') as f:
        f.write(str(err_code))
        f.write(os.linesep)
        f.write(str(details))