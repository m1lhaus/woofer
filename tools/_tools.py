# -*- coding: utf-8 -*-
#
# Woofer - free open-source cross-platform music player
# Copyright (C) 2015 Milan Herbig <milanherbig[at]gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

"""
Various tools and functions
"""

import os
import sys
import logging
import zipfile
import errno
import shutil
import platform
import traceback

import ujson

from PyQt5.QtCore import QStandardPaths

logger = logging.getLogger(__name__)

# directories and files
APP_ROOT_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
OS_DATA_DIR = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
if OS_DATA_DIR and os.path.exists(OS_DATA_DIR):
    OS_DATA_DIR = os.path.normpath(OS_DATA_DIR)
    OS_DATA_DIR = os.path.join(OS_DATA_DIR, "WooferPlayer")
else:
    OS_DATA_DIR = APP_ROOT_DIR
LOG_DIR = os.path.join(OS_DATA_DIR, 'log')
DATA_DIR = os.path.join(OS_DATA_DIR, 'data')

BUILD_INFO_FILE = os.path.join(APP_ROOT_DIR, "build.info")

# misc
IS_WIN32_EXE = sys.argv[0].endswith(".exe")
IS_PYTHON_FILE = sys.argv[0].endswith((".py", ".pyc"))
PLATFORM = 32 if platform.architecture()[0] == '32bit' else 64


def checkBinaryType(path):
    """
    Method reads PE header and get binary type (x32 vs x64)
    @param path: path to file
    @return: binary type str
    """
    if not os.path.isfile(path):
        raise Exception("Given path '%s' not found!" % path)

    import struct

    bin_type = None
    IMAGE_FILE_MACHINE_I386 = 332
    IMAGE_FILE_MACHINE_IA64 = 512
    IMAGE_FILE_MACHINE_AMD64 = 34404

    with open(path, "rb") as f:
        s = f.read(2)
        if s != b"MZ":
            print("check_binary_type - Not an EXE file!")

        else:
            f.seek(60)
            s = f.read(4)
            header_offset = struct.unpack("<L", s)[0]
            f.seek(header_offset + 4)
            s = f.read(2)
            machine = struct.unpack("<H", s)[0]

            if machine == IMAGE_FILE_MACHINE_I386:
                bin_type = "IA-32 (32-bit x86)"
            elif machine == IMAGE_FILE_MACHINE_IA64:
                bin_type = "IA-64 (Itanium)"
            elif machine == IMAGE_FILE_MACHINE_AMD64:
                bin_type = "AMD64 (64-bit x86)"
            else:
                bin_type = "Unknown"

    return bin_type


def extractZIPFiles(src, dst):
    """
    Extracts all files from ZIP archive to given directory.
    @param src: source ZIP file
    @param dst: where to extract files
    """

    def get_members(zip_object):
        parts = []
        for name in zip_object.namelist():
            if not name.endswith('/'):
                parts.append(name.split('/')[:-1])
        prefix = os.path.commonprefix(parts) or ''
        if prefix:
            prefix = '/'.join(prefix) + '/'
        offset = len(prefix)
        for zipinfo in zip_object.infolist():
            name = zipinfo.filename
            if len(name) > offset:
                zipinfo.filename = name[offset:]
                yield zipinfo

    logger.debug("Extracting new files to '%s' ...", dst)
    with zipfile.ZipFile(src, 'r') as zip_object:
        zip_object.extractall(dst, get_members(zip_object))


def removeFile(filepath):
    """
    Remove file permanently.
    @param filepath: string path
    """
    logger.debug("Removing file '%s'...", filepath)
    try:
        os.remove(filepath)
    except OSError as e:
        if e.errno != errno.ENOENT:
            logger.exception("Error when removing file '%s'", filepath)
    except Exception:
        logger.exception("Error when removing file '%s'", filepath)


def removeFolder(folderpath):
    """
    Remove file permanently.
    @param folderpath: string path
    """
    logger.debug("Removing folder '%s'...", folderpath)
    try:
        shutil.rmtree(folderpath)
    except Exception:
        logger.exception("Error when removing directory '%s'!", folderpath)


def getFullTraceback():
    """
    Method grabs last available traceback error and makes conversion to string.
    @return: full traceback error string
    """
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]      # last one would be full_stack()
    if exc is not None:                         # i.e. if an exception is present
        del stack[-1]                           # remove call of full_stack, the printed exception
                                                # will contain the caught exception caller instead
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
        stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr


def loadBuildInfo():
    build_info_file = os.path.join(APP_ROOT_DIR, "build.info")
    if not os.path.isfile(build_info_file):
        logger.error("Unable to locate build.info file!")
        return {}

    with open(build_info_file, 'r') as f:
        build_data = ujson.load(f)               # dict

    return build_data


class ErrorMessages(object):
    """
    Error messages enums.
    """
    WARNING = 0
    ERROR = 1
    CRITICAL = 2
    INFO = 3
