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

import logging
import json
import os

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from forms.library_form import Ui_libraryDialog
from components.translator import tr

logger = logging.getLogger(__name__)


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
                assert isinstance(self.mediaFolders, list)
        except IOError:
            logger.exception(u"Error when reading media file data from disk")
            QMessageBox(QMessageBox.Critical, tr['ERROR_READ_MEDIALIB_FILE'], u"").exec_()
        except Exception:
            logger.exception(u"Error when parsing media file data from json")
            QMessageBox(QMessageBox.Critical, tr['ERROR_PARSE_MEDIALIB_FILE'], u"").exec_()

        # fill QListWidget with folders
        for folder in self.mediaFolders:
            folder = os.path.normpath(folder)       # trim all redundant slashes, etc.
            folder_item = QListWidgetItem(folder)

            if not os.path.isdir(folder):
                folder_item.setForeground(QBrush(Qt.red))
                folder_item.setToolTip(tr['FOLDER_NOT_EXIST'])

            self.folderList.addItem(folder_item)

    def setupSignals(self):
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.addBtn.clicked.connect(self.addFolder)
        self.removeBtn.clicked.connect(self.removeFolder)
        self.folderList.itemDoubleClicked.connect(self.editFolder)

    @pyqtSlot()
    def addFolder(self, edit=False):
        """
        When 'Add' button clicked, system folder dialog is opened and new directory is added
        """
        logger.debug(u"Opening system file dialog for adding.")

        settings = QSettings()
        start_folder = settings.value(u"gui/LibraryDialog/lastVisited", None)

        # use last visited directory or home directory if last used does not exist
        if not start_folder or not os.path.isdir(start_folder):
            start_folder = QDesktopServices.storageLocation(QDesktopServices.HomeLocation)

        new_folder = QFileDialog.getExistingDirectory(directory=start_folder)
        if new_folder:
            logger.debug(u"Selected directory: %s", new_folder)
            new_folder = os.path.normpath(new_folder)
            self.mediaFolders.append(new_folder)
            self.folderList.addItem(new_folder)
            self.anyChanges = True

            # save last visited directory
            settings.setValue(u"gui/LibraryDialog/lastVisited", os.path.dirname(new_folder))

    @pyqtSlot('QListWidgetItem')
    def editFolder(self, item):
        """
        When item (folder) is doubleclicked, system folder dialog is opened and clicked  directory is edited
        @type item: QListWidgetItem
        """
        logger.debug(u"Opening system file dialog for editing.")

        old_folder = os.path.normpath(item.text())
        new_folder = QFileDialog.getExistingDirectory(directory=old_folder)

        if new_folder:
            logger.debug(u"Selected directory: %s", new_folder)
            new_folder = os.path.normpath(new_folder)
            self.mediaFolders[self.mediaFolders.index(old_folder)] = new_folder
            item.setText(new_folder)
            self.anyChanges = True

            # save last visited directory
            settings = QSettings()
            settings.setValue(u"gui/LibraryDialog/lastVisited", os.path.dirname(new_folder))

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
            QMessageBox(QMessageBox.Critical, tr['ERROR_WRITE_MEADIALIB_FILE'], u"").exec_()
        except Exception:
            logger.exception(u"Error when dumping mediaFolders to media file")
            QMessageBox(QMessageBox.Critical, tr['ERROR_PARSE_MEDIALIB_FILE'], u"").exec_()

        super(LibraryDialog, self).accept()