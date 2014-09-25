# -*- coding: utf-8 -*-

"""
Main application GUI module.
"""

__version__ = "$Id$"

import logging
import pickle
import sys
import os
import errno
import json
import time

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from forms.main_form import MainForm
from dialogs.library_dialog import LibraryDialog
from components import disk
from components import media
from components import global_hotkey_hook
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

    errorEncountered = pyqtSignal(int, unicode, unicode)        # (Message.CRITICAL, main_text, description)
    scanFiles = pyqtSignal(unicode)

    myComputerPathIndex = None

    WARNING_MSG_DELAY = 5000
    ERROR_MSG_DELAY = 10000

    def __init__(self):
        super(MainApp, self).__init__()
        self.appRootPath = os.path.dirname(sys.argv[0])
        self.appDataPath = os.path.join(self.appRootPath, 'data')
        self.mediaLibFile = os.path.join(self.appDataPath, 'medialib.json')
        self.session_file = os.path.join(self.appDataPath, 'session.dat')

        self.setupUi(self)          # setups all GUI components from form (design part)
        self.setupPlayer()
        self.setupGUISignals()

        self.setupScanner()
        self.setupActionsSignals()
        self.setupSystemHook()

        self.checkPaths()
        self.setupFileBrowser(initModel=True)       # todo: future: set dynamically (from last session)

        self.loadSettings()

        QTimer.singleShot(25, self.loadSettingsQueued)
        logger.debug(u"Main application dialog initialized")

    def setupGUISignals(self):
        """
        Connects GUI components with desired slots.
        Only for GUI components!
        """
        self.sourceBrowser.itemSelectionChanged.connect(self.changeSource)
        self.folderCombo.currentIndexChanged.connect(self.changeFileBrowserRoot)
        self.libraryBtn.clicked.connect(self.openLibraryDialog)
        self.mainTreeBrowser.customContextMenuRequested.connect(self.sourceItemsBrowserContextMenu)
        self.playlistTable.customContextMenuRequested.connect(self.playlistContextMenu)
        self.playlistTable.cellDoubleClicked.connect(self.playNow)
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

        self.playlistTable.enterShortcut.activated.connect(self.playNow)
        self.playlistTable.delShortcut.activated.connect(self.remFromPlaylist)
        self.playlistTable.shiftDelShortcut.activated.connect(self.remFromDisk)

    def setupActionsSignals(self):
        self.mediaPlayPauseAction.triggered.connect(self.mediaPlayer.playPause)
        self.mediaStopAction.triggered.connect(self.mediaPlayer.stop)
        self.mediaNextAction.triggered.connect(self.mediaPlayer.next)
        self.mediaPreviousAction.triggered.connect(self.mediaPlayer.prev)

    def setupSystemHook(self):
        """
        Initializes system-wide keyboard hook, which listens for media control keys (Media_Play_Pause,
        Media_Stop, Media_Next_Track, Media_Prev_Track).
        Listener is executed in separated thread (thread clocking method).
        Caught keys are mapped to signal and then forwarded to menubar actions.
        """
        self.hkHookThread = QThread(self)

        if os.name == 'nt':
            self.hkHook = global_hotkey_hook.WindowsHook()
        elif os.name == 'posix':
            # todo: ckeck platform - linux only
            return
        else:
            logger.warning("System-wide keyboard hook is not available for '%s' platform" % os.name)
            return

        self.hkHook.moveToThread(self.hkHookThread)

        self.hkHook.mediaPlayKeyPressed.connect(self.mediaPlayPauseAction.trigger)
        self.hkHook.mediaStopKeyPressed.connect(self.mediaStopAction.trigger)
        self.hkHook.mediaNextTrackKeyPressed.connect(self.mediaNextAction.trigger)
        self.hkHook.mediaPrevTrackKeyPressed.connect(self.mediaPreviousAction.trigger)

        self.hkHookThread.started.connect(self.hkHook.startHook)
        self.hkHookThread.start()

    def setupPlayer(self):
        """
        Initializes VLC based media player.
        Player class (basically it is only the interface) lives in main thread.
        VlC player itself lives in separated threads!
        """
        self.mediaPlayer = media.MediaPlayer()

        self.mediaPlayer.mediaAdded.connect(self.addToPlaylist)
        self.mediaPlayer.playing.connect(self.playing)
        self.mediaPlayer.paused.connect(self.paused)
        self.mediaPlayer.stopped.connect(self.stopped)
        self.mediaPlayer.timeChanged.connect(self.syncPlayTime)
        self.mediaPlayer.positionChanged.connect(self.syncSeeker)
        self.mediaPlayer.mediaChanged.connect(self.displayCurrentMedia)

    def setupScanner(self):
        """
        Setup classes for disk digging (media searching) and asynchronous parsing.
        Scanner and parser live in separated threads.
        """
        # asynchronous scanner
        self.scanner = disk.RecursiveBrowser(nameFilter=FileExt_, followSym=False)
        self.scannerThread = QThread(self)
        self.scanner.moveToThread(self.scannerThread)
        # asynchronous parser
        self.parser = media.MediaParser()
        self.parserThread = QThread(self)
        self.parser.moveToThread(self.parserThread)

        self.scanFiles.connect(self.scanner.scanFiles)
        self.parser.finished.connect(self.clearProgress)
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

    def loadSettings(self):
        """
        Method called on start to load and set stuff.
        Method is called directly, so no heavy operation is expected. (see loadSettingsQueued() for more info)
        """
        logger.debug(u"Global load settings called. Loading settings...")

    @pyqtSlot()
    def loadSettingsQueued(self):
        """
        This method is called as slot directly from main thread, but few milliseconds queued,
        so Qt engine can render application.
        Method is delayed for 25ms. On average computer is this delay enough to fully render whole application,
        but almost unnoticeable.
        """
        self.loadSession()
        self.changeSource(Sources.FILES)

    def loadSession(self):
        """
        Loads last session information
        e.g. last playlist, volume settings, etc.
        """
        if not os.path.isfile(self.session_file):
            logger.debug(u"No session file found, skipping")
            return

        logger.debug(u"Loading session file...")

        try:
            with open(self.session_file, 'rb') as f:
                session_data = pickle.load(f)
        except IOError:
            logger.exception(u"Unable to load data from session file!")
        else:
            self.loadPlaylist(session_data)

            # load shuffle, repeat and volume
            self.mediaPlayer.shuffle_mode = session_data['shuffle']
            self.mediaPlayer.repeat_mode = session_data['repeat']
            self.volumeSlider.setValue(session_data['volume'])
            self.shuffleBtn.blockSignals(True)
            self.shuffleBtn.setChecked(self.mediaPlayer.shuffle_mode)
            self.shuffleBtn.blockSignals(False)
            self.repeatBtn.blockSignals(True)
            self.repeatBtn.setChecked(self.mediaPlayer.repeat_mode)
            self.repeatBtn.blockSignals(False)

            logger.debug(u"Session restored successfully")

    def loadPlaylist(self, session_data):
        """
        Loads and sets saved playlist from last session (from disk)
        @param session_data: data from disk are stored in this dict file
        """
        table_content = session_data['playlist_table']              # playlistTable content
        if not table_content:               # playlist is empty
            return

        n_cols = len(table_content)
        n_rows = len(table_content[0])

        paths_list = table_content[-1]

        logger.debug(u"Restoring items from playlist in playlistTable...")
        self.playlistTable.setRowCount(n_rows)
        self.playlistTable.setColumnCount(n_cols)

        # array is transposed ... [ [1st col], [2nd col], etc ]
        for row in range(n_rows):
            for column in range(n_cols):
                cell_data = table_content[column][row]
                if not cell_data:       # empty or None cell -> skip
                    continue

                item = QTableWidgetItem(cell_data)
                self.playlistTable.setItem(row, column, item)

        logger.debug(u"Restoring items from playlist in mediaPlayer object...")
        self.mediaPlayer.id_playlist = session_data['id_playlist']
        self.mediaPlayer.playlist_pointer = session_data['playlist_pointer']
        self.mediaPlayer.playlist_len = session_data['playlist_len']
        self.mediaPlayer.addMedia(paths_list, restoring_session=True)

    def saveSettings(self):
        """
        When program is about to close, all desired settings is saved.
        Called when dialog closeEvent in caught.
        """
        logger.debug(u"Global save settings called. Saving settings...")
        self.saveSession()
        self.mainTreeBrowser.saveSettings()

    def saveSession(self):
        """
        Save current session information
        e.g. current playlist, volume settings, etc.
        """
        session_data = {}

        self.savePlaylist(session_data)

        session_data['shuffle'] = self.mediaPlayer.shuffle_mode
        session_data['repeat'] = self.mediaPlayer.repeat_mode
        session_data['volume'] = self.mediaPlayer.volume()

        logger.debug(u"Dumping session file to disk...")
        with open(self.session_file, 'wb') as f:
            pickle.dump(session_data, f)

    def savePlaylist(self, session_data):
        """
        Dump information about playlist from playlist_table and from media_player
        @param session_data: all information are stored to this dict file
        """
        logger.debug(u"Dumping and saving playlist information...")

        n_cols = self.playlistTable.columnCount()
        n_rows = self.playlistTable.rowCount()

        # array is transposed ... [ [1st col], [2nd col], etc ] for easier manipulation when loading data back
        table_content = [[None for x in range(n_rows)] for x in range(n_cols)]
        for row in range(self.playlistTable.rowCount()):
            for column in range(self.playlistTable.columnCount()):
                item = self.playlistTable.item(row, column)

                if item is not None:
                    table_content[column][row] = self.playlistTable.item(row, column).text()
                else:
                    table_content[column][row] = None

        session_data['playlist_table'] = table_content
        session_data['id_playlist'] = self.mediaPlayer.id_playlist
        session_data['playlist_pointer'] = self.mediaPlayer.playlist_pointer
        session_data['playlist_len'] = self.mediaPlayer.playlist_len

    @pyqtSlot(int)
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

        # remember selected folder in combobox to set it back lately
        # signals must be blocked because currentIndexChanged() signal is emitted after clear()
        current_folder_text = self.folderCombo.currentText()
        self.folderCombo.blockSignals(True)
        self.folderCombo.clear()

        self.folderCombo.addItem(self.fileBrowserModel.myComputer(Qt.DisplayRole))      # get default name
        folders_to_display = [self.fileBrowserModel.myComputer(Qt.DisplayRole), ]         # save table of contents

        # add only valid folders from medialib to folderCombobox
        for folder in mediaFolders:
            folder = QDir.cleanPath(folder)       # normalize => remove redundant slashes, etc.
            if os.path.isdir(folder):
                self.folderCombo.addItem(folder)
                folders_to_display.append(folder)
            else:
                print "aaaaa"
                self.errorEncountered.emit(Message.WARNING, u"Some folders in media library don't exist.", u"")

        # set back previously selected (current) item in folderCombo if exists (may be deleted => set root folder)
        if current_folder_text in folders_to_display:
            self.folderCombo.setCurrentIndex(folders_to_display.index(current_folder_text))
            self.folderCombo.blockSignals(False)
        else:
            self.folderCombo.blockSignals(False)
            self.folderCombo.currentIndexChanged.emit(0)

    def setupPlaylistBrowser(self):
        # TODO future: implement
        pass

    def setupRadioBrowser(self):
        # TODO future: implement
        pass

    @pyqtSlot('QPointF')
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
        playNow = QAction(QIcon(u":/icons/play-now.png"), u"Play now", menu)
        addToPlayList = QAction(QIcon(u":/icons/play-next.png"), u"Add to playlist", menu)
        playAll = QAction(QIcon(u":/icons/play-now.png"), u"Play all", menu)
        removeFromDisk = QAction(QIcon(u":/icons/delete.png"), u"Remove from disk", menu)
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

    @pyqtSlot('QPointF')
    def playlistContextMenu(self, pos):
        item = self.playlistTable.itemAt(pos)
        if not item:
            return

        logger.debug(u"Opening playlist context menu.")
        menu = QMenu(self.playlistTable)
        playNowAction = QAction(QIcon(u":/icons/play-now.png"), u"Play now", menu)
        playNowAction.setShortcut(QKeySequence(Qt.Key_Enter))
        remFromPlaylistAction = QAction(u"Remove from playlist", menu)
        remFromPlaylistAction.setShortcut(QKeySequence(Qt.Key_Delete))
        remFromDiskAction = QAction(QIcon(u":/icons/delete.png"), u"Remove from disk", menu)
        remFromDiskAction.setShortcut(QKeySequence(Qt.SHIFT + Qt.Key_Delete))
        separator = QAction(menu)
        separator.setSeparator(True)

        menu.addActions([playNowAction, separator])
        removeMenu = menu.addMenu(u"Remove")
        removeMenu.addActions([remFromPlaylistAction, remFromDiskAction])
        choice = menu.exec_(self.playlistTable.viewport().mapToGlobal(pos))

        index = self.playlistTable.row(item)
        if choice is playNowAction:
            self.playNow(index)
        elif choice is remFromPlaylistAction:
            self.remFromPlaylist(index)
        elif choice is remFromDiskAction:
            self.remFromDisk(index)

    @pyqtSlot()
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

    @pyqtSlot(int)
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

    @pyqtSlot()
    def openLibraryDialog(self):
        """
        When library button is clicked, open library editor dialog.
        When dialog is closed, refresh media folders combobox.
        """
        libraryDialog = LibraryDialog(self.mediaLibFile, self)
        libraryDialog.finished.connect(self.setupFileBrowser)
        libraryDialog.exec_()

    @pyqtSlot(list, bool)
    def addToPlaylist(self, sources, append):
        """
        Sets and adds media files to playlist.
        @param sources: list of (path, duration)
        @type sources: list of (unicode, int)
        """
        n = len(sources)
        logger.debug(u"Adding '%s' sources to current playlist.", n)

        lastItemIndex = self.playlistTable.rowCount() if append else 0
        self.playlistTable.setRowCount(lastItemIndex + n)

        i = 0
        for path, duration in sources:
            titleItem = QTableWidgetItem(os.path.basename(path))
            durationItem = QTableWidgetItem(QTime().addMSecs(duration).toString("hh:mm:ss"))
            pathItem = QTableWidgetItem(path)
            self.playlistTable.setItem(i + lastItemIndex, 0, titleItem)
            self.playlistTable.setItem(i + lastItemIndex, 2, durationItem)
            self.playlistTable.setItem(i + lastItemIndex, 3, pathItem)
            i += 1

    @pyqtSlot()
    def cancelAdding(self):
        logger.debug(u"Canceling adding new files to playlist (parsing).")
        self.parser.stop(True)


    @pyqtSlot(int, unicode, unicode)
    def displayErrorMsg(self, er_type, text, details=u""):
        """
        Called to display warnings and errors.
        @param er_type: error type (Message enum)
        @param text: main text
        @param details: description
        """

        print "display error"

        if er_type == Message.WARNING:
            icon = QPixmap(u":/icons/warning.png").scaled(14, 14, transformMode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.WARNING_MSG_DELAY, self.clearErrorMsg)
        elif er_type == Message.ERROR:
            icon = QPixmap(u":/icons/error.png").scaled(14, 14, transformMode=Qt.SmoothTransformation)
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

    @pyqtSlot()
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

    @pyqtSlot()
    def clearProgress(self):
        """
        Hides progress bar and label from statusbar when showing progress
        """
        self.progressLabel.hide()
        self.progressBar.hide()
        self.progressCancelBtn.hide()

    @pyqtSlot()
    def playing(self):
        logger.debug(u"Media player playing.")
        icon = QIcon()
        icon.addPixmap(QPixmap(u":/icons/media-pause.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)
        self.mediaPlayPauseAction.setIcon(icon)
        self.mediaPlayPauseAction.setText(u"Pause")

    @pyqtSlot()
    def paused(self):
        logger.debug(u"Media player paused.")
        icon = QIcon()
        icon.addPixmap(QPixmap(u":/icons/media-play.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)
        self.mediaPlayPauseAction.setIcon(icon)
        self.mediaPlayPauseAction.setText(u"Play")

    @pyqtSlot()
    def stopped(self):
        logger.debug(u"Media player stopped.")
        self.paused()
        self.timeLbl.setText(u"00:00:00")
        self.seekerSlider.blockSignals(True)        # prevent syncing
        self.seekerSlider.setValue(0)
        self.seekerSlider.blockSignals(False)

        icon = QIcon()
        icon.addPixmap(QPixmap(u":/icons/media-play.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)
        self.mediaPlayPauseAction.setIcon(icon)
        self.mediaPlayPauseAction.setText(u"Play")

    @pyqtSlot(int)
    def syncPlayTime(self, value):
        """
        @param value: time in milliseconds
        @type value: int
        """
        self.timeLbl.setText(QTime().addMSecs(value).toString("hh:mm:ss"))

    @pyqtSlot(float)
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

    @pyqtSlot(int)
    def displayCurrentMedia(self, index):
        """
        When media is changed, select row corresponding with media.
        @param index: position of media in media_list == position in playlist table
        @type index: int
        """
        self.playlistTable.setCurrentCell(index, 0)          # select the entire row due to table selection behaviour

    @pyqtSlot()
    def playNow(self, row=None, col=None):
        """
        Play song from playlist table immediately.
        @param row: song row number
        @param col: ignore - just slot requirement
        """
        index = self.playlistTable.currentRow() if row is None else row
        if index == -1:
            return

        fileName = os.path.basename(self.playlistTable.item(index, self.playlistTable.columnCount()-1).text())
        logger.debug(u"Play now called, playing #%s song from playlist named '%s'.", index, fileName)

        self.mediaPlayer.play(index)

    @pyqtSlot()
    def remFromPlaylist(self, row=None):
        """
        Removes song from playlist table and from player (media_list).
        @param row: row number in playlist table
        """
        index = self.playlistTable.currentRow() if row is None else row
        if index == -1:
            return

        fileName = os.path.basename(self.playlistTable.item(index, self.playlistTable.columnCount()-1).text())
        logger.debug(u"Removing from playlist #%s song named '%s'", index, fileName)

        self.mediaPlayer.removeItem(index)
        self.playlistTable.removeRow(index)

    @pyqtSlot()
    def remFromDisk(self, row=None):
        """
        Removes song from playlist table, from player (media_list) and from disk if possible.
        @param row: row number in playlist table
        """
        index = self.playlistTable.currentRow() if row is None else row
        if index == -1:
            return

        filePath = self.playlistTable.item(index, self.playlistTable.columnCount()-1).text()
        fileName = os.path.basename(filePath)
        self.remFromPlaylist(index)

        logger.debug(u"Removing from disk #%s song named '%s' on path '%s'", index, fileName, filePath)

        try:
            misc.moveToTrash(filePath)
        except OSError, exception:
            self.errorEncountered.emit(Message.ERROR, u"Unable to move path to Trash path '%s'!" % filePath,
                                       u"Details: %s" % exception.message)

    @pyqtSlot(bool)
    def toggleShuffle(self, checked):
        self.mediaPlayer.setShuffle(checked)

    @pyqtSlot(bool)
    def toggleRepeat(self, checked):
        self.mediaPlayer.setRepeat(checked)

    def closeEvent(self, event):
        """
        Method called when close event caught.
        Quits all threads, saves settings, etc. before application exit.
        :type event: QCloseEvent
        """
        # self.mediaPlayerThread.quit()
        self.scannerThread.quit()
        self.parserThread.quit()
        self.hkHookThread.quit()

        self.saveSettings()

        # print >> sys.stderr, "neco"
        # logger.error("neco log")
        # StdErrRedirector.redirect_C_stderr_back()
        event.accept()








