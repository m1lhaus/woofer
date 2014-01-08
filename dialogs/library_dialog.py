# -*- coding: utf-8 -*-

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
    """
    Dialog where user can edit folders id media library:
    - add new folder
    - remove folder
    @param mediaLibFile: path to media library file
    @param parent: parent dialog
    """
    def __init__(self, mediaLibFile, parent=None):
        super(LibraryDialog, self).__init__(parent)
        self.mediaLibFile = mediaLibFile
        self.mediaFolders = []
        self.setupUi(self)
        self.setupSignals()

        try:
            with open(self.mediaLibFile, 'r') as mediaFile:
                self.mediaFolders = json.load(mediaFile)
        except IOError:
            logger.exception("Error when reading media file data from disk")
            QMessageBox(QMessageBox.Critical, "IO Error", "Error when reading media file data from disk!").exec_()
        except Exception:
            logger.exception("Error when parsing media file data from json")
            QMessageBox(QMessageBox.Critical, "Parsing error", "Error when parsing media file data from json!").exec_()

        # fill QListWidget with folders
        for folder in self.mediaFolders:
            folder = os.path.normpath(folder)
            self.folderList.addItem(folder)

    def setupSignals(self):
        self.addBtn.clicked.connect(self.addFolder)
        self.removeBtn.clicked.connect(self.removeFolder)

    @Slot()
    def addFolder(self):
        """
        When add button clicked, file dialog is opened and new directory is added
        """
        logger.debug("Opening system file dialog.")
        homeFolder = QDesktopServices.storageLocation(QDesktopServices.HomeLocation)
        newFolder = QFileDialog.getExistingDirectory(self, dir=homeFolder)

        if not newFolder:
            return

        logger.debug("Selected directory: %s", newFolder)
        newFolder = os.path.normpath(newFolder)
        self.mediaFolders.append(newFolder)
        self.folderList.addItem(newFolder)

    @Slot()
    def removeFolder(self):
        """
        When remove button is clicked, record from folderList and media library is removed.
        """
        index = self.folderList.currentRow()
        self.folderList.takeItem(index)
        del self.mediaFolders[index]

    def accept(self):
        try:
            with open(self.mediaLibFile, 'w') as mediaFile:
                json.dump(self.mediaFolders, mediaFile)
        except IOError:
            logger.exception("Error when writing media file data to disk")
            QMessageBox(QMessageBox.Critical, "IO Error", "Error when writing media file data to disk!").exec_()
        except Exception:
            logger.exception("Error when dumping mediaFolders to media file")
            QMessageBox(QMessageBox.Critical, "Parsing error", "Error when parsing media file data from json!").exec_()

        super(LibraryDialog, self).accept()