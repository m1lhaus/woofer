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

"""
Main application GUI module.
"""

import logging
import ujson
import sys
import os
import errno
import subprocess

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from forms import main_form
from dialogs import library_dialog
from dialogs import settings_dialog
from components.translator import tr

import components.disk
import components.media
import components.scheduler
import components.network
import tools

if sys.platform == "win32":
    from components import winkeyhook as keyhook
elif sys.platform.startswith('linux'):
    from components import xkeyhook as keyhook


logger = logging.getLogger(__name__)

# all supported codecs and formats can be found at https://wiki.videolan.org/VLC_Features_Formats/
FileExt = ('*.mp3', '*.m4a', '*.m4p', '*.flac', '*.wav', '*.wma', '*.aac', '*.mpga', '*.3ga', '*.669', '*.a52',
           '*.ac3', '*.adt', '*.adts', '*.aif', '*.aifc', '*.aiff', '*.amr', '*.aob', '*.ape', '*.awb', '*.caf',
           '*.dts',  '*.it', '*.kar',  '*.m5p', '*.mid', '*.mka', '*.mlp', '*.mod', '*.mpa', '*.mp1', '*.mp2',
           '*.mpc',  '*.oga', '*.ogg', '*.oma', '*.opus', '*.qcp', '*.ra', '*.rmi', '*.s3m', '*.spx', '*.thd',
           '*.tta', '*.voc', '*.vqf', '*.w64', '*.wv', '*.xa', '*.xm')
assert not any([not ext.startswith('*.') for ext in FileExt])
assert len(set(FileExt)) == len(FileExt)


