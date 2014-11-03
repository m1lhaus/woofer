# -*- coding: utf-8 -*-


import logging
import json
import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from forms.library_form import Ui_libraryDialog

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class LibraryDialog(QDialog, Ui_libraryDialog):
    """
    Dialog where user can edit folders id media library:
    - add new folder
    - remove folder
    """

    def __init__(self, mediaLibFile, parent=None):
        """
        @param mediaLibFile: path to media library file
        @param parent: parent dialog
        """
        super(LibraryDialog, self).__init__(parent)
        self.mediaLibFile = mediaLibFile
        self.mediaFolders = []
        self.anyChanges = False

        self.setupUi(self)
        self.setupSignals()

        # loads folders from medialib
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
            folder = os.path.normpath(folder)       # trim all redundant slashes, etc.
            folder_item = QListWidgetItem(folder)

            if not os.path.isdir(folder):
                folder_item.setForeground(QBrush(Qt.red))
                folder_item.setToolTip("Folder does not exist!")

            self.folderList.addItem(folder_item)

    def setupSignals(self):
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.addBtn.clicked.connect(self.addFolder)
        self.removeBtn.clicked.connect(self.removeFolder)

    @pyqtSlot()
    def addFolder(self):
        """
        When 'Add' button clicked, system folder dialog is opened and new directory is added
        """
        logger.debug("Opening system file dialog.")
        homeFolder = QStandardPaths.standardLocations(QStandardPaths.HomeLocation)[0]
        newFolder = QFileDialog.getExistingDirectory(self, directory=homeFolder)

        if newFolder:
            logger.debug("Selected directory: %s", newFolder)
            newFolder = os.path.normpath(newFolder)
            self.mediaFolders.append(newFolder)
            self.folderList.addItem(newFolder)
            self.anyChanges = True

    @pyqtSlot()
    def removeFolder(self):
        """
        When 'Remove' button is clicked, folder record from folderList and media library is removed.
        """
        index = self.folderList.currentRow()
        # remove folder_item from listWidget and from list
        self.folderList.takeItem(index)
        del self.mediaFolders[index]
        self.anyChanges = True

    def accept(self):
        """
        When 'Save' button is clicked, changes are saved to medialib file.
        """
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