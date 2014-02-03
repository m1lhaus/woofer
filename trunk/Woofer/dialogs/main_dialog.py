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
FileExtensions = ['*.aac', '*.flac', '*.mp3', '*.ogg', '*.wav', '*.wma']


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
        self.appRootPath = os.path.dirname(sys.argv[0])
        self.appDataPath = os.path.join(self.appRootPath, 'data')
        self.mediaLibFile = os.path.join(self.appDataPath, 'medialib.json')
        self.setupUi(self)
        self.setupSignals()

        self.checkPaths()
        self.setupFileBrowser(initModel=True)
        # self.setupPlaylistBrowser()
        # self.setupRadioBrowser()

        self.changeSource(Sources.FILES)        # display file browser as default
        logger.debug("Main application dialog initialized")

    def setupUi(self, parent):
        super(MainApp, self).setupUi(parent)
        self.sourceBrowser.expandAll()
        self.sourceBrowser.setColumnHidden(1, True)     # there is hidden id value in second column
        # self.sourceItemsBrowser.setContextMenuPolicy(Qt.CustomContextMenu)

    def setupSignals(self):
        self.sourceBrowser.itemSelectionChanged.connect(self.changeSource)
        self.folderCombo.currentIndexChanged.connect(self.changeFileBrowserRoot)
        self.libraryBtn.clicked.connect(self.openLibraryDialog)
        self.sourceItemsBrowser.customContextMenuRequested.connect(self.sourceItemsBrowserContextMenu)

        self.errorEncountered.connect(self.displayError)

    def checkPaths(self):
        """
        Creates data folder and media library file if doesn't exist!
        """
        # check data folder
        try:
            os.makedirs(self.appDataPath)
        except OSError, exception:
            if exception.errno != errno.EEXIST:
                logger.exception("Unable to create media library folder on path: %s", self.appDataPath)
                # TODO display error
                raise
        else:
            logger.debug("Data folder didn't exist and has been created.")

        # check medialib file
        try:
            with open(self.mediaLibFile, 'r') as f:
                pass
        except IOError, exception:
            #  file doesn't exist => create and init file
            if exception.errno == errno.ENOENT:
                try:
                    with open(self.mediaLibFile, 'w') as f:
                        f.write('[]')
                    logger.debug("Media file has been created and initialized.")
                except IOError:
                    logger.exception("Error when creating new media library file.")
                    # TODO display error
                    raise
            else:
                logger.exception("Error when reading medialib file.")
                # TODO display error
                raise

    @Slot(int)
    def setupFileBrowser(self, rcode=None, initModel=False):
        """
        Re-initialize file model for file browser treeView and setup mediaLib folder combobox .
        @param rcode: return code from library dialog (ignore it)
        @param initModel: if true, fileSystemModel is re-initialized
        """
        logger.debug("Opening media folder and reading data.")
        try:
            with open(self.mediaLibFile, 'r') as mediaFile:
                mediaFolders = json.load(mediaFile)
        except IOError:
            logger.exception("Error when reading medialib file.")
            # TODO display error
            raise
        except Exception:
            logger.exception("Unable to load mediaFolders from medialib file.")
            # TODO display error
            raise

        if initModel:
            # init fileSystem model
            self.fileBrowserModel = QFileSystemModel(self)
            self.fileBrowserModel.setRootPath(QDir.rootPath())
            self.fileBrowserModel.setResolveSymlinks(True)
            # display only supported files (media files) and hide rest
            self.fileBrowserModel.setNameFilterDisables(False)
            self.fileBrowserModel.setNameFilters(FileExtensions)

        self.folderCombo.clear()
        self.folderCombo.addItem(self.fileBrowserModel.myComputer(Qt.DisplayRole))      # get default name
        # add only valid folders from medialib to folderCombobox
        for folder in mediaFolders:
            folder = os.path.normpath(folder)       # normalize => remove redundant slashes, etc.
            if os.path.isdir(folder):
                self.folderCombo.addItem(folder)
            else:
                logger.warning("Path '%s' from medialib doesn't exist.", folder)

    def loadSettings(self):
        pass

    def setupPlaylistBrowser(self):
        pass

    def setupRadioBrowser(self):
        pass

    @Slot(QPointF)
    def sourceItemsBrowserContextMenu(self, pos):
        pass
        # menu = QMenu(self.sourceItemsBrowser)
        # playNow = QAction(QIcon(":/new/icons/icons/play-now.png"), "Play now", menu)
        # addToPlayList = QAction(QIcon(":/new/icons/icons/play-next.png"), "Add to playlist", menu)
        # separator = QAction(menu)
        # separator.setSeparator(True)
        # removeFromDisk = QAction(QIcon(":/new/icons/icons/delete.png"), "Remove from disk", menu)
        #
        #
        # if self.sourceType == Sources.FILES:
        #     logger.debug("Opening file browser context menu.")
        #     menu.addActions([playNow, addToPlayList, separator, removeFromDisk])
        # if self.sourceType == Sources.PLAYLISTS:
        #     logger.debug("Opening playlist browser context menu.")
        # if self.sourceType == Sources.RADIO:
        #     logger.debug("Opening radio browser context menu.")
        #
        # menu.exec_(self.sourceItemsBrowser.viewport().mapToGlobal(pos))

    @Slot()
    def changeSource(self, source_id=None):
        """
        When item in sourceBrowser is clicked, source is changed.
        Source could be changed manually by providing source_id.
        @param source_id: enum Source
        @type source_id: int
        """
        logger.debug("Change source called.")

        # get only valid source id from sourceBrowser
        if source_id is None:
            table_item = self.sourceBrowser.currentItem()
            try:
                source_id = int(table_item.text(1))         # parent item has no id
            except ValueError:
                return

        if source_id == Sources.FILES:
            self.sourceType = Sources.FILES
            self.sourceItemsBrowser.setModel(self.fileBrowserModel)

            # hide unwanted columns
            for i in range(1, self.fileBrowserModel.columnCount()):
                self.sourceItemsBrowser.setColumnHidden(i, True)

            # remember my_computer root index for the first time
            if self.myComputerPathIndex is None:
                self.myComputerPathIndex = self.sourceItemsBrowser.rootIndex()

            logger.debug("File source has been selected.")

        elif source_id == Sources.PLAYLISTS:
            self.sourceType = Sources.PLAYLISTS
            logger.debug("Playlist source has been selected.")
            # TODO implement playlists

        elif source_id == Sources.RADIO:
            self.sourceType = Sources.RADIO
            logger.debug("Radio source has been selected.")
            # TODO implement radios

    @Slot(int)
    def changeFileBrowserRoot(self, index):
        """
        When new folder from folderCombo is selected, update folder browser (sourceItemsBrowser)
        @type index: int
        """
        # ignore on reset
        if index == -1:
            return

        newMediaFolder = self.folderCombo.currentText()

        if newMediaFolder == self.fileBrowserModel.myComputer(Qt.DisplayRole):
            if self.myComputerPathIndex is not None:
                self.sourceItemsBrowser.setRootIndex(self.myComputerPathIndex)
                self.fileBrowserModel.setRootPath(QDir.rootPath())
        else:
            folderIndex = self.fileBrowserModel.index(newMediaFolder)
            # if valid, set given folders as root
            if folderIndex.row() != -1 and folderIndex.column() != -1:
                self.sourceItemsBrowser.setRootIndex(folderIndex)
                self.fileBrowserModel.setRootPath(newMediaFolder)
            else:
                logger.error("Media path from folderCombo could not be found in fileSystemModel!")
                # TODO emit error

    @Slot()
    def openLibraryDialog(self):
        """
        When library button is clicked, open library editor dialog.
        When dialog is closed, refresh media folders combobox.
        """
        libraryDialog = LibraryDialog(self.mediaLibFile, self)
        libraryDialog.finished.connect(self.setupFileBrowser)
        libraryDialog.exec_()

    @Slot(int, unicode)
    def displayError(self, er_type, text):
        pass
        # TODO implement





