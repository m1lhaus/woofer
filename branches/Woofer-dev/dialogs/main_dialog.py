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
import time

from PySide.QtGui import *
from PySide.QtCore import *

from forms.main_form import Ui_MainWindow
from dialogs.library_dialog import LibraryDialog
from components import disk
from components import media
from tools import misc

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)

Sources = misc.enum(FILES=0, PLAYLISTS=1, RADIO=2)
Message = misc.enum('WARNING', 'ERROR', 'CRITICAL')
FileExt = ['*.aac', '*.flac', '*.mp3', '*.ogg', '*.wav', '*.wma']
FileExt_ = ('.aac', '.flac', '.mp3', '.ogg', '.wav', '.wma')

StdErrRedirector = misc.RedirectDescriptor()
StdErrRedirector.redirect_C_stderr_null()


class MainApp(QMainWindow, Ui_MainWindow):
    """
    Main application GUI form.
    - setup main window dialog
    - connects signals from dialogs widgets
    """

    errorEncountered = Signal(int, unicode, unicode)
    scanFiles = Signal(unicode)

    myComputerPathIndex = None

    def __init__(self):
        super(MainApp, self).__init__()
        self.appRootPath = os.path.dirname(sys.argv[0])
        self.appDataPath = os.path.join(self.appRootPath, 'data')
        self.mediaLibFile = os.path.join(self.appDataPath, 'medialib.json')
        self.stBarMsgIcon = QLabel(self)
        self.stBarMsgText = QLabel(self)
        self.progressBar = QProgressBar(self)
        self.progressLabel = QLabel(self)
        self.appendToPlaylist = False
        self.setupUi(self)
        self.checkPaths()
        self.setupFileBrowser(initModel=True)
        self.setupPlayer()
        self.setupScanner()
        self.setupGUISignals()

        self.changeSource(Sources.FILES)        # display file browser as default
        logger.debug("Main application dialog initialized")

    def setupUi(self, parent):
        super(MainApp, self).setupUi(parent)
        self.sourceBrowser.expandAll()
        self.sourceBrowser.setColumnHidden(1, True)     # there is hidden id value in second column
        self.playlist.setColumnHidden(self.playlist.columnCount() - 1, True)
        header = self.playlist.horizontalHeader()
        header.setResizeMode(0, QHeaderView.Stretch)
        header.setResizeMode(1, QHeaderView.Fixed)
        header.setResizeMode(2, QHeaderView.ResizeToContents)
        self.playlist.setColumnWidth(1, 100)
        self.statusbar.setStyleSheet("QStatusBar::item {border: none;}")    # remove statusbar separator
        self.sourceItemsBrowser.setContextMenuPolicy(Qt.CustomContextMenu)

    def setupGUISignals(self):
        self.sourceBrowser.itemSelectionChanged.connect(self.changeSource)
        self.folderCombo.currentIndexChanged.connect(self.changeFileBrowserRoot)
        self.libraryBtn.clicked.connect(self.openLibraryDialog)
        self.sourceItemsBrowser.customContextMenuRequested.connect(self.sourceItemsBrowserContextMenu)

        self.errorEncountered.connect(self.displayErrorMsg)

        self.playPauseBtn.clicked.connect(self.mediaPlayer.playPause)
        self.stopBtn.clicked.connect(self.mediaPlayer.stop)
        self.nextBtn.clicked.connect(self.mediaPlayer.next)
        self.previousBtn.clicked.connect(self.mediaPlayer.prev)

    def setupPlayer(self):
        self.mediaPlayer = media.MediaPlayer()
        # self.mediaPlayerThread = QThread(self)
        # self.mediaPlayer.moveToThread(self.mediaPlayerThread)

        self.mediaPlayer.mediaAdded.connect(self.addToPlaylist)
        self.mediaPlayer.playing.connect(self.playing)
        self.mediaPlayer.paused.connect(self.paused)
        self.mediaPlayer.stopped.connect(self.stopped)
        self.mediaPlayer.timeChanged.connect(self.displayTime)

        # self.mediaPlayerThread.start()

    # def printTime(self):
    #     print (time.time() - self.t0) * 1000, "ms"

    def setupScanner(self):
        # asynchronous scanner
        self.scanner = disk.RecursiveBrowser(nameFilter=FileExt_, followSym=False)
        self.scannerThread = QThread(self)
        self.scanner.moveToThread(self.scannerThread)
        # asynchronous parser
        self.parser = media.MediaParser()
        self.parserThread = QThread(self)
        self.parser.moveToThread(self.parserThread)

        self.scanFiles.connect(self.scanner.scanFiles)
        # self.parser.finished.connect(self.printTime)    # FIXME debug only
        self.parser.finished.connect(self.clearProgress)
        # self.parser.finished.connect(self.scanner.finish)
        self.parser.parsedData.connect(self.mediaPlayer.addMedia)
        self.scanner.parseData.connect(self.parser.parseMedia)

        self.scannerThread.start()
        self.parserThread.start()

    def checkPaths(self):
        """
        Creates data folder and media library file if doesn't exist!
        """
        # check data folder
        try:
            os.makedirs(self.appDataPath)
        except OSError, exception:
            if exception.errno != errno.EEXIST:
                logger.exception("Unable to create data folder on path: %s", self.appDataPath)
                self.errorEncountered.emit(Message.CRITICAL, "Unable to create data folder.",
                                                             "Error number: %s\n"
                                                             "%s" % (exception.errno, exception.strerror))
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
                except IOError:
                    logger.exception("Error when creating new media library file.")
                    self.errorEncountered.emit(Message.CRITICAL,
                                               "Unable to create medialib file and write default data.",
                                               "Error number: %s\n"
                                               "%s" % (exception.errno, exception.strerror))
                    raise
                else:
                    logger.debug("Media file has been created and initialized.")
            else:
                logger.exception("Error when reading medialib file.")
                self.errorEncountered.emit(Message.CRITICAL, "Unable to open and read medialib file.",
                                                             "Error number: %s\n"
                                                             "%s" % (exception.errno, exception.strerror))
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
        except IOError, exception:
            logger.exception("Error when reading medialib file.")
            self.errorEncountered.emit(Message.CRITICAL, "Unable to open and read medialib file.",
                                                         "Error number: %s\n"
                                                         "%s" % (exception.errno, exception.strerror))
            raise
        except ValueError, exception:
            logger.exception("Unable to load and parse data from JSON file.")
            self.errorEncountered.emit(Message.CRITICAL, "Unable to load and parse data from medialib file.",
                                                         "Description: %s" % exception.message)
            raise

        if initModel:
            # init fileSystem model
            self.fileBrowserModel = QFileSystemModel(self)
            self.fileBrowserModel.setRootPath(QDir.rootPath())
            self.fileBrowserModel.setResolveSymlinks(True)
            # display only supported files (media files) and hide rest
            self.fileBrowserModel.setNameFilterDisables(False)
            self.fileBrowserModel.setNameFilters(FileExt)

        self.folderCombo.clear()
        self.folderCombo.addItem(self.fileBrowserModel.myComputer(Qt.DisplayRole))      # get default name
        # add only valid folders from medialib to folderCombobox
        for folder in mediaFolders:
            folder = os.path.normpath(folder)       # normalize => remove redundant slashes, etc.
            if os.path.isdir(folder):
                self.folderCombo.addItem(folder)
            else:
                self.errorEncountered.emit(Message.WARNING, "Some folders in media library do not exist.", "")

    def loadSettings(self):
        # TODO implement QSettings
        pass

    def setupPlaylistBrowser(self):
        # TODO future: implement
        pass

    def setupRadioBrowser(self):
        # TODO future: implement
        pass

    @Slot(QPointF)
    def sourceItemsBrowserContextMenu(self, pos):
        """
        SourceItemsBrowser treeView context menu method.
        Method creates context menu depending on source type (files, playlist, radios).
        @type pos: QPointF
        """

        logger.debug("SourceItemBrowser context menu called. Choosing appropriate context menu...")

        if self.sourceType == Sources.FILES:
            self.fileBrowserContextMenu(pos)

        if self.sourceType == Sources.PLAYLISTS:
            logger.debug("Opening playlist browser context menu.")

        if self.sourceType == Sources.RADIO:
            logger.debug("Opening radio browser context menu.")

    def fileBrowserContextMenu(self, pos):
        """
        Context menu for file browser treeView.
        @type pos: QPointF
        """
        fileInfo = self.fileBrowserModel.fileInfo(self.sourceItemsBrowser.indexAt(pos))
        isFile = fileInfo.isFile()
        isDir = fileInfo.isDir()

        # menu setup
        menu = QMenu(self.sourceItemsBrowser)
        playNow = QAction(QIcon(":/new/icons/icons/play-now.png"), "Play now", menu)
        addToPlayList = QAction(QIcon(":/new/icons/icons/play-next.png"), "Add to playlist", menu)
        playAll = QAction(QIcon(":/new/icons/icons/play-now.png"), "Play all", menu)
        removeFromDisk = QAction(QIcon(":/new/icons/icons/delete.png"), "Remove from disk", menu)
        separator = QAction(menu)
        separator.setSeparator(True)

        if isFile:
            menu.addActions([playNow, addToPlayList, separator, removeFromDisk])
        elif isDir:
            menu.addActions([playAll, addToPlayList, separator, removeFromDisk])
            if fileInfo.isRoot():
                removeFromDisk.setEnabled(False)        # disable root removing (i.e. C:\)
        else:
            logger.error("Unknown media type on '%s'", fileInfo.absoluteFilePath())
            return

        logger.debug("Opening file browser context menu.")
        choice = menu.exec_(self.sourceItemsBrowser.viewport().mapToGlobal(pos))

        # self.t0 = time.time()

        # PLAY NOW
        if choice is playNow:
            self.appendToPlaylist = False
            targetPath = fileInfo.absoluteFilePath()
            # asynchronously recursively search for media files
            self.scanFiles.emit(targetPath)
            self.displayProgress(u"Searching...")

        # PLAY ALL
        elif choice is playAll:
            self.appendToPlaylist = False
            targetPath = fileInfo.absoluteFilePath()
            # asynchronously recursively search for media files
            self.scanFiles.emit(targetPath)
            self.displayProgress(u"Searching...")

        # ADD TO PLAYLIST
        elif choice is addToPlayList:
            self.appendToPlaylist = True
            targetPath = fileInfo.absoluteFilePath()
            # asynchronously recursively search for media files
            self.scanFiles.emit(targetPath)
            self.displayProgress(u"Searching...")

        # REMOVE FROM DISK
        elif choice is removeFromDisk:
            path = fileInfo.absoluteFilePath()
            logger.debug("Moving path '%s' to Trash", path)
            try:
                misc.moveToTrash(path)
            except OSError, exception:
                self.errorEncountered.emit(Message.ERROR, "Unable to move path to Trash path '%s'!" % path,
                                                          "Details: %s" % exception.message)

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
            # TODO future: implement playlists

        elif source_id == Sources.RADIO:
            self.sourceType = Sources.RADIO
            logger.debug("Radio source has been selected.")
            # TODO future: implement radios

    @Slot(int)
    def changeFileBrowserRoot(self, index):
        """
        When new folder from folderCombo is selected, update folder browser (sourceItemsBrowser)
        @type index: int
        """
        if index == -1:
            return          # ignore on reset

        newMediaFolder = self.folderCombo.currentText()

        if newMediaFolder == self.fileBrowserModel.myComputer(Qt.DisplayRole):
            # display MyComputer folder (root on Linux)
            if self.myComputerPathIndex is not None:
                self.sourceItemsBrowser.setRootIndex(self.myComputerPathIndex)
                self.fileBrowserModel.setRootPath(QDir.rootPath())
        else:
            # if valid, display given folder as root
            folderIndex = self.fileBrowserModel.index(newMediaFolder)
            if folderIndex.row() != -1 and folderIndex.column() != -1:
                self.sourceItemsBrowser.setRootIndex(folderIndex)
                self.fileBrowserModel.setRootPath(newMediaFolder)
            else:
                logger.error("Media path from folderCombo could not be found in fileSystemModel!")
                self.errorEncountered.emit(Message.ERROR, "Media folder '%s' could not be found!" % newMediaFolder, "")
                self.folderCombo.removeItem(self.folderCombo.currentIndex())

    @Slot()
    def openLibraryDialog(self):
        """
        When library button is clicked, open library editor dialog.
        When dialog is closed, refresh media folders combobox.
        """
        libraryDialog = LibraryDialog(self.mediaLibFile, self)
        libraryDialog.finished.connect(self.setupFileBrowser)
        libraryDialog.exec_()

    @Slot(list)
    def addToPlaylist(self, sources):
        """
        Sets and adds media files to playlist.
        @param sources: list of (path, duration)
        @type sources: list of (unicode, int)
        """
        n = len(sources)
        logger.debug("Adding '%s' sources to current playlist.", n)

        if self.appendToPlaylist:
            last = self.playlist.rowCount()
        else:
            self.appendToPlaylist = True        # next data needs to be appended to current
            last = 0

        self.playlist.setRowCount(last + n)
        i = 0
        for path, duration in sources:
            titleItem = QTableWidgetItem(os.path.basename(path))
            durationItem = QTableWidgetItem(QTime().addMSecs(duration).toString("hh:mm:ss"))
            pathItem = QTableWidgetItem(path)
            self.playlist.setItem(i + last, 0, titleItem)
            self.playlist.setItem(i + last, 2, durationItem)
            self.playlist.setItem(i + last, 3, pathItem)
            i += 1

    def closeEvent(self, event):
        # self.mediaPlayerThread.quit()
        self.scannerThread.quit()
        self.parserThread.quit()

        StdErrRedirector.redirect_C_stderr_back()
        event.accept()

    @Slot(int, unicode, unicode)
    def displayErrorMsg(self, er_type, text, details=u""):
        """
        Called to display warnings and errors.
        @param er_type: error type (Message enum)
        @param text: main text
        @param details: description
        """
        if er_type == Message.WARNING:
            icon = QPixmap(":/new/icons/icons/warning.png").scaled(14, 14, mode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.statusbar.addWidget(self.stBarMsgIcon)
            self.statusbar.addWidget(self.stBarMsgText)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(5000, self.clearErrorMsg)
        elif er_type == Message.ERROR:
            icon = QPixmap(":/new/icons/icons/error.png").scaled(14, 14, mode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.statusbar.addWidget(self.stBarMsgIcon)
            self.statusbar.addWidget(self.stBarMsgText)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(10000, self.clearErrorMsg)
            QApplication.beep()
        elif er_type == Message.CRITICAL:
            msgBox = QMessageBox(self)
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle("Critical error")
            msgBox.setText(text)
            msgBox.setInformativeText(details)
            msgBox.exec_()

    @Slot()
    def clearErrorMsg(self):
        """
        Called to clear statusbar after displaying error message (widgets).
        """
        self.statusbar.removeWidget(self.stBarMsgIcon)
        self.statusbar.removeWidget(self.stBarMsgText)

    def displayProgress(self, description, minimum=0, maximum=0):
        """
        Called to show progress bar and label in statusbar to inform user when some action on background is running.
        When minimum and maximum attributes are not set (zero), busy progress bar is shown.
        @type description: unicode
        @type minimum: int
        @type maximum: int
        """
        self.progressBar.setMaximumSize(200, self.progressBar.minimumSizeHint().height())
        self.progressBar.setMinimum(minimum)
        self.progressBar.setMaximum(maximum)
        self.progressLabel.setText(description)

        self.statusbar.addPermanentWidget(self.progressLabel)
        self.statusbar.addPermanentWidget(self.progressBar)
        # show widgets if not visible <= removeWidget() hides widgets
        self.progressBar.show()
        self.progressLabel.show()

    def updateProgress(self, value, description=None, minimum=None, maximum=None):
        """
        Called to update value on progressBar or label when showing progress
        @type value: int
        @type description: unicode
        @type minimum: int
        @type maximum: int
        """
        self.progressBar.setValue(value)

        if minimum is not None:
            self.progressBar.setMinimum(minimum)
        if maximum is not None:
            self.progressBar.setMaximum(maximum)
        if description is not None:
            self.progressLabel.setText(description)

    @Slot()
    def clearProgress(self):
        """
        Hides progress bar and label from statusbar when showing progress
        """
        self.statusbar.removeWidget(self.progressLabel)
        self.statusbar.removeWidget(self.progressBar)

    @Slot()
    def playing(self):
        icon = QIcon()
        icon.addPixmap(QPixmap(":/new/icons/icons/media-pause.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)

    @Slot()
    def paused(self):
        icon = QIcon()
        icon.addPixmap(QPixmap(":/new/icons/icons/media-play.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)

    @Slot()
    def stopped(self):
        self.paused()
        self.timeLbl.setText("00:00:00")

    @Slot(int)
    def displayTime(self, value):
        self.timeLbl.setText(QTime().addMSecs(value).toString("hh:mm:ss"))