class MainApp(QMainWindow, main_form.MainForm):
    """
    Main application GUI form.
    - setup main window dialog
    - connects signals from dialogs widgets

    @param mode: DEBUG or PRODUCTION
    @param play_path: input media/dir path given by user via console arg
    """

    errorSignal = pyqtSignal(int, str, str)        # (tools.Message.CRITICAL, main_text, description)
    removeFileSignal = pyqtSignal(str)
    scanFilesSignal = pyqtSignal(str)

    INFO_MSG_DELAY = 5000
    WARNING_MSG_DELAY = 10000
    ERROR_MSG_DELAY = 20000
    QUEUED_SETTINGS_DELAY = 40
    TERMINATE_DELAY = 3000
    
    FILES_SOURCE = 0
    PLAYLISTS_SOURCE = 1
    RADIO_SOURCE = 2

    def __init__(self, mode, play_path):
        super(MainApp, self).__init__()
        self.mediaLibFile = os.path.join(tools.DATA_DIR, 'medialib.dat')
        self.session_file = os.path.join(tools.DATA_DIR, 'session.dat')
        self.input_path = play_path if play_path else None
        self.mediaPlayer = components.media.MediaPlayer()

        self.myComputerPathIndex = None
        self.homeDirIndex = None
        self.oldVolumeValue = 0
        self.updateOnExit = False
        self.updateExe = None
        self.availableUpdateLabel = None
        self.downloadUpdateBtn = None
        self.updateOnExit = False
        self.restartAfterUpdate = False

        # setups all GUI components from form (design part)
        self.setupUi(self)
        self.setWindowTitle("Woofer" if mode == 'PRODUCTION' else "Woofer - debug mode")
        self.setupGUISignals()
        self.setupPlayerSignals()
        self.setupActionsSignals()

        # check if all needed folders and files are ready and writable
        self.checkPaths()

        # create all components in their independent threads
        self.setupDiskTools()
        self.setupSystemHook()
        self.setupScheduledTasks()

        # play given file path as console arg if any
        if self.input_path:
            self.playPath(self.input_path, append=False)

        # restore session/settings
        self.loadSettings()
        QTimer.singleShot(self.QUEUED_SETTINGS_DELAY, self.loadSettingsQueued)
        logger.debug("Main application dialog initialized")

    def setupGUISignals(self):
        """
        Connects GUI components with desired slots.
        Only for GUI components!
        """
        # self.sourceBrowser.itemSelectionChanged.connect(self.changeSource)
        self.folderCombo.currentIndexChanged.connect(self.changeFileBrowserRoot)
        self.libraryBtn.clicked.connect(self.openLibraryDialog)
        self.mainTreeBrowser.customContextMenuRequested.connect(self.fileBrowserContextMenu)
        self.playlistTable.customContextMenuRequested.connect(self.playlistContextMenu)
        self.playlistTable.cellDoubleClicked.connect(self.playlistPlayNow)
        self.progressCancelBtn.clicked.connect(self.cancelAdding)
        self.mainTreeBrowser.activated.connect(self.fileBrowserActivated)

        self.errorSignal.connect(self.displayErrorMsg)

        self.playPauseBtn.clicked.connect(self.mediaPlayer.playPause)
        self.stopBtn.clicked.connect(self.mediaPlayer.stop)
        self.nextBtn.clicked.connect(self.mediaPlayer.next_track)
        self.previousBtn.clicked.connect(self.mediaPlayer.prev_track)
        self.seekerSlider.valueChanged.connect(self.mediaPlayer.setPosition)
        self.volumeSlider.valueChanged.connect(self.mediaPlayer.setVolume)
        self.volumeSlider.valueChanged.connect(self.volumeChanged)
        self.shuffleBtn.toggled.connect(self.toggleShuffle)
        self.repeatBtn.toggled.connect(self.toggleRepeat)
        self.volumeBtn.clicked.connect(self.displayVolumePopup)
        self.muteBtn.toggled.connect(self.muteStatusChanged)

        self.playlistTable.enterShortcut.activated.connect(self.playlistPlayNow)
        self.playlistTable.delShortcut.activated.connect(self.playlistRemFromPlaylist)
        self.playlistTable.shiftDelShortcut.activated.connect(self.playlistRemFromDisk)

    def setupActionsSignals(self):
        self.mediaPlayPauseAction.triggered.connect(self.mediaPlayer.playPause)
        self.mediaStopAction.triggered.connect(self.mediaPlayer.stop)
        self.mediaNextAction.triggered.connect(self.mediaPlayer.next_track)
        self.mediaPreviousAction.triggered.connect(self.mediaPlayer.prev_track)
        self.mediaShuffleAction.triggered.connect(self.shuffleBtn.toggle)
        self.mediaRepeatAction.triggered.connect(self.repeatBtn.toggle)
        self.mediaMuteAction.triggered.connect(self.muteBtn.toggle)
        self.mediaQuitAction.triggered.connect(self.close)

        self.playlistClearAction.triggered.connect(self.clearPlaylist)
        self.toolsSettingsAction.triggered.connect(self.openSettingsDialog)
        self.helpAboutAction.triggered.connect(self.openAboutDialog)

    def setupSystemHook(self):
        """
        Initializes system-wide keyboard hook, which listens for media control keys (Media_Play_Pause,
        Media_Stop, Media_Next_Track, Media_Prev_Track).
        Listener is executed in separated thread (thread clocking method).
        Caught keys are mapped to signal and then forwarded to menubar actions.
        """
        self.hkHookThread = QThread(self)
        self.hkHook = keyhook.GlobalHKListener()
        self.hkHook.moveToThread(self.hkHookThread)
        self.hkHook.mediaPlayKeyPressed.connect(self.mediaPlayPauseAction.trigger)
        self.hkHook.mediaStopKeyPressed.connect(self.mediaStopAction.trigger)
        self.hkHook.mediaNextTrackKeyPressed.connect(self.mediaNextAction.trigger)
        self.hkHook.mediaPrevTrackKeyPressed.connect(self.mediaPreviousAction.trigger)
        self.hkHook.errorSignal.connect(self.displayErrorMsg)

        self.hkHookThread.started.connect(self.hkHook.start_listening)
        self.hkHookThread.start()

    def setupPlayerSignals(self):
        """
        Initializes VLC based media player.
        Player class (basically it is only the interface) lives in main thread.
        VlC player itself lives in separated threads!
        """
        self.mediaPlayer.mediaAddedSignal.connect(self.addToPlaylist)
        self.mediaPlayer.playingSignal.connect(self.playing)
        self.mediaPlayer.pausedSignal.connect(self.paused)
        self.mediaPlayer.stoppedSignal.connect(self.stopped)
        self.mediaPlayer.timeChangedSignal.connect(self.syncPlayTime)
        self.mediaPlayer.positionChangedSignal.connect(self.syncSeeker)
        self.mediaPlayer.mediaChangedSignal.connect(self.displayCurrentMedia)
        self.mediaPlayer.errorSignal.connect(self.displayErrorMsg)

    def setupDiskTools(self):
        """
        Setup classes for disk digging (media searching) and asynchronous parsing.
        Scanner and parser live in separated threads.
        """
        # asynchronous scanner
        self.scanner = components.disk.RecursiveBrowser(names_filter=FileExt)
        self.scannerThread = QThread(self)

        # asynchronous parser
        self.parser = components.media.MediaParser()
        self.parserThread = QThread(self)

        # asynchronous file/folder remover
        self.fileRemover = components.disk.MoveToTrash()
        self.fileRemoverThread = QThread(self)

        self.scanFilesSignal.connect(self.scanner.scanFiles)
        self.parser.finishedSignal.connect(self.clearProgress)
        self.parser.finishedSignal.connect(self.mediaPlayer.mediaAddingFinished)
        self.parser.dataParsedSignal.connect(self.mediaPlayer.addMedia)
        self.scanner.parseDataSignal.connect(self.parser.parseMedia)
        self.scanner.errorSignal.connect(self.displayErrorMsg)
        self.removeFileSignal.connect(self.fileRemover.remove)
        self.fileRemover.errorSignal.connect(self.displayErrorMsg)
        self.scanner.moveToThread(self.scannerThread)
        self.parser.moveToThread(self.parserThread)
        self.fileRemover.moveToThread(self.fileRemoverThread)

        self.scannerThread.start()
        self.parserThread.start()
        self.fileRemoverThread.start()

    def setupScheduledTasks(self):
        """
        Setup scheduled tasks as update checker, logfile cleaner, etc.
        All scheduled tasks live in separated threads.
        """
        self.logCleaner = components.scheduler.LogCleaner()
        self.logCleanerThread = QThread(self)
        self.logCleaner.moveToThread(self.logCleanerThread)
        self.logCleanerThread.started.connect(self.logCleaner.start)

        self.logCleanerThread.start()

        self.updaterThread = QThread(self)
        self.updater = components.scheduler.Updater()
        self.updater.moveToThread(self.updaterThread)
        self.updaterThread.started.connect(self.updater.start)

        self.updater.updaterStartedSignal.connect(self.startDownloadingUpdate)
        self.updater.updateStatusSignal.connect(self.updateDownloaderStatus)
        self.updater.updaterFinishedSignal.connect(self.endDownloadingUpdate)
        self.updater.readyForUpdateOnRestartSignal.connect(self.prepareForAppUpdate)
        self.updater.availableUpdatePackageSignal.connect(self.displayAvailableUpdates)
        self.updater.errorSignal.connect(self.displayErrorMsg)

        if sys.platform.startswith('win') and tools.IS_WIN32_EXE:
            self.updaterThread.start()

    def checkPaths(self):
        """
        Creates data folder and media library file if doesn't exist!
        """
        # check data folder
        try:
            os.makedirs(tools.DATA_DIR)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                logger.exception("Unable to create data folder on path: %s", tools.DATA_DIR)
                self.errorSignal.emit(tools.ErrorMessages.CRITICAL, tr['ERROR_CREATE_DATA_FOLDER'], str(exception))
        else:
            logger.debug("Data folder didn't exist and has been created.")

        # check medialib file
        try:
            with open(self.mediaLibFile, 'r') as f:
                pass
        except IOError as exception:
            #  file doesn't exist => create and init file
            if exception.errno == errno.ENOENT:
                try:
                    with open(self.mediaLibFile, 'w') as f:
                        f.write('[]')
                except IOError:
                    logger.exception("Error when creating new media library file.")
                    self.errorSignal.emit(tools.ErrorMessages.CRITICAL, tr['ERROR_CREATE_MEDIALIB_FILE'], str(exception))
                else:
                    logger.debug("Media file has been created and initialized.")
            else:
                logger.exception("Error when reading medialib file.")
                self.errorSignal.emit(tools.ErrorMessages.CRITICAL, tr['ERROR_READ_MEDIALIB_FILE'], str(exception))

    @pyqtSlot(int)
    def setupFileBrowser(self, rcode=None, initModel=False):
        """
        Re-initialize file model for file browser treeView and setup mediaLib folder combobox .
        @param rcode: return code from library dialog (ignore it)
        @param initModel: if true, fileSystemModel is re-initialized
        """
        logger.debug("Opening media folder and reading data.")
        try:
            with open(self.mediaLibFile, 'r') as mediaFile:
                mediaFolders = ujson.load(mediaFile)
        except IOError as exception:
            logger.exception("Error when reading medialib file.")
            self.errorSignal.emit(tools.ErrorMessages.CRITICAL, tr['READ_MEDIALIB_FILE_ERROR'], str(exception))
            raise
        except ValueError as exception:
            logger.exception("Unable to load and parse data from JSON file.")
            self.errorSignal.emit(tools.ErrorMessages.CRITICAL, tr['ERROR_PARSE_MEDIALIB_FILE'], str(exception))
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

        self.folderCombo.addItem(tr['HOME_DIR'])
        self.folderCombo.addItem(tr['MY_COMPUTER'])  # fileBrowserModel.myComputer(Qt.DisplayRole)
        folders_to_display = [tr['HOME_DIR'], tr['MY_COMPUTER'], ]         # save table of contents

        # add only valid folders from medialib to folderCombobox
        for folder in mediaFolders:
            folder = QDir.cleanPath(folder)       # normalize => remove redundant slashes, etc.
            if os.path.isdir(folder):
                self.folderCombo.addItem(folder)
                folders_to_display.append(folder)
            else:
                self.errorSignal.emit(tools.ErrorMessages.WARNING, tr['WARNING_NONEXIST_MEDIALIB_PATH'], "")

        # set back previously selected (current) item in folderCombo if exists (may be deleted => set root folder)
        if current_folder_text in folders_to_display:
            self.folderCombo.setCurrentIndex(folders_to_display.index(current_folder_text))
            self.folderCombo.blockSignals(False)
        else:
            self.folderCombo.blockSignals(False)
            self.folderCombo.currentIndexChanged.emit(0)

    def loadSettings(self):
        """
        Method called on start to load and set stuff.
        Method is called directly, so no heavy operation is expected. (see loadSettingsQueued() for more info)
        """
        logger.debug("Global load settings called. Loading settings...")

        # restore window position
        settings = QSettings()
        windowGeometry = settings.value("gui/MainApp/geometry", None)
        if windowGeometry is not None:
            self.restoreGeometry(windowGeometry)
        splitterState = settings.value("gui/MainApp/splitter", None)
        if splitterState is not None:
            self.splitter.restoreState(splitterState)
        playlistHeaderState = settings.value("gui/MainApp/playlistHeader", None)
        if playlistHeaderState is not None:
            self.playlistTable.horizontalHeader().restoreState(playlistHeaderState)

        self.setupFileBrowser(initModel=True)

    @pyqtSlot()
    def loadSettingsQueued(self):
        """
        This method is called as slot directly from main thread, but few milliseconds queued,
        so Qt engine can render application.
        Method is delayed for 25ms. On average computer is this delay enough to fully render whole application,
        but almost unnoticeable.
        """
        self.loadSession()
        self.initFileBrowser()

    def loadSession(self):
        """
        Loads last session information
        e.g. last playlist, etc.
        """
        if not os.path.isfile(self.session_file):
            logger.debug("No session file found, skipping")
            return

        if not QSettings().value("session/saveRestoreSession", True, bool):
            logger.debug("Skipped session load, functionality disabled")
            return

        logger.debug("Loading session...")
        try:
            with open(self.session_file, 'r') as f:
                session_data = ujson.load(f)
        except Exception:
            logger.exception("Unable to load data from session file!")
        else:
            volume = session_data.get('volume', 100)
            self.volumeSlider.setValue(volume)
            self.mediaPlayer.setVolume(volume)
            self.volumeChanged(self.volumeSlider.value())

            # do not load playlist
            # if not program started with input path argument (i.e. user double clicked on .mp3 file and woofer opened)
            if not self.input_path:
                self.loadPlaylist(session_data)

                # load shuffle, repeat and volume
                self.mediaPlayer.shuffle_mode = session_data.get('shuffle', False)
                self.mediaPlayer.repeat_mode = session_data.get('repeat', False)
                self.shuffleBtn.blockSignals(True)
                self.shuffleBtn.setChecked(self.mediaPlayer.shuffle_mode)
                self.shuffleBtn.blockSignals(False)
                self.mediaShuffleAction.setChecked(self.mediaPlayer.shuffle_mode)
                self.repeatBtn.blockSignals(True)
                self.repeatBtn.setChecked(self.mediaPlayer.repeat_mode)
                self.repeatBtn.blockSignals(False)
                self.mediaRepeatAction.setChecked(self.mediaPlayer.repeat_mode)

            logger.debug("Session restored successfully")

    def loadPlaylist(self, session_data):
        """
        Loads and sets saved playlist from last session (from disk)
        @param session_data: data from disk are stored in this dict file
        """
        table_content = session_data.get('playlist_table', [])              # playlistTable content
        if not table_content:                                               # playlist is empty
            return

        n_cols = len(table_content)
        n_rows = len(table_content[0])
        if n_rows == 0:
            logger.debug("No playlist to restore")
            return

        paths_list = table_content[-1]

        logger.debug("Restoring items from playlist in playlistTable...")
        self.playlistTable.setRowCount(n_rows)
        self.playlistTable.setColumnCount(n_cols)

        column_with_path = self.playlistTable.columnCount() - 1
        for row in range(n_rows):
            for column in range(n_cols):
                cell_data = table_content[column][row]      # 2D array is saved as transposed
                if cell_data:       # empty or None cell -> skip
                    item = QTableWidgetItem(cell_data)
                    item.setToolTip(cell_data)
                    self.playlistTable.setItem(row, column, item)

                    # if given track doesn't exist, set whole row italic and gray
                    if column == column_with_path and not os.path.exists(cell_data):
                        for i in (0, 1, 2):        # title and duration items
                            title_item = self.playlistTable.item(row, i)
                            if title_item:          # could be None
                                font = title_item.font()
                                font.setItalic(True)
                                title_item.setFont(font)
                                title_item.setForeground(QBrush(Qt.gray))

        self.playlistTable.resizeColumnToContents(1)

        logger.debug("Restoring items from playlist in mediaPlayer object...")
        self.mediaPlayer.shuffled_playlist = session_data.get('shuffled_playlist', [])
        self.mediaPlayer.shuffled_playlist_current_index = session_data.get('shuffled_playlist_current_index', 0)

        if paths_list and len(self.mediaPlayer.shuffled_playlist) == len(paths_list):
            self.mediaPlayer.addMedia(paths_list, restoring_session=True)

            # set current media in table as current item and scroll to the item
            self.playlistTable.setCurrentCell(self.mediaPlayer.shuffled_playlist[self.mediaPlayer.shuffled_playlist_current_index], 0)
            self.playlistTable.scrollToItem(self.playlistTable.currentItem(), QAbstractItemView.PositionAtCenter)
        else:
            logger.error("Error when loading/restoring playlist: "
                         "paths_list and shuffled_playlist are not the same length")
            self.clearPlaylist()

    def saveSettings(self):
        """
        When program is about to close, all desired settings is saved.
        Called when dialog closeEvent in caught.
        """
        logger.debug("Global save settings called. Saving settings...")
        self.saveSession()
        self.mainTreeBrowser.saveSettings()

        # save window position
        settings = QSettings()
        settings.setValue("gui/MainApp/geometry", self.saveGeometry())
        settings.setValue("gui/MainApp/splitter", self.splitter.saveState())
        settings.setValue("gui/MainApp/playlistHeader", self.playlistTable.horizontalHeader().saveState())

    def saveSession(self):
        """
        Save current session information
        e.g. current playlist, etc.
        """
        if not QSettings().value("session/saveRestoreSession", True):
            logger.debug("Skipped session save, functionality disabled")
            return

        session_data = {}

        self.savePlaylist(session_data)

        session_data['shuffle'] = self.mediaPlayer.shuffle_mode
        session_data['repeat'] = self.mediaPlayer.repeat_mode
        session_data['volume'] = self.volumeSlider.value()

        logger.debug("Dumping session file to disk...")
        with open(self.session_file, 'w') as f:
            ujson.dump(session_data, f)

    def savePlaylist(self, session_data):
        """
        Dump information about playlist from playlist_table and from media_player
        @param session_data: all information are stored to this dict file
        """
        logger.debug("Dumping and saving playlist information...")

        n_cols = self.playlistTable.columnCount()
        n_rows = self.playlistTable.rowCount()

        n_shuf_play = len(self.mediaPlayer.shuffled_playlist)
        n_media_list = self.mediaPlayer._media_list.count()     # access to protected for sanity-check purposes only
        shuf_play_index = self.mediaPlayer.shuffled_playlist_current_index
        if (n_shuf_play == n_rows == n_media_list) and (shuf_play_index == 0 or 0 < shuf_play_index < n_shuf_play):
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
            session_data['shuffled_playlist'] = self.mediaPlayer.shuffled_playlist
            session_data['shuffled_playlist_current_index'] = self.mediaPlayer.shuffled_playlist_current_index

        else:
            # woofer may crash during some playlist operation, so records may be inconsistent
            logger.error("Playlist (gui) and _media_list are not are not the same length!")
            session_data['playlist_table'] = []
            session_data['shuffled_playlist'] = []
            session_data['shuffled_playlist_current_index'] = 0

    @pyqtSlot(str)
    def messageFromAnotherInstance(self, message):
        """
        Called when another instance of Woofer is opened.
        This instance finds out, that another instance is already running and sends its args to this instance.
        @param message: command with optional args
        @type message: str
        """
        logger.debug("Received message from another instance: %s", message)

        if message.startswith("play"):
            path = message.replace("play ", "")
            logger.error(path)
            logger.error(type(path))
            if os.path.exists(path):
                self.playPath(path, append=False)
            else:
                logger.error("From another instance received path which do not exist!")

        elif message.startswith("open"):
            logger.debug("Setting application window on top")
            if self.windowState() & Qt.WindowMinimized:         # if window is minimized -> un-minimize
                self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
            self.activateWindow()                               # set window as active with focus
            self.raise_()

    @pyqtSlot(QModelIndex)
    def fileBrowserActivated(self, modelIndex):
        """
        When media file browser is selected and user doubleclicks or hit enter in treeview,
        selected path will be played.
        @type modelIndex: QModelIndex
        """
        logger.debug("File (media) browser activated, now checking if activated index if file or folder...")

        # stop current media adding
        self.scanner.stop()
        self.parser.stop()
        n_tries = 300       # wait 3 sec
        while self.mediaPlayer.adding_media and (n_tries > 0):
            QCoreApplication.processEvents()        # to unfreeze gui
            self.thread().msleep(33)            # to get responsible look&feel
            n_tries -= 1

        if self.mediaPlayer.adding_media:
            logger.error("Media adding didn't stopped!")
            self.displayErrorMsg(tools.ErrorMessages.ERROR,
                                 "Can't add another media when media adding is already running", "")
            return

        self.scanner.init()     # reset _stop flags
        self.parser.init()

        fileInfo = self.fileBrowserModel.fileInfo(modelIndex)
        targetPath = fileInfo.absoluteFilePath()
        logger.debug("Initializing playing of path: %s", targetPath)
        self.mediaPlayer.clearMediaList()
        self.mediaPlayer.initMediaAdding(append=False)
        self.scanFilesSignal.emit(targetPath)                 # asynchronously recursively search for media files
        self.displayProgress(tr['PROGRESS_ADDING'])

    @pyqtSlot(QPoint)
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
        playNow = QAction(QIcon(":/icons/play-now.png"), tr['PLAY_NOW'], menu)
        addToPlayList = QAction(QIcon(":/icons/play-next.png"), tr['ADD_TO_PLAYLIST'], menu)
        playAll = QAction(QIcon(":/icons/play-now.png"), tr['PLAY_ALL'], menu)
        removeFromDisk = QAction(QIcon(":/icons/delete.png"), tr['REMOVE_FROM_DISK'], menu)
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
        choice = menu.exec_(self.mainTreeBrowser.viewport().mapToGlobal(pos))

        # PLAY NOW
        if choice is playNow:
            self.playPath(fileInfo.absoluteFilePath(), append=False)

        # PLAY ALL
        elif choice is playAll:
            self.playPath(fileInfo.absoluteFilePath(), append=False)

        # ADD TO PLAYLIST
        elif choice is addToPlayList:
            self.playPath(fileInfo.absoluteFilePath(), append=True)

        # REMOVE FROM DISK
        elif choice is removeFromDisk:
            path = fileInfo.absoluteFilePath()
            path = os.path.normpath(path)
            if path in self.mediaPlayer.media_list:
                # implicitly removes media from media player
                self.playlistRemFromDisk(self.mediaPlayer.media_list.index(path))
            else:
                logger.debug("Removing path '%s' to Trash", path)
                self.removeFileSignal.emit(path)

    @pyqtSlot(QPoint)
    def playlistContextMenu(self, pos):
        selected_rows = [sel_index.row() for sel_index in self.playlistTable.selectionModel().selectedRows()]
        if not selected_rows:
            return

        logger.debug("Opening playlist context menu.")
        menu = QMenu(self.playlistTable)
        playNowAction = QAction(QIcon(":/icons/play-now.png"), tr['PLAY_NOW'], menu)
        playNowAction.setShortcut(QKeySequence(Qt.Key_Enter))
        playNowAction.setEnabled(True if len(selected_rows) == 1 else False)
        remFromPlaylistAction = QAction(tr['REMOVE_FROM_PLAYLIST'], menu)
        remFromPlaylistAction.setShortcut(QKeySequence(Qt.Key_Delete))
        remFromDiskAction = QAction(QIcon(":/icons/delete.png"), tr['REMOVE_FROM_DISK'], menu)
        remFromDiskAction.setShortcut(QKeySequence(Qt.SHIFT + Qt.Key_Delete))
        separator = QAction(menu)
        separator.setSeparator(True)

        menu.addActions([playNowAction, separator])
        removeMenu = menu.addMenu(tr['REMOVE'])
        removeMenu.addActions([remFromPlaylistAction, remFromDiskAction])
        choice = menu.exec_(self.playlistTable.viewport().mapToGlobal(pos))

        if choice is playNowAction:
            self.playlistPlayNow(row=selected_rows[0])
        elif choice is remFromPlaylistAction:
            selected_rows = sorted(selected_rows, reverse=True)
            self.playlistRemFromPlaylist(selected_rows)
        elif choice is remFromDiskAction:
            selected_rows = sorted(selected_rows, reverse=True)
            self.playlistRemFromDisk(selected_rows)

    @pyqtSlot()
    def initFileBrowser(self):
        """
        Loads QT File browser to mainTreeBrowser widget.
        """
        self.mainTreeBrowser.setModel(self.fileBrowserModel)

        # hide unwanted columns
        for i in range(1, self.fileBrowserModel.columnCount()):
            self.mainTreeBrowser.setColumnHidden(i, True)

        # remember my_computer root index for the first time
        if self.myComputerPathIndex is None:
            self.myComputerPathIndex = self.mainTreeBrowser.rootIndex()
        if self.homeDirIndex is None:
            self.homeDirIndex = self.fileBrowserModel.index(QDir.homePath())

        self.mainTreeBrowser.restoreSettings()
        self.folderCombo.currentIndexChanged.emit(self.folderCombo.currentIndex())  # invoke refresh manually

    @pyqtSlot(int)
    def changeFileBrowserRoot(self, index):
        """
        When new folder from folderCombo is selected, update folder browser (sourceItemsBrowser)
        @type index: int
        """
        if index == -1:
            return          # ignore on reset

        newMediaFolder = self.folderCombo.currentText()

        if newMediaFolder == tr['MY_COMPUTER']:
            # display MyComputer folder (root on Linux)
            if self.myComputerPathIndex is not None:
                logger.debug("Changing file_browser root to 'My Computer/root'.")
                self.mainTreeBrowser.setRootIndex(self.myComputerPathIndex)
                self.fileBrowserModel.setRootPath(QDir.rootPath())
        elif newMediaFolder == tr['HOME_DIR']:
            # display home/user directory
            if self.homeDirIndex is not None:
                logger.debug("Changing file_browser root to 'home_dir'.")
                self.mainTreeBrowser.setRootIndex(self.homeDirIndex)
                self.fileBrowserModel.setRootPath(QDir.homePath())
        else:
            # if valid, display given folder as root
            folderIndex = self.fileBrowserModel.index(newMediaFolder)
            if folderIndex.row() != -1 and folderIndex.column() != -1:
                logger.debug("Changing file_browser root to '%s'.", newMediaFolder)
                self.mainTreeBrowser.setRootIndex(folderIndex)
                self.fileBrowserModel.setRootPath(newMediaFolder)
            else:
                logger.error("Media path from folderCombo could not be found in fileSystemModel!")
                self.errorSignal.emit(tools.ErrorMessages.ERROR, tr['ERROR_MEDIALIB_FOLDER_NOT_FOUND'] % newMediaFolder, "")
                self.folderCombo.removeItem(self.folderCombo.currentIndex())

    @pyqtSlot()
    def openLibraryDialog(self):
        """
        When library button is clicked, open library editor dialog.
        When dialog is closed, refresh media folders combobox.
        """
        libraryDialog = library_dialog.LibraryDialog(self.mediaLibFile, self)
        libraryDialog.finished.connect(self.setupFileBrowser)
        libraryDialog.exec_()

    def openSettingsDialog(self):
        settingsDialog = settings_dialog.SettingsDialog(self)
        # libraryDialog.finished.connect(self.setupFileBrowser)
        settingsDialog.exec_()

    @pyqtSlot(list, bool)
    def addToPlaylist(self, sources, append):
        """
        Sets and adds media files to playlist.
        @param sources: list of (path, duration)
        @type sources: list of (unicode, int)
        """
        lastItemIndex = self.playlistTable.rowCount() if append else 0
        self.playlistTable.setRowCount(lastItemIndex + len(sources))

        i = 0
        for path, duration in sources:
            titleItem = QTableWidgetItem(os.path.basename(path))
            titleItem.setToolTip(os.path.basename(path))
            folder = os.path.dirname(path)
            fname = os.path.basename(folder)
            if fname.strip().lower().startswith(("cd", "dvd")):
                parent_fname = os.path.basename(os.path.dirname(folder))
                fname = parent_fname + "/" + fname
            folderNameItem = QTableWidgetItem(fname)
            folderNameItem.setToolTip(fname)
            ttime = QTime(0, 0, 0, 0).addMSecs(duration).toString("hh:mm:ss")
            durationItem = QTableWidgetItem(ttime)
            durationItem.setToolTip(ttime)
            pathItem = QTableWidgetItem(path)
            self.playlistTable.setItem(i + lastItemIndex, 0, titleItem)
            self.playlistTable.setItem(i + lastItemIndex, 1, folderNameItem)
            self.playlistTable.setItem(i + lastItemIndex, 2, durationItem)
            self.playlistTable.setItem(i + lastItemIndex, 3, pathItem)
            i += 1

    @pyqtSlot()
    def clearPlaylist(self):
        logger.debug("Clear media playlist called")
        self.mediaPlayer.clearMediaList()

        self.playlistTable.clearContents()
        self.playlistTable.setRowCount(0)

    @pyqtSlot()
    def cancelAdding(self):
        logger.debug("Canceling adding new files to playlist (parsing).")
        self.scanner.stop()
        self.parser.stop()

    @pyqtSlot(int, str, str)
    def displayErrorMsg(self, er_type, text, details=" "):
        """
        Called to display warnings and errors.
        @param er_type: error type (Message enum)
        @param text: main text
        @param details: description
        """
        details = "Details: <i>" + details + "</i>" if details else ""

        if er_type == tools.ErrorMessages.INFO:
            icon = QPixmap(":/icons/info.png").scaled(14, 14, transformMode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.INFO_MSG_DELAY, self.clearErrorMsg)

        elif er_type == tools.ErrorMessages.WARNING:
            icon = QPixmap(":/icons/warning.png").scaled(14, 14, transformMode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.WARNING_MSG_DELAY, self.clearErrorMsg)

        elif er_type == tools.ErrorMessages.ERROR:
            icon = QPixmap(":/icons/error.png").scaled(16, 16, transformMode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.ERROR_MSG_DELAY, self.clearErrorMsg)
            QApplication.beep()

        elif er_type == tools.ErrorMessages.CRITICAL:
            msgBox = QMessageBox(self)
            horizontalSpacer = QSpacerItem(400, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
            layout = msgBox.layout()
            layout.addItem(horizontalSpacer, layout.rowCount(), 0, 1, layout.columnCount())
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle(tr['CRITICAL_ERROR'])
            msgBox.setText(text)
            msgBox.setInformativeText(details)
            msgBox.exec_()
            sys.exit(-1)

    @pyqtSlot()
    def displayVolumePopup(self):
        """
        Called when user clicks on volume button.
        Opens popup with mute button and volume slider
        """
        newPos = self.volumeBtn.pos()
        newPos = self.controlsFrame.mapToGlobal(newPos)
        newPos = newPos - QPoint(self.volumePopup.width()/2, self.volumePopup.height())

        self.volumePopup.move(newPos)
        self.volumePopup.show()

        self.volumePopup.activateWindow()
        self.volumePopup.setFocus()

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
        logger.debug("Media player playing.")
        icon = QIcon()
        icon.addPixmap(QPixmap(":/icons/media-pause.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)
        self.seekerSlider.setEnabled(True)
        self.mediaPlayPauseAction.setIcon(icon)
        self.mediaPlayPauseAction.setText(tr['PAUSE'])
        # reset the volume (volume level might be shared across libvlc library)
        self.mediaPlayer.setVolume(self.volumeSlider.value())

    @pyqtSlot()
    def paused(self):
        logger.debug("Media player paused.")
        icon = QIcon()
        icon.addPixmap(QPixmap(":/icons/media-play.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)
        self.mediaPlayPauseAction.setIcon(icon)
        self.mediaPlayPauseAction.setText(tr['PLAY'])

    @pyqtSlot()
    def stopped(self):
        logger.debug("Media player stopped.")
        self.paused()
        self.timeLbl.setText("00:00:00")
        self.seekerSlider.blockSignals(True)        # prevent syncing
        self.seekerSlider.setValue(0)
        self.seekerSlider.blockSignals(False)
        self.seekerSlider.setEnabled(False)

        icon = QIcon()
        icon.addPixmap(QPixmap(":/icons/media-play.png"), QIcon.Normal, QIcon.Off)
        self.playPauseBtn.setIcon(icon)
        self.mediaPlayPauseAction.setIcon(icon)
        self.mediaPlayPauseAction.setText(tr['PLAY'])

    @pyqtSlot(int)
    def syncPlayTime(self, value):
        """
        @param value: time in milliseconds
        @type value: int
        """
        self.timeLbl.setText(QTime(0, 0, 0, 0).addMSecs(value).toString("hh:mm:ss"))

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

    @pyqtSlot(int, int)
    def displayCurrentMedia(self, current_index, last_index):
        """
        When media is changed, select row corresponding with media.
        @param current_index: position of media in media_list == position in playlist table
        @type current_index: int
        @param last_index: previous position of media in media_list
        @type last_index: int
        """
        # remove icon from previous item (playlist row)
        last_item = self.playlistTable.item(last_index, 0)
        null_icon = QIcon()
        last_item.setIcon(null_icon)

        # set play icon to current item (current playlist row)
        self.playlistTable.setCurrentCell(current_index, 0)          # select the entire row due to table selection behaviour
        current_item = self.playlistTable.item(current_index, 0)
        current_item.setIcon(QIcon(QPixmap(":/icons/media-play.png")))

    @pyqtSlot()
    def playlistPlayNow(self, row=None, col=None):
        """
        Play song from playlist table immediately.
        @param row: song row number
        @param col: ignore - just slot requirement
        """
        index = self.playlistTable.currentRow() if row is None else row
        if index == -1:
            return

        fileName = os.path.basename(self.playlistTable.item(index, self.playlistTable.columnCount()-1).text())
        logger.debug("Play now called, playing #%s song from playlist named '%s'.", index, fileName)

        self.mediaPlayer.play(index)

    @pyqtSlot()
    def playlistRemFromPlaylist(self, rows=None):
        """
        Removes songs from playlist table and from player (media_list).
        @param rows: row numbers in playlist table
        """
        if rows is None:
            rows = [sel_index.row() for sel_index in self.playlistTable.selectionModel().selectedRows()]
            rows = sorted(rows, reverse=True)

        if not rows:
            return

        for row in rows:
            fileName = os.path.basename(self.playlistTable.item(row, self.playlistTable.columnCount()-1).text())
            logger.debug("Removing from playlist #%s song named '%s'", row, fileName)

            self.playlistTable.removeRow(row)
            self.mediaPlayer.removeItem(row)

    @pyqtSlot()
    def playlistRemFromDisk(self, rows=None):
        """
        Removes songs from playlist table, from player (media_list) and from disk if possible.
        @param rows: row numbers in playlist table
        """
        if rows is None:
            rows = [sel_index.row() for sel_index in self.playlistTable.selectionModel().selectedRows()]
            rows = sorted(rows, reverse=True)

        if not rows:
            return

        for row in rows:
            filePath = self.playlistTable.item(row, self.playlistTable.columnCount()-1).text()
            fileName = os.path.basename(filePath)
            self.playlistRemFromPlaylist((row,))

            logger.debug("Removing to Trash #%s song named '%s' on path '%s'", row, fileName, filePath)
            self.removeFileSignal.emit(filePath)

    def playPath(self, targetPath, append):
        """
        Initializes scanning, parsing and adding new media files from given path.
        @type targetPath: unicode
        @type append: bool
        """
        if not append:
            self.mediaPlayer.clearMediaList()

        self.mediaPlayer.initMediaAdding(append=append)
        self.scanFilesSignal.emit(targetPath)                 # asynchronously recursively search for media files
        self.displayProgress(tr['PROGRESS_ADDING'])

    @pyqtSlot(bool)
    def toggleShuffle(self, checked):
        self.mediaPlayer.setShuffle(checked)
        self.mediaShuffleAction.setChecked(checked)

    @pyqtSlot(bool)
    def toggleRepeat(self, checked):
        self.mediaPlayer.setRepeat(checked)
        self.mediaRepeatAction.setChecked(checked)

    @pyqtSlot(int)
    def volumeChanged(self, volume):
        """
        Called when volume has been changed to update volume button icon depending on volume value.
        @type volume: int
        """
        if volume == 0:
            self.volumePopup.muteBtn.setChecked(True)
        else:
            self.volumePopup.muteBtn.setChecked(False)

            if volume < 20:
                self.volumeBtn.setIcon(self.minVolumeIcon)
            elif volume < 40:
                self.volumeBtn.setIcon(self.lowVolumeIcon)
            elif volume < 80:
                self.volumeBtn.setIcon(self.mediumVolumeIcon)
            elif volume <= 100:
                self.volumeBtn.setIcon(self.maxVolumeIcon)
            else:
                color = QColor()
                color.setHsv((25-(volume-100)/2), 255, 255)
                color_mask = QPixmap(self.colorVolumePixmap.size())
                color_mask.fill(color)
                color_mask.setMask(self.colorVolumePixmap.createMaskFromColor(Qt.transparent))
                self.volumeBtn.setIcon(QIcon(color_mask))

    @pyqtSlot(bool)
    def muteStatusChanged(self, status):
        """
        Method called when mute button has been toggled to new value.
        Mute or un-mute audio playback.
        @type status: bool
        """
        self.mediaPlayer.setMute(status)

        if status:
            logger.debug("Mute button checked, MUTING audio...")
            self.volumeBtn.setIcon(QIcon(QPixmap(":/icons/mute.png")))
            self.oldVolumeValue = self.volumeSlider.value()
            self.volumeSlider.blockSignals(True)
            self.volumeSlider.setValue(0)
            self.volumeSlider.blockSignals(False)

            self.mediaMuteAction.setText(tr['UNMUTE'])
            self.mediaMuteAction.setIcon(QIcon(QPixmap(":/icons/volume-max.png")))
        else:
            logger.debug("Mute button checked, UN-MUTING audio...")

            if not self.oldVolumeValue:
                self.oldVolumeValue = 20
                self.volumeSlider.setValue(self.oldVolumeValue)
            else:
                self.volumeSlider.blockSignals(True)
                self.volumeSlider.setValue(self.oldVolumeValue)
                self.volumeSlider.blockSignals(False)
                self.volumeChanged(self.oldVolumeValue)

            self.mediaMuteAction.setText(tr['MUTE'])
            self.mediaMuteAction.setIcon(QIcon(QPixmap(":/icons/mute.png")))

    @pyqtSlot()
    def openAboutDialog(self):


        def find_licence_file():
            if os.path.isfile('LICENSE.txt'):
                path_to_licence = tools.APP_ROOT_DIR
                path_to_licence = path_to_licence.split(os.sep)
                path_to_licence = "/".join(path_to_licence) + "/LICENSE.txt"
                path_to_licence = "file:///" + path_to_licence
            else:
                logger.error("LICENSE.txt file was not found in woofer root dir!")
                path_to_licence = "http://www.gnu.org/licenses/gpl-3.0.txt"

            return path_to_licence

        logger.debug("Open 'About' dialog called")
        path_to_licence = find_licence_file()
        build_data = tools.loadBuildInfo()

        author = build_data.get('author')
        email = build_data.get('email')
        videolan_url = "http://www.videolan.org/index.cs.html"
        woofer_url = "http://m1lhaus.github.io/woofer"
        github_url = "https://github.com/m1lhaus/woofer"
        maintext = "Woofer player is <strong>free and open-source cross-platform</strong> music player " \
                   "that plays most multimedia files, CDs and DVDs. " \
                   "Whole written in Python and Qt provides easy, reliable, " \
                   "and high quality playback thanks to LibVLC library developed by " \
                   "<a href='{0}'>VideoLAN community</a>.<br/>" \
                   "<br/>" \
                   "Created by: {4} &lt; {5} &gt;<br/>" \
                   "Web: <a href='{1}'>m1lhaus.github.io/woofer</a><br/>" \
                   "Source: <a href='{2}'>GitHub repository</a> &lt; <a href='{3}'>LICENCE GPL v3</a> &gt;".format(
                   videolan_url, woofer_url, github_url, path_to_licence, author, email)

        maintextLabel = QLabel()
        maintextLabel.setTextFormat(Qt.RichText)
        maintextLabel.setOpenExternalLinks(True)
        maintextLabel.setWordWrap(True)
        maintextLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        maintextLabel.setText(maintext)

        iconLabel = QLabel()
        iconLabel.setPixmap(QPixmap(":/icons/app_icon.png").scaled(128, 128, transformMode=Qt.SmoothTransformation))
        iconLabel.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        maintextLayout = QHBoxLayout()
        maintextLayout.addWidget(iconLabel)
        maintextLayout.addWidget(maintextLabel)

        # ------------------------------

        from components import libvlc
        libvlc_version = libvlc.bytes_to_str(libvlc.libvlc_get_version())
        pyversion = "%s.%s.%s" % (sys.version_info[0], sys.version_info[1], sys.version_info[2])
        version = "%s.r%s" % (build_data.get('version'), build_data.get('commits'))
        rev = build_data.get('revision')
        build_date = build_data.get('date')
        platform_str = "x86" if tools.getPlatformArchitecture() == 32 else "x64"
        detailtext = "<hr><br/>" \
                     "<strong>Build information:</strong><br/>" \
                     "Version: {4} | Revision: {5} | Build date: {6}<br />" \
                     "Python: {0} {7} | PyQt: {1} | Qt: {2} | LibVLC version: {3}".format(
                     pyversion, PYQT_VERSION_STR, QT_VERSION_STR, libvlc_version, version, rev, build_date, platform_str)

        detailtextLabel = QLabel()
        detailtextLabel.setTextFormat(Qt.RichText)
        detailtextLabel.setOpenExternalLinks(True)
        detailtextLabel.setWordWrap(True)
        detailtextLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        detailtextLabel.setText(detailtext)

        detailtextLayout = QVBoxLayout()
        detailtextLayout.addWidget(detailtextLabel)

        # ------------------------------

        aboutDialog = QDialog(self)
        aboutDialog.setWindowFlags(aboutDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        aboutDialog.setWindowTitle(tr['ABOUT_WOOFER'])

        topLayout = QVBoxLayout()
        topLayout.setContentsMargins(15, 15, 15, 15)
        topLayout.addLayout(maintextLayout)
        topLayout.addLayout(detailtextLayout)
        aboutDialog.setLayout(topLayout)

        aboutDialog.setFixedWidth(550)
        aboutDialog.setFixedHeight(aboutDialog.sizeHint().height())
        aboutDialog.exec_()
        logger.debug("'About' dialog closed")

    @pyqtSlot(int)
    def startDownloadingUpdate(self, total_size):
        """
        Called by scheduler/updater when the updater starts downloading data from the internet.
        Method displays 'progress' animation (QLabel) in status bar.
        Real download progress is being display in QLabel tooltip.
        @param total_size: total size of the file/package
        """
        logger.debug("Updater started, initializing GUI download status")
        if self.downloadUpdateBtn and self.availableUpdateLabel:
            self.statusbar.removeWidget(self.downloadUpdateBtn)
            self.statusbar.removeWidget(self.availableUpdateLabel)

        self.downloadStatusLabel = QLabel(self)
        self.downloadAnimation = QMovie(":/icons/loading.gif", parent=self)

        self.downloadStatusLabel.setMinimumWidth(24)
        self.downloadStatusLabel.setToolTip(tr['PROGRESS_DOWNLOADING_UPDATE'] + ": 0 B / " + str(total_size))
        self.downloadStatusLabel.setMovie(self.downloadAnimation)
        self.statusbar.addPermanentWidget(self.downloadStatusLabel)
        self.downloadAnimation.start()

        self.errorSignal.emit(tools.ErrorMessages.INFO, tr['INFO_DOWNLOADING_UPDATE'], "")

    @pyqtSlot(int, int)
    def updateDownloaderStatus(self, already_down, total_size):
        """
        Called from scheduler/updater whenever one percent of the file is downloaded.
        Method will display progress in 'downloadStatusLabel'.
        """
        self.downloadStatusLabel.setToolTip(tr['PROGRESS_DOWNLOADING_UPDATE'] + ": " + str(already_down) + " / " + str(total_size))

    @pyqtSlot(int, str)
    def endDownloadingUpdate(self, status, filepath):
        """
        Called from scheduler/updater when downloading is finished to remove progress label from status bar.
        """
        logger.debug("Updater finished, updating GUI download status")
        if status == components.network.Downloader.COMPLETED:
            self.downloadStatusLabel.setToolTip(tr['PROGRESS_DOWNLOADING_FINISHED'])
            self.downloadAnimation.stop()
            self.statusbar.removeWidget(self.downloadStatusLabel)
        else:
            pass

    @pyqtSlot(str, int)
    def displayAvailableUpdates(self, version, total_size):
        """
        Display information about newer version is beeing available in statusbar.
        Version and total download size is displayed.
        @type version: unicode
        @type total_size: int
        """
        logger.debug("Displaying info about available application update")

        self.availableUpdateLabel = QLabel(tr['NEW_VERSION_AVAILABLE'], self)
        self.availableUpdateLabel.setToolTip(tr['UPDATER_TOOLTIP'] % (version, total_size))
        self.downloadUpdateBtn = QPushButton(self)
        self.downloadUpdateBtn.setIcon(QIcon(QPixmap(":/icons/download.png")))
        self.downloadUpdateBtn.setFlat(True)
        self.downloadUpdateBtn.setToolTip(tr['DOWNLOAD_AND_INSTALL'])

        # when user hits download button, downloader thread will start downloading update package
        self.downloadUpdateBtn.clicked.connect(self.updater.downloadUpdatePackage)

        self.statusbar.addPermanentWidget(self.availableUpdateLabel)
        self.statusbar.addPermanentWidget(self.downloadUpdateBtn)

    @pyqtSlot(str)
    def prepareForAppUpdate(self, filepath):
        """
        Called from scheduler when ZIP file is checked (CRC check) to prepare the 'update on restart' procedure.
        @param filepath: path to downloaded package
        """
        logger.debug("Preparing for update on restart")

        self.updateOnExit = True
        self.updateExe = filepath

        self.updateAppBtn = QPushButton(self)
        self.updateAppBtn.setIcon(QIcon(QPixmap(":/icons/update.png")))
        self.updateAppBtn.setFlat(True)
        self.updateAppBtn.setText(tr['UPDATE_AND_RESTART'])
        self.updateAppBtn.setLayoutDirection(Qt.RightToLeft)
        self.updateAppBtn.clicked.connect(self.updateAndRestart)
        self.statusbar.addPermanentWidget(self.updateAppBtn)

        self.errorSignal.emit(tools.ErrorMessages.INFO, tr['INFO_DOWNLOADING_FINISHED'], "")

    @pyqtSlot()
    def updateAndRestart(self):
        """
        Called as slot by "Update and restart" button in statusbar.
        """
        self.restartAfterUpdate = True
        self.close()

    def closeEvent(self, event):
        """
        Method called when close event caught.
        Quits all threads, saves settings, etc. before application exit.
        :type event: QCloseEvent
        """
        self.hkHook.stop_listening()    # stop hotkey listener
        self.updater.stop()             # stop downloading if any
        self.scanner.stop()             # stop hard disk browsing
        self.parser.stop()              # stop media parsing
        self.logCleaner.stop()          # stop scheduled timer or file listing/removing
        self.fileRemover.stop()         # nothing here
        self.mediaPlayer.quit()         # stop media player playback (libvlc)

        self.saveSettings()             # save session and app configuration

        self.thread().msleep(100)

        self.scannerThread.quit()
        self.parserThread.quit()
        self.logCleanerThread.quit()
        self.fileRemoverThread.quit()
        self.hkHookThread.quit()
        self.updaterThread.quit()

        self.scannerThread.wait(self.TERMINATE_DELAY)
        self.parserThread.wait(self.TERMINATE_DELAY)
        self.logCleanerThread.wait(self.TERMINATE_DELAY)
        self.fileRemoverThread.wait(self.TERMINATE_DELAY)
        self.hkHookThread.wait(self.TERMINATE_DELAY)
        self.updaterThread.wait(self.TERMINATE_DELAY)

        if self.hkHookThread.isRunning():
            logger.error("hkHookThread still running after timeout! Thread will be terminated.")
            self.hkHookThread.terminate()

        if self.updateOnExit:
            if os.path.isfile(self.updateExe):
                command = ["start", self.updateExe, tools.APP_ROOT_DIR, str(os.getpid())]
                if self.restartAfterUpdate:
                    command.append('-r')

                logger.debug("Launching updater script, command: %s", " ".join(command))
                subprocess.call(command, shell=True, close_fds=True)
            else:
                logger.error("Unable to locate Woofer updater launcher at '%s'!", self.updateExe)

        self.playlistTable.clear()  # fixes Python crashing on exit (no one knows why)
        event.accept()              # emits quit events
