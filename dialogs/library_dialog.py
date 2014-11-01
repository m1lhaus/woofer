# -*- coding: utf-8 -*-

__version__ = "$Id: library_dialog.py 89 2014-09-27 18:24:40Z m1lhaus $"

import logging
import json
import os

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from forms.library_form import Ui_libraryDialog

logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)


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
        self.anyChanges = False

        self.setupUi(self)
        self.setupSignals()

        # loads folders from medialib
        try:
            with open(self.mediaLibFile, 'r') as mediaFile:
                self.mediaFolders = json.load(mediaFile)
        except IOError:
            logger.exception(u"Error when reading media file data from disk")
            QMessageBox(QMessageBox.Critical, u"IO Error", u"Error when reading media file data from disk!").exec_()
        except Exception:
            logger.exception(u"Error when parsing media file data from json")
            QMessageBox(QMessageBox.Critical, u"Parsing error", u"Error when parsing media file data from json!").exec_()

        # fill QListWidget with folders
        for folder in self.mediaFolders:
            folder = os.path.normpath(folder)       # trim all redundant slashes, etc.
            folder_item = QListWidgetItem(folder)

            if not os.path.isdir(folder):
                folder_item.setForeground(QBrush(Qt.red))
                folder_item.setToolTip(u"Folder does not exist!")

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
        logger.debug(u"Opening system file dialog.")
        homeFolder = QDesktopServices.storageLocation(QDesktopServices.HomeLocation)
        newFolder = QFileDialog.getExistingDirectory(self, directory=homeFolder)

        if newFolder:
            logger.debug(u"Selected directory: %s", newFolder)
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
            logger.exception(u"Error when writing media file data to disk")
            QMessageBox(QMessageBox.Critical, u"IO Error", u"Error when writing media file data to disk!").exec_()
        except Exception:
            logger.exception(u"Error when dumping mediaFolders to media file")
            QMessageBox(QMessageBox.Critical, u"Parsing error", u"Error when parsing media file data from json!").exec_()

        super(LibraryDialog, self).accept()