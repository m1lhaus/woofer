# -*- coding: utf-8 -*-

"""
Main application GUI module.
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

from forms.main_form import MainForm
from dialogs.library_dialog import LibraryDialog
from components import disk
from components import media
from tools import misc

logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)

Sources = misc.enum(FILES=0, PLAYLISTS=1, RADIO=2)
Message = misc.enum('WARNING', 'ERROR', 'CRITICAL')
FileExt = ['*.aac', '*.flac', '*.mp3', '*.ogg', '*.wav', '*.wma']
FileExt_ = ('.aac', '.flac', '.mp3', '.ogg', '.wav', '.wma')

# StdErrRedirector = misc.RedirectDescriptor()
# StdErrRedirector.redirect_C_stderr_null()


class MainApp(QMainWindow, MainForm):
    """
    Main application GUI form.
    - setup main window dialog
    - connects signals from dialogs widgets
    """

    errorEncountered = Signal(int, unicode, unicode)        # (Message.CRITICAL, main_text, description)
    scanFiles = Signal(unicode)

    myComputerPathIndex = None

    queuedLoad = Signal()

    WARNING_MSG_DELAY = 5000
    ERROR_MSG_DELAY = 10000

    def __init__(self):
        super(MainApp, self).__init__()
        self.appRootPath = os.path.dirname(sys.argv[0])
        self.appDataPath = os.path.join(self.appRootPath, u'data')
        self.mediaLibFile = os.path.join(self.appDataPath, u'medialib.json')

        self.setupUi(self)
        self.checkPaths()
        self.setupFileBrowser(initModel=True)
        self.setupPlayer()
        self.setupScanner()
        self.setupActions()
        self.setupGUISignals()

        self.loadSettings()

        QTimer.singleShot(0, self.loadSettingsQueued)           # run method after dialog is opened
        logger.debug(u"Main application dialog initialized")

    def setupUi(self, parent):
        super(MainApp, self).setupUi(parent)
        self.sourceBrowser.expandAll()
        self.timeLbl.setFixedSize(self.timeLbl.minimumSizeHint())       # prevent 1px oscillation

    def setupGUISignals(self):
        self.sourceBrowser.itemSelectionChanged.connect(self.changeSource)
        self.folderCombo.currentIndexChanged.connect(self.changeFileBrowserRoot)
        self.libraryBtn.clicked.connect(self.openLibraryDialog)
        self.mainTreeBrowser.customContextMenuRequested.connect(self.sourceItemsBrowserContextMenu)
        self.playlist.customContextMenuRequested.connect(self.playlistContextMenu)
        self.playlist.cellDoubleClicked.connect(self.playNow)
        self.progressCancelBtn.clicked.connect(self.cancelAdding)

        self.errorEncountered.connect(self.displayErrorMsg)

        self.playPauseBtn.clicked.connect(self.mediaPlayer.playPause)
        self.stopBtn.clicked.connect(self.mediaPlayer.stop)
        self.nextBtn.clicked.connect(self.mediaPlayer.next)
        self.previousBtn.clicked.connect(self.mediaPlayer.prev)
        self.seekerSlider.valueChanged.connect(self.mediaPlayer.setPosition)
        self.volumeSlider.valueChanged.connect(self.mediaPlayer.setVolume)
        self.shuffleBtn.toggled.connect(self.toggleShuffle)
        self.repeatBtn.toggled.connect(self.toggleRepeat)

        self.playlist.enterShortcut.activated.connect(self.playNow)
        self.playlist.delShortcut.activated.connect(self.remFromPlaylist)
        self.playlist.shiftDelShortcut.activated.connect(self.remFromDisk)

    def setupActions(self):
        pass

    def setupPlayer(self):
        self.mediaPlayer = media.MediaPlayer()

        self.mediaPlayer.mediaAdded.connect(self.addToPlaylist)
        self.mediaPlayer.playing.connect(self.playing)
        self.mediaPlayer.paused.connect(self.paused)
        self.mediaPlayer.stopped.connect(self.stopped)
        self.mediaPlayer.timeChanged.connect(self.syncPlayTime)
        self.mediaPlayer.positionChanged.connect(self.syncSeeker)
        self.mediaPlayer.mediaChanged.connect(self.displayCurrentMedia)

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
        self.parser.finished.connect(self.scanner.finish)
        self.parser.finished.connect(self.mediaPlayer.mediaAddingFinished)
        self.parser.parsed.connect(self.mediaPlayer.addMedia)
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
                logger.exception(u"Unable to create data folder on path: %s", self.appDataPath)
                self.errorEncountered.emit(Message.CRITICAL, u"Unable to create data folder.",
                                                             u"Error number: %s\n"
                                                             u"%s" % (exception.errno, exception.strerror))
                raise
        else:
            logger.debug(u"Data folder didn't exist and has been created.")

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
                    logger.exception(u"Error when creating new media library file.")
                    self.errorEncountered.emit(Message.CRITICAL,
                                               u"Unable to create medialib file and write default data.",
                                               u"Error number: %s\n"
                                               u"%s" % (exception.errno, exception.strerror))
                    raise
                else:
                    logger.debug(u"Media file has been created and initialized.")
            else:
                logger.exception(u"Error when reading medialib file.")
                self.errorEncountered.emit(Message.CRITICAL, u"Unable to open and read medialib file.",
                                                             u"Error number: %s\n"
                                                             u"%s" % (exception.errno, exception.strerror))
                raise

    @Slot(int)
    def setupFileBrowser(self, rcode=None, initModel=False):
        """
        Re-initialize file model for file browser treeView and setup mediaLib folder combobox .
        @param rcode: return code from library dialog (ignore it)
        @param initModel: if true, fileSystemModel is re-initialized
        """
        logger.debug(u"Opening media folder and reading data.")
        try:
            with open(self.mediaLibFile, 'r') as mediaFile:
                mediaFolders = json.load(mediaFile)
        except IOError, exception:
            logger.exception(u"Error when reading medialib file.")
            self.errorEncountered.emit(Message.CRITICAL, u"Unable to open and read medialib file.",
                                                         u"Error number: %s\n"
                                                         u"%s" % (exception.errno, exception.strerror))
            raise
        except ValueError, exception:
            logger.exception(u"Unable to load and parse data from JSON file.")
            self.errorEncountered.emit(Message.CRITICAL, u"Unable to load and parse data from medialib file.",
                                                         u"Description: %s" % exception.message)
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
            # folder = os.path.normpath(folder)       # normalize => remove redundant slashes, etc.
            folder = QDir.cleanPath(folder)       # normalize => remove redundant slashes, etc.
            if os.path.isdir(folder):
                self.folderCombo.addItem(folder)
            else:
                self.errorEncountered.emit(Message.WARNING, u"Some folders in media library do not exist.", u"")

    def loadSettings(self):
        logger.debug(u"Global load settings called. Loading settings...")
        # self.changeSource(Sources.FILES)                    # display file browser as default

    def loadSettingsQueued(self):
        self.changeSource(Sources.FILES)

    def saveSettings(self):
        logger.debug(u"Global save settings called. Saving settings...")
        self.mainTreeBrowser.saveSettings()

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

        logger.debug(u"Browser context menu called. Choosing appropriate context menu...")

        if self.sourceType == Sources.FILES:
            self.fileBrowserContextMenu(pos)

        if self.sourceType == Sources.PLAYLISTS:
            logger.debug(u"Opening playlist browser context menu.")

        if self.sourceType == Sources.RADIO:
            logger.debug(u"Opening radio browser context menu.")

    def fileBrowserContextMenu(self, pos):
        """
        Context menu for file browser treeView.
        @type pos: QPointF
        """
        fileInfo = self.fileBrowserModel.fileInfo(self.mainTreeBrowser.indexAt(pos))
        isFile = fileInfo.isFile()
        isDir = fileInfo.isDir()

        # menu setup
        menu = QMenu(self.mainTreeBrowser)
        playNow = QAction(QIcon(u":/new/icons/icons/play-now.png"), u"Play now", menu)
        addToPlayList = QAction(QIcon(u":/new/icons/icons/play-next.png"), u"Add to playlist", menu)
        playAll = QAction(QIcon(u":/new/icons/icons/play-now.png"), u"Play all", menu)
        removeFromDisk = QAction(QIcon(u":/new/icons/icons/delete.png"), u"Remove from disk", menu)
        separator = QAction(menu)
        separator.setSeparator(True)

        if isFile:
            menu.addActions([playNow, addToPlayList, separator, removeFromDisk])
        elif isDir:
            menu.addActions([playAll, addToPlayList, separator, removeFromDisk])
            if fileInfo.isRoot():
                removeFromDisk.setEnabled(False)        # disable root removing (i.e. C:\)
        else:
            logger.error(u"Unknown media type on '%s'", fileInfo.absoluteFilePath())
            return

        logger.debug(u"Opening file browser context menu.")
        choice = menu.exec_(self.mainTreeBrowser.viewport().mapToGlobal(pos))

        # PLAY NOW
        if choice is playNow:
            self.mediaPlayer.clearMediaList()
            self.mediaPlayer.initMediaAdding(append=False)
            targetPath = fileInfo.absoluteFilePath()
            self.scanFiles.emit(targetPath)                 # asynchronously recursively search for media files
            self.displayProgress(u"Adding...")

        # PLAY ALL
        elif choice is playAll:
            self.mediaPlayer.clearMediaList()
            self.mediaPlayer.initMediaAdding(append=False)
            targetPath = fileInfo.absoluteFilePath()
            self.scanFiles.emit(targetPath)                 # asynchronously recursively search for media files
            self.displayProgress(u"Adding...")

        # ADD TO PLAYLIST
        elif choice is addToPlayList:
            targetPath = fileInfo.absoluteFilePath()
            self.mediaPlayer.initMediaAdding(append=True)
            # asynchronously recursively search for media files
            self.scanFiles.emit(targetPath)
            self.displayProgress(u"Adding...")

        # REMOVE FROM DISK
        elif choice is removeFromDisk:
            path = fileInfo.absoluteFilePath()
            logger.debug(u"Moving path '%s' to Trash", path)
            try:
                misc.moveToTrash(path)
            except OSError, exception:
                self.errorEncountered.emit(Message.ERROR, u"Unable to move path to Trash path '%s'!" % path,
                                                          u"Details: %s" % exception.message)

    @Slot(QPointF)
    def playlistContextMenu(self, pos):
        item = self.playlist.itemAt(pos)
        if not item:
            return

        logger.debug(u"Opening playlist context menu.")
        menu = QMenu(self.playlist)
        playNowAction = QAction(QIcon(u":/new/icons/icons/play-now.png"), u"Play now", menu)
        playNowAction.setShortcut(QKeySequence(Qt.Key_Enter))
        remFromPlaylistAction = QAction(u"Remove from playlist", menu)
        remFromPlaylistAction.setShortcut(QKeySequence(Qt.Key_Delete))
        remFromDiskAction = QAction(QIcon(u":/new/icons/icons/delete.png"), u"Remove from disk", menu)
        remFromDiskAction.setShortcut(QKeySequence(Qt.SHIFT + Qt.Key_Delete))
        separator = QAction(menu)
        separator.setSeparator(True)

        menu.addActions([playNowAction, separator])
        removeMenu = menu.addMenu(u"Remove")
        removeMenu.addActions([remFromPlaylistAction, remFromDiskAction])
        choice = menu.exec_(self.playlist.viewport().mapToGlobal(pos))

        index = self.playlist.row(item)
        if choice is playNowAction:
            self.playNow(index)
        elif choice is remFromPlaylistAction:
            self.remFromPlaylist(index)
        elif choice is remFromDiskAction:
            self.remFromDisk(index)

    @Slot()
    def changeSource(self, source_id=None):
        """
        When item in sourceBrowser is clicked, source is changed.
        Source could be changed manually by providing source_id.
        @param source_id: enum Source
        @type source_id: int
        """
        # get only valid source id from sourceBrowser
        if source_id is None:
            table_item = self.sourceBrowser.currentItem()
            try:
                source_id = int(table_item.text(1))         # parent item has no id
            except ValueError:
                return

        # save TreeBrowser settings if switched to another mode
        oldTreeMode = self.mainTreeBrowser.getMode()
        if oldTreeMode is not None and oldTreeMode != source_id:
            self.mainTreeBrowser.saveSettings()

        if source_id == Sources.FILES:
            self.sourceType = Sources.FILES
            self.mainTreeBrowser.setMode(Sources.FILES)
            self.mainTreeBrowser.setModel(self.fileBrowserModel)

            # hide unwanted columns
            for i in range(1, self.fileBrowserModel.columnCount()):
                self.mainTreeBrowser.setColumnHidden(i, True)

            # remember my_computer root index for the first time
            if self.myComputerPathIndex is None:
                self.myComputerPathIndex = self.mainTreeBrowser.rootIndex()

            self.mainTreeBrowser.restoreSettings()

            logger.debug(u"Browser source has been selected to FILES.")

        elif source_id == Sources.PLAYLISTS:
            self.sourceType = Sources.PLAYLISTS
            self.mainTreeBrowser.setMode(Sources.FILES)
            logger.debug(u"Browser source has been selected to PLAYLISTS.")
            logger.warning(u"PLAYLISTS NOT IMPLEMENTED!")
            # TODO future: implement playlists

        elif source_id == Sources.RADIO:
            self.sourceType = Sources.RADIO
            self.mainTreeBrowser.setMode(Sources.FILES)
            logger.debug(u"Browser source has been selected to RADIOS.")
            logger.warning(u"RADIOS NOT IMPLEMENTED!")
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
                logger.debug(u"Changing file_browser root to 'My Computer/root'.")
                self.mainTreeBrowser.setRootIndex(self.myComputerPathIndex)
                self.fileBrowserModel.setRootPath(QDir.rootPath())
                # self.mainTreeBrowser.currentRootFolder = '/'
        else:
            # if valid, display given folder as root
            folderIndex = self.fileBrowserModel.index(newMediaFolder)
            if folderIndex.row() != -1 and folderIndex.column() != -1:
                logger.debug(u"Changing file_browser root to '%s'.", newMediaFolder)
                self.mainTreeBrowser.setRootIndex(folderIndex)
                self.fileBrowserModel.setRootPath(newMediaFolder)
                # self.mainTreeBrowser.currentRootFolder = newMediaFolder
            else:
                logger.error(u"Media path from folderCombo could not be found in fileSystemModel!")
                self.errorEncountered.emit(Message.ERROR, u"Media folder '%s' could not be found!" % newMediaFolder, u"")
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
    def addToPlaylist(self, sources, append):
        """
        Sets and adds media files to playlist.
        @param sources: list of (path, duration)
        @type sources: list of (unicode, int)
        """
        n = len(sources)
        logger.debug(u"Adding '%s' sources to current playlist.", n)

        lastItemIndex = self.playlist.rowCount() if append else 0
        self.playlist.setRowCount(lastItemIndex + n)

        i = 0
        for path, duration in sources:
            titleItem = QTableWidgetItem(os.path.basename(path))
            durationItem = QTableWidgetItem(QTime().addMSecs(duration).toString("hh:mm:ss"))
            pathItem = QTableWidgetItem(path)
            self.playlist.setItem(i + lastItemIndex, 0, titleItem)
            self.playlist.setItem(i + lastItemIndex, 2, durationItem)
            self.playlist.setItem(i + lastItemIndex, 3, pathItem)
            i += 1

    @Slot()
    def cancelAdding(self):
        logger.debug(u"Canceling adding new files to playlist (parsing).")
        self.parser.stop(True)


    @Slot(int, unicode, unicode)
    def displayErrorMsg(self, er_type, text, details=u""):
        """
        Called to display warnings and errors.
        @param er_type: error type (Message enum)
        @param text: main text
        @param details: description
        """
        if er_type == Message.WARNING:
            icon = QPixmap(u":/new/icons/icons/warning.png").scaled(14, 14, mode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.WARNING_MSG_DELAY, self.clearErrorMsg)
        elif er_type == Message.ERROR:
            icon = QPixmap(u":/new/icons/icons/error.png").scaled(14, 14, mode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.ERROR_MSG_DELAY, self.clearErrorMsg)
            QApplication.beep()
        elif er_type == Message.CRITICAL:
            msgBox = QMessageBox(self)
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle(u"Critical error")
            msgBox.setText(text)
            msgBox.setInformativeText(details)
            msgBox.exec_()

    @Slot()
    def clearErrorMsg(self):
        """
        Called to clear statusbar after displaying error message (widgets).
        """
        self.stBarMsgIcon.hide()
        self.stBarMsgText.hide()

    def displayProgress(self, description, minimum=0, maximum=0):
        """
        Called to show progress bar and label in statusbar to inform user when some action on background is running.
        When minimum and maximum attributes are not set (zero), busy progress bar is shown.
        @type description: unicode
        @type minimum: int
        @type maximum: int
        """
        # self.progressBar.setMaximumSize(200, self.progressBar.minimumSizeHint().height())
        self.progressBar.setMinimum(minimum)
        self.progressBar.setMaximum(maximum)
        self.progressLabel.setText(description)
        self.progressBar.show()
        self.progressLabel.show()
        self.progressCancelBtn.show()

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
        self.progressLabel.hide()
        self.progressBar.hide()
        self.progressCancelBtn.hide()

    @Slot()
    def playing(self):
        logger.debug(u"Media player playing.")
        icon = QIcon()
        icon.addPixmap(QPixmap(u":/new/icons/icons/media-pause.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)

    @Slot()
    def paused(self):
        logger.debug(u"Media player paused.")
        icon = QIcon()
        icon.addPixmap(QPixmap(u":/new/icons/icons/media-play.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)

    @Slot()
    def stopped(self):
        logger.debug(u"Media player stopped.")
        self.paused()
        self.timeLbl.setText(u"00:00:00")
        self.seekerSlider.blockSignals(True)        # prevent syncing
        self.seekerSlider.setValue(0)
        self.seekerSlider.blockSignals(False)

    @Slot(int)
    def syncPlayTime(self, value):
        """
        @param value: time in milliseconds
        @type value: int
        """
        self.timeLbl.setText(QTime().addMSecs(value).toString("hh:mm:ss"))

    @Slot(float)
    def syncSeeker(self, value):
        """
        When media time is changed, sync seeker position.
        @param value: Relative position from [0; 1]
        @type value: float
        """
        # do not sync if user is going to change slider position
        if not self.seekerSlider.mouseLBPressed:
            value = int(value * 100)
            self.seekerSlider.blockSignals(True)
            self.seekerSlider.setValue(value)
            self.seekerSlider.blockSignals(False)

    # def printTime(self):
    #     # FIXME debug only
    #     print (time.time() - self.t0) * 1000

    @Slot(int)
    def displayCurrentMedia(self, index):
        """
        When media is changed, select row corresponding with media.
        @param index: position of media in media_list == position in playlist table
        @type index: int
        """
        self.playlist.setCurrentCell(index, 0)          # select the entire row due to table selection behaviour

    @Slot()
    def playNow(self, row=None, col=None):
        """
        Play song from playlist table immediately.
        @param row: song row number
        @param col: ignore - just slot requirement
        """
        index = self.playlist.currentRow() if row is None else row
        if index == -1:
            return

        fileName = os.path.basename(self.playlist.item(index, self.playlist.columnCount()-1).text())
        logger.debug(u"Play now called, playing #%s song from playlist named '%s'.", index, fileName)

        self.mediaPlayer.play(index)

    @Slot()
    def remFromPlaylist(self, row=None):
        """
        Removes song from playlist table and from player (media_list).
        @param row: row number in playlist table
        """
        index = self.playlist.currentRow() if row is None else row
        if index == -1:
            return

        fileName = os.path.basename(self.playlist.item(index, self.playlist.columnCount()-1).text())
        logger.debug(u"Removing from playlist #%s song named '%s'", index, fileName)

        self.mediaPlayer.removeItem(index)
        self.playlist.removeRow(index)

    @Slot()
    def remFromDisk(self, row=None):
        """
        Removes song from playlist table, from player (media_list) and from disk if possible.
        @param row: row number in playlist table
        """
        index = self.playlist.currentRow() if row is None else row
        if index == -1:
            return

        filePath = self.playlist.item(index, self.playlist.columnCount()-1).text()
        fileName = os.path.basename(filePath)
        self.remFromPlaylist(index)

        logger.debug(u"Removing from disk #%s song named '%s' on path '%s'", index, fileName, filePath)

        try:
            misc.moveToTrash(filePath)
        except OSError, exception:
            self.errorEncountered.emit(Message.ERROR, u"Unable to move path to Trash path '%s'!" % filePath,
                                       u"Details: %s" % exception.message)

    @Slot(bool)
    def toggleShuffle(self, checked):
        self.mediaPlayer.setShuffle(checked)

    @Slot(bool)
    def toggleRepeat(self, checked):
        self.mediaPlayer.setRepeat(checked)

    def closeEvent(self, event):
        # self.mediaPlayerThread.quit()
        self.scannerThread.quit()
        self.parserThread.quit()

        self.saveSettings()

        # print >> sys.stderr, "neco"
        # logger.error("neco log")
        # StdErrRedirector.redirect_C_stderr_back()
        event.accept()








