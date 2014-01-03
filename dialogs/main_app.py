# -*- coding: utf-8 -*-

"""
Main application GUI module
"""

__version__ = "$Id$"

import logging
import sys
import os
import errno

from PySide.QtGui import *
from PySide.QtCore import *

import win32com.shell.shell as shell
from forms.mainform import Ui_MainWindow

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class MainApp(QMainWindow, Ui_MainWindow):
    """
    Main application GUI form.
    - setup main window dialog
    - connects signals from dialogs widgets
    """

    def __init__(self):
        super(MainApp, self).__init__()
        self.root_path = os.path.dirname(sys.argv[0])
        self.setupUi(self)
        self.setupFileBrowser()

        logger.debug("Main application dialog initialized")

    def setupFileBrowser(self):
        # init media library folder
        os_data_folder = QDesktopServices.storageLocation(QDesktopServices.DataLocation)
        media_lib_path = os.path.join(os_data_folder, 'library')
        try:
            os.makedirs(media_lib_path)
        except OSError, exception:
            if exception.errno != errno.EEXIST:
                logger.exception("Unable to create media library folder on path: %s", media_lib_path)
                raise
        else:
            logger.debug("Media library folder created")

        self.fileBrowserModel = QFileSystemModel(self)
        self.fileBrowserModel.setRootPath(media_lib_path)
        self.fileBrowserModel.setResolveSymlinks(True)

        self.fileBrowser.setModel(self.fileBrowserModel)
        self.fileBrowser.setRootIndex(self.fileBrowserModel.index(media_lib_path))
        for i in range(1, self.fileBrowserModel.columnCount()):
            self.fileBrowser.setColumnHidden(i, True)

        # winsym_path = os.path.join(self.root_path, "tools", 'winsym.pyc')
        # winsym_result = os.path.join(self.root_path, "tools", 'winsym.txt')
        # type = '1'    # folder
        # source_folder = r"D:\MP3"
        # target_folder = os.path.join(media_lib_path, 'MP3')
        # params = ' '.join([winsym_path, type, source_folder, target_folder, winsym_result])
        #
        # shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)
