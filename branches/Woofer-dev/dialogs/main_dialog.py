# -*- coding: utf-8 -*-

"""
Main application GUI module
"""

__version__ = "$Id$"

import logging
import sys
import os
import errno
import json

from PySide.QtGui import *
from PySide.QtCore import *

from forms.main_form import Ui_MainWindow
from dialogs.library_dialog import LibraryDialog
from tools.misc import enumm, enum

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)

Sources = enumm(FILES=0, PLAYLISTS=1, RADIO=2)
Errors = enum('WARNING', 'SERIOUS', 'CRITICAL')


class MainApp(QMainWindow, Ui_MainWindow):
    """
    Main application GUI form.
    - setup main window dialog
    - connects signals from dialogs widgets
    """

    errorEncountered = Signal(int, unicode)

    myComputerPathIndex = None

    def __init__(self):
        super(MainApp, self).__init__()
        self.root_path = os.path.dirname(sys.argv[0])
        self.setupUi(self)
        self.setupSignals()
        self.setupFileBrowser()
        # self.setupPlaylistBrowser()
        # self.setupRadioBrowser()

        # display file browser as default
        self.changeSource(Sources.FILES)

        logger.debug("Main application dialog initialized")

    def setupUi(self, parent):
        super(MainApp, self).setupUi(parent)

        self.sourceBrowser.expandAll()
        self.sourceBrowser.setColumnHidden(1, True)

    def setupSignals(self):
        self.sourceBrowser.itemSelectionChanged.connect(self.changeSource)
        self.folderCombo.currentIndexChanged.connect(self.changeFileBrowserRoot)
        self.libraryBtn.clicked.connect(self.openLibraryDialog)

        self.errorEncountered.connect(self.displayError)

    def setupFileBrowser(self):
        """
        Initializes file browser model
        """
        # init data folder
        dataFolder = os.path.join(self.root_path, 'data')
        try:
            os.makedirs(dataFolder)
        except OSError, exception:
            if exception.errno != errno.EEXIST:
                logger.exception("Unable to create media library folder on path: %s", dataFolder)
                # TODO emit error
                raise
        else:
            logger.debug("Media library folder created")

        # init media library file
        self.mediaLibFile = os.path.join(dataFolder, 'medialib.json')
        mediaFolders = None
        try:
            with open(self.mediaLibFile, 'r') as mediaFile:
                logger.debug("Media file opened.")
                mediaFolders = json.load(mediaFile)
        except IOError, exception:
            if exception.errno != errno.ENOENT:
                logger.exception("Error when reading medialib file.")
                # TODO emit error
                raise

            # create file
            with open(self.mediaLibFile, 'w') as f:
                logger.debug("Media file created")
                f.write('[]')
        except Exception:
            logger.exception("Unable to load mediaFolders from medialib file.")

        # init fileSystem model
        self.fileBrowserModel = QFileSystemModel(self)
        self.fileBrowserModel.setRootPath(QDir.rootPath())
        self.fileBrowserModel.setResolveSymlinks(True)

        # add folder from medialib to folderCombobox
        self.folderCombo.addItem(self.fileBrowserModel.myComputer(Qt.DisplayRole))
        if mediaFolders:
            for folder in mediaFolders:
                folder = os.path.normpath(folder)
                if os.path.isdir(folder):
                    self.folderCombo.addItem(folder)
                else:
                    logger.debug("Path '%s' from medialib doesn't exist.", folder)

    def loadSettings(self):
        pass

    def setupPlaylistBrowser(self):
        pass

    def setupRadioBrowser(self):
        pass

    @Slot()
    def changeSource(self, source_id=None):
        """
        When item in sourceBrowser is clicked, source is changed.
        Source could be changed manually by providing source_id.
        @param source_id: enum Source
        @type source_id: int
        """
        if source_id is None:
            table_item = self.sourceBrowser.currentItem()
            try:
                source_id = int(table_item.text(1))
            except ValueError:
                return

        if source_id == Sources.FILES:
            self.sourceItemsBrowser.setModel(self.fileBrowserModel)
            # self.sourceItemsBrowser.setRootIndex(self.fileBrowserModel.index(self.mediaLibPath))
            for i in range(1, self.fileBrowserModel.columnCount()):
                self.sourceItemsBrowser.setColumnHidden(i, True)
            self.browser_type = Sources.FILES

            # remember my_computer root index
            if self.myComputerPathIndex is None:
                self.myComputerPathIndex = self.sourceItemsBrowser.rootIndex()

        elif source_id == Sources.PLAYLISTS:
            # TODO implement
            self.browser_type = Sources.PLAYLISTS

        elif source_id == Sources.RADIO:
            # TODO implement
            self.browser_type = Sources.RADIO

    @Slot(int)
    def changeFileBrowserRoot(self, index):
        """
        When new folder from folderCombo is selected, update folder browser (sourceItemsBrowser)
        @type index: int
        """
        newMediaFolder = self.folderCombo.currentText()

        if newMediaFolder == self.fileBrowserModel.myComputer(Qt.DisplayRole):
            if self.myComputerPathIndex is not None:
                self.sourceItemsBrowser.setRootIndex(self.myComputerPathIndex)
        else:
            folderIndex = self.fileBrowserModel.index(newMediaFolder)
            if folderIndex.row() != -1 and folderIndex.column() != -1:
                self.sourceItemsBrowser.setRootIndex(folderIndex)
            else:
                logger.error("Media path from folderCombo could not be found in fileSystemModel!")
                # TODO emit error

    @Slot()
    def openLibraryDialog(self):
        libraryDialog = LibraryDialog(self.mediaLibFile, self)
        libraryDialog.exec_()


    @Slot(int, unicode)
    def displayError(self, er_type, text):
        pass
        # TODO implement





