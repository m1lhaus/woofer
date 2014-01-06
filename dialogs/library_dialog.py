# -*- coding: utf-8 -*-

"""
"""

__version__ = "$Id$"

import logging
import json
import os

from PySide.QtGui import *
from PySide.QtCore import *

from forms.library_form import Ui_libraryDialog

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class LibraryDialog(QDialog, Ui_libraryDialog):

    def __init__(self, mediaLibFile, parent):
        super(LibraryDialog, self).__init__(parent)
        self.setupUi(self)

        try:
            with open(mediaLibFile, 'r') as mediaFile:
                mediaFolders = json.load(mediaFile)
        except Exception:
            logger.exception("Error when reading media file data")
            # TODO handle error
            return

        for folder in mediaFolders:
            folder = os.path.normpath(folder)
            self.folderList.addItem(folder)

    def addFolder(self):
        pass

    def removeFolder(self):
        pass