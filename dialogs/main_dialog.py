# -*- coding: utf-8 -*-

"""
Main application GUI module.
"""

import logging
import pickle
import sys
import os
import errno
import json

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from forms import main_form
from dialogs import library_dialog
from components import disk,  media, scheduler
from tools import ErrorMessages, PlaybackSources

if os.name == "nt":
    from components import winkeyhook as keyhook
elif os.name == "posix":
    from components import xkeyhook as keyhook


logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)

# all supported codecs and formats can be found at https://wiki.videolan.org/VLC_Features_Formats/
FileExt = ('*.3ga', '*.669', '*.a52', '*.aac', '*.ac3', '*.adt', '*.adts', '*.aif', '*.aifc', '*.aiff', '*.amr', '*.aob',
           '*.ape', '*.awb', '*.caf', '*.dts', '*.flac', '*.it', '*.kar', '*.m4a', '*.m4p', '*.m5p', '*.mid', '*.mka',
           '*.mlp', '*.mod', '*.mpa', '*.mp1', '*.mp2', '*.mp3', '*.mpc', '*.mpga', '*.oga', '*.ogg', '*.oma',
           '*.opus', '*.qcp', '*.ra', '*.rmi', '*.s3m', '*.spx', '*.thd', '*.tta', '*.voc', '*.vqf', '*.w64',
           '*.wav', '*.wma', '*.wv', '*.xa', '*.xm')
FileExt_ = ('.3ga', '.669', '.a52', '.aac', '.ac3', '.adt', '.adts', '.aif', '.aifc', '.aiff', '.amr',
            '.aob', '.ape', '.awb', '.caf', '.dts', '.flac', '.it', '.kar', '.m4a', '.m4p', '.m5p',
            '.mid', '.mka', '.mlp', '.mod', '.mpa', '.mp1', '.mp2', '.mp3', '.mpc', '.mpga', '.oga',
            '.ogg', '.oma', '.opus', '.qcp', '.ra', '.rmi', '.s3m', '.spx', '.thd', '.tta', '.voc',
            '.vqf', '.w64', '.wav', '.wma', '.wv', '.xa', '.xm')


class MainApp(QMainWindow, main_form.MainForm):
    """
    Main application GUI form.
    - setup main window dialog
    - connects signals from dialogs widgets
    """

    errorSignal = pyqtSignal(int, unicode, unicode)        # (tools.Message.CRITICAL, main_text, description)
    removeFileSignal = pyqtSignal(unicode)
    scanFilesSignal = pyqtSignal(unicode)

    myComputerPathIndex = None
    oldVolumeValue = 0

    INFO_MSG_DELAY = 5000
    WARNING_MSG_DELAY = 10000
    ERROR_MSG_DELAY = 20000
    QUEUED_SETTINGS_DELAY = 100

    def __init__(self):
        super(MainApp, self).__init__()
        self.appRootPath = unicode(os.path.dirname(sys.argv[0]), sys.getfilesystemencoding())
        self.appDataPath = os.path.join(self.appRootPath, u'data')
        self.mediaLibFile = os.path.join(self.appDataPath, u'medialib.json')
        self.session_file = os.path.join(self.appDataPath, u'session.dat')

        self.mediaPlayer = media.MediaPlayer()

        # setups all GUI components from form (design part)
        self.setupUi(self)
        self.setupGUISignals()
        self.setupPlayerSignals()
        self.setupActionsSignals()

        # check if all needed folders and files are ready and writable
        self.checkPaths()

        # create all components in their independent threads
        self.setupDiskTools()
        self.setupSystemHook()
        self.setupScheduledTasks()

        # restore session/settings
        self.loadSettings()
        QTimer.singleShot(self.QUEUED_SETTINGS_DELAY, self.loadSettingsQueued)

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
        self.playlistTable.cellDoubleClicked.connect(self.playlistPlayNow)
        self.progressCancelBtn.clicked.connect(self.cancelAdding)
        # self.mainTreeBrowser.doubleClicked.connect(self.sourceItemsBrowserDoubleClicked)
        self.mainTreeBrowser.activated.connect(self.sourceItemsBrowserActivated)

        self.errorSignal.connect(self.displayErrorMsg)

        self.playPauseBtn.clicked.connect(self.mediaPlayer.playPause)
        self.stopBtn.clicked.connect(self.mediaPlayer.stop)
        self.nextBtn.clicked.connect(self.mediaPlayer.next)
        self.previousBtn.clicked.connect(self.mediaPlayer.prev)
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
        self.mediaNextAction.triggered.connect(self.mediaPlayer.next)
        self.mediaPreviousAction.triggered.connect(self.mediaPlayer.prev)
        self.mediaShuffleAction.triggered.connect(self.shuffleBtn.toggle)
        self.mediaRepeatAction.triggered.connect(self.repeatBtn.toggle)
        self.mediaMuteAction.triggered.connect(self.muteBtn.toggle)
        self.mediaQuitAction.triggered.connect(self.close)

        self.playlistClearAction.triggered.connect(self.clearPlaylist)

        self.helpAboutAction.triggered.connect(self.openAboutDialog)

    def setupSystemHook(self):
        """
        Initializes system-wide keyboard hook, which listens for media control keys (Media_Play_Pause,
        Media_Stop, Media_Next_Track, Media_Prev_Track).
        Listener is executed in separated thread (thread clocking method).
        Caught keys are mapped to signal and then forwarded to menubar actions.
        """
        self.hkHookThread = QThread(self)

        if os.name == 'nt' and not keyhook.GlobalHKListener.isAbleToRegisterHK():
            logger.warning(u"Unable to use win32 RegisterHotKey() function, "
                           u"switching to backup solution - registering Windows hook.")
            self.hkHook = keyhook.WindowsKeyHook()
        else:
            self.hkHook = keyhook.GlobalHKListener()

        self.hkHook.moveToThread(self.hkHookThread)
        self.hkHook.mediaPlayKeyPressed.connect(self.mediaPlayPauseAction.trigger)
        self.hkHook.mediaStopKeyPressed.connect(self.mediaStopAction.trigger)
        self.hkHook.mediaNextTrackKeyPressed.connect(self.mediaNextAction.trigger)
        self.hkHook.mediaPrevTrackKeyPressed.connect(self.mediaPreviousAction.trigger)

        self.hkHookThread.started.connect(self.hkHook.start_listening)
        self.hkHookThread.start()

    def setupPlayerSignals(self):
        """
        Initializes VLC based media player.
        Player class (basically it is only the interface) lives in main thread.
        VlC player itself lives in separated threads!
        """


        self.mediaPlayer.mediaAdded.connect(self.addToPlaylist)
        self.mediaPlayer.playing.connect(self.playing)
        self.mediaPlayer.paused.connect(self.paused)
        self.mediaPlayer.stopped.connect(self.stopped)
        self.mediaPlayer.timeChanged.connect(self.syncPlayTime)
        self.mediaPlayer.positionChanged.connect(self.syncSeeker)
        self.mediaPlayer.mediaChanged.connect(self.displayCurrentMedia)
        self.mediaPlayer.errorEncountered.connect(self.displayErrorMsg)

    def setupDiskTools(self):
        """
        Setup classes for disk digging (media searching) and asynchronous parsing.
        Scanner and parser live in separated threads.
        """
        # asynchronous scanner
        self.scanner = disk.RecursiveBrowser(nameFilter=FileExt_, followSym=False)
        self.scannerThread = QThread(self)

        # asynchronous parser
        self.parser = media.MediaParser()
        self.parserThread = QThread(self)

        self.fileRemover = disk.MoveToTrash()
        self.fileRemoverThread = QThread(self)

        self.scanFilesSignal.connect(self.scanner.scanFiles)
        self.parser.finished.connect(self.clearProgress)
        self.parser.finished.connect(self.mediaPlayer.mediaAddingFinished)
        self.parser.parsed.connect(self.mediaPlayer.addMedia)
        self.scanner.parseData.connect(self.parser.parseMedia)
        self.removeFileSignal.connect(self.fileRemover.remove)
        self.fileRemover.finished.connect(self.displayErrorMsg)
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
        self.logCleaner = scheduler.LogCleaner()
        self.logCleanerThread = QThread(self)
        self.logCleanerThread.started.connect(self.logCleaner.start)
        self.logCleaner.moveToThread(self.logCleanerThread)

        self.logCleanerThread.start()

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
                self.errorSignal.emit(ErrorMessages.CRITICAL, u"Unable to create data folder.",
                                      u"Error number: %s\n"
                                      u"%s" % (exception.errno, unicode(exception.strerror, "utf-8")))
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
                    self.errorSignal.emit(ErrorMessages.CRITICAL,
                                          u"Unable to create medialib file and write default data.",
                                          u"Error number: %s\n"
                                          u"%s" % (exception.errno, unicode(exception.strerror, "utf-8")))
                else:
                    logger.debug(u"Media file has been created and initialized.")
            else:
                logger.exception(u"Error when reading medialib file.")
                self.errorSignal.emit(ErrorMessages.CRITICAL, u"Unable to open and read medialib file.",
                                      u"Error number: %s\n"
                                      u"%s" % (exception.errno, unicode(exception.strerror, "utf-8")))

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
            self.errorSignal.emit(ErrorMessages.CRITICAL, u"Unable to open and read medialib file.",
                                                         u"Error number: %s\n"
                                                         u"%s" % (exception.errno, exception.strerror))
            raise
        except ValueError, exception:
            logger.exception(u"Unable to load and parse data from JSON file.")
            self.errorSignal.emit(ErrorMessages.CRITICAL, u"Unable to load and parse data from medialib file.",
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
                self.errorSignal.emit(ErrorMessages.WARNING, u"Some folders in media library don't exist.", u"")

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

    def loadSettings(self):
        """
        Method called on start to load and set stuff.
        Method is called directly, so no heavy operation is expected. (see loadSettingsQueued() for more info)
        """
        logger.debug(u"Global load settings called. Loading settings...")

        # restore window position
        settings = QSettings()
        windowGeometry = settings.value(u"gui/MainApp/geometry")
        if windowGeometry:
            self.restoreGeometry(windowGeometry)

        self.setupFileBrowser(initModel=True)       # todo: future: set dynamically (from last session)

    @pyqtSlot()
    def loadSettingsQueued(self):
        """
        This method is called as slot directly from main thread, but few milliseconds queued,
        so Qt engine can render application.
        Method is delayed for 25ms. On average computer is this delay enough to fully render whole application,
        but almost unnoticeable.
        """
        self.loadSession()
        self.changeSource(PlaybackSources.FILES)

    def loadSession(self):
        """
        Loads last session information
        e.g. last playlist, etc.
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
            self.shuffleBtn.blockSignals(True)
            self.shuffleBtn.setChecked(self.mediaPlayer.shuffle_mode)
            self.shuffleBtn.blockSignals(False)
            self.mediaShuffleAction.setChecked(self.mediaPlayer.shuffle_mode)
            self.repeatBtn.blockSignals(True)
            self.repeatBtn.setChecked(self.mediaPlayer.repeat_mode)
            self.repeatBtn.blockSignals(False)
            self.mediaRepeatAction.setChecked(self.mediaPlayer.repeat_mode)

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
        self.mediaPlayer.shuffled_playlist = session_data['id_playlist']
        self.mediaPlayer.shuffled_playlist_current_index = session_data['playlist_pointer']
        # self.mediaPlayer.playlist_len = len(self.mediaPlayer.shuffled_playlist)

        if paths_list:
            self.mediaPlayer.addMedia(paths_list, restoring_session=True)

            # set current media in table as current item and scroll to the item
            self.playlistTable.setCurrentCell(self.mediaPlayer.shuffled_playlist[self.mediaPlayer.shuffled_playlist_current_index], 0)
            self.playlistTable.scrollToItem(self.playlistTable.currentItem(), QAbstractItemView.PositionAtCenter)

    def saveSettings(self):
        """
        When program is about to close, all desired settings is saved.
        Called when dialog closeEvent in caught.
        """
        logger.debug(u"Global save settings called. Saving settings...")
        self.saveSession()
        self.mainTreeBrowser.saveSettings()

        # save window position
        settings = QSettings()
        settings.setValue(u"gui/MainApp/geometry", self.saveGeometry())
        settings.setValue(u"gui/MainApp/state", self.saveState())

    def saveSession(self):
        """
        Save current session information
        e.g. current playlist, etc.
        """
        session_data = {}

        self.savePlaylist(session_data)

        session_data['shuffle'] = self.mediaPlayer.shuffle_mode
        session_data['repeat'] = self.mediaPlayer.repeat_mode

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
        session_data['id_playlist'] = self.mediaPlayer.shuffled_playlist
        session_data['playlist_pointer'] = self.mediaPlayer.shuffled_playlist_current_index
        # session_data['playlist_len'] = len(self.mediaPlayer.shuffled_playlist)

    @pyqtSlot('QModelIndex')
    def sourceItemsBrowserActivated(self, index):
        if self.sourceType == PlaybackSources.FILES:
            self.fileBrowserActivated(index)
        if self.sourceType == PlaybackSources.PLAYLISTS:
            pass
        if self.sourceType == PlaybackSources.RADIO:
            pass

    def fileBrowserActivated(self, modelIndex):
        """
        When media file browser is selected and user doubleclicks or hit enter in treeview,
        selected path will be played.
        @type modelIndex: QModelIndex
        """
        logger.debug(u"File (media) browser activated, now checking if activated index if file or folder...")

        fileInfo = self.fileBrowserModel.fileInfo(modelIndex)
        targetPath = fileInfo.absoluteFilePath()
        logger.debug(u"Initializing playing of path: %s", targetPath)
        self.mediaPlayer.clearMediaList()
        self.mediaPlayer.initMediaAdding(append=False)
        self.scanFilesSignal.emit(targetPath)                 # asynchronously recursively search for media files
        self.displayProgress(u"Adding...")

    @pyqtSlot('QPointF')
    def sourceItemsBrowserContextMenu(self, pos):
        """
        SourceItemsBrowser treeView context menu method.
        Method creates context menu depending on source type (files, playlist, radios).
        @type pos: QPointF
        """

        logger.debug(u"Browser context menu called. Choosing appropriate context menu...")

        if self.sourceType == PlaybackSources.FILES:
            self.fileBrowserContextMenu(pos)

        if self.sourceType == PlaybackSources.PLAYLISTS:
            logger.debug(u"Opening playlist browser context menu.")

        if self.sourceType == PlaybackSources.RADIO:
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
            self.scanFilesSignal.emit(targetPath)                 # asynchronously recursively search for media files
            self.displayProgress(u"Adding...")

        # PLAY ALL
        elif choice is playAll:
            self.mediaPlayer.clearMediaList()
            self.mediaPlayer.initMediaAdding(append=False)
            targetPath = fileInfo.absoluteFilePath()
            self.scanFilesSignal.emit(targetPath)                 # asynchronously recursively search for media files
            self.displayProgress(u"Adding...")

        # ADD TO PLAYLIST
        elif choice is addToPlayList:
            targetPath = fileInfo.absoluteFilePath()
            self.mediaPlayer.initMediaAdding(append=True)
            # asynchronously recursively search for media files
            self.scanFilesSignal.emit(targetPath)
            self.displayProgress(u"Adding...")

        # REMOVE FROM DISK
        elif choice is removeFromDisk:
            path = fileInfo.absoluteFilePath()
            logger.debug(u"Removing path '%s' to Trash", path)
            self.removeFileSignal.emit(path)

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
            self.playlistPlayNow(index)
        elif choice is remFromPlaylistAction:
            self.playlistRemFromPlaylist(index)
        elif choice is remFromDiskAction:
            self.playlistRemFromDisk(index)

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

        if source_id == PlaybackSources.FILES:
            self.sourceType = PlaybackSources.FILES
            self.mainTreeBrowser.setMode(PlaybackSources.FILES)
            self.mainTreeBrowser.setModel(self.fileBrowserModel)

            # hide unwanted columns
            for i in range(1, self.fileBrowserModel.columnCount()):
                self.mainTreeBrowser.setColumnHidden(i, True)

            # remember my_computer root index for the first time
            if self.myComputerPathIndex is None:
                self.myComputerPathIndex = self.mainTreeBrowser.rootIndex()

            self.mainTreeBrowser.restoreSettings()

            logger.debug(u"Browser source has been selected to FILES.")

        elif source_id == PlaybackSources.PLAYLISTS:
            self.sourceType = PlaybackSources.PLAYLISTS
            self.mainTreeBrowser.setMode(PlaybackSources.FILES)
            logger.debug(u"Browser source has been selected to PLAYLISTS.")
            logger.warning(u"PLAYLISTS NOT IMPLEMENTED!")

        elif source_id == PlaybackSources.RADIO:
            self.sourceType = PlaybackSources.RADIO
            self.mainTreeBrowser.setMode(PlaybackSources.FILES)
            logger.debug(u"Browser source has been selected to RADIOS.")
            logger.warning(u"RADIOS NOT IMPLEMENTED!")

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
                self.errorSignal.emit(ErrorMessages.ERROR, u"Media folder '%s' could not be found!" % newMediaFolder, u"")
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
    def clearPlaylist(self):
        logger.debug(u"Clear media playlist called")
        self.mediaPlayer.clearMediaList()

        self.playlistTable.clearContents()
        self.playlistTable.setRowCount(0)

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
        if er_type == ErrorMessages.INFO:
            icon = QPixmap(u":/icons/info.png").scaled(14, 14, transformMode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + u' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.INFO_MSG_DELAY, self.clearErrorMsg)

        elif er_type == ErrorMessages.WARNING:
            icon = QPixmap(u":/icons/warning.png").scaled(14, 14, transformMode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.WARNING_MSG_DELAY, self.clearErrorMsg)

        elif er_type == ErrorMessages.ERROR:
            icon = QPixmap(u":/icons/error.png").scaled(16, 16, transformMode=Qt.SmoothTransformation)
            self.stBarMsgIcon.setPixmap(icon)
            self.stBarMsgText.setText(text + ' ' + details)
            self.stBarMsgIcon.show()
            self.stBarMsgText.show()
            QTimer.singleShot(self.ERROR_MSG_DELAY, self.clearErrorMsg)
            QApplication.beep()

        elif er_type == ErrorMessages.CRITICAL:
            msgBox = QMessageBox(self)
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle(u"Critical error")
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

    @pyqtSlot(int)
    def displayCurrentMedia(self, index):
        """
        When media is changed, select row corresponding with media.
        @param index: position of media in media_list == position in playlist table
        @type index: int
        """
        self.playlistTable.setCurrentCell(index, 0)          # select the entire row due to table selection behaviour

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
        logger.debug(u"Play now called, playing #%s song from playlist named '%s'.", index, fileName)

        self.mediaPlayer.play(index)

    @pyqtSlot()
    def playlistRemFromPlaylist(self, row=None):
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
    def playlistRemFromDisk(self, row=None):
        """
        Removes song from playlist table, from player (media_list) and from disk if possible.
        @param row: row number in playlist table
        """
        index = self.playlistTable.currentRow() if row is None else row
        if index == -1:
            return

        filePath = self.playlistTable.item(index, self.playlistTable.columnCount()-1).text()
        fileName = os.path.basename(filePath)
        self.playlistRemFromPlaylist(index)

        logger.debug(u"Removing to Trash #%s song named '%s' on path '%s'", index, fileName, filePath)
        self.removeFileSignal.emit(filePath)

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
                self.volumeBtn.setIcon(QIcon(QPixmap(u":/icons/volume-min.png")))
            elif volume < 40:
                self.volumeBtn.setIcon(QIcon(QPixmap(u":/icons/volume-low.png")))
            elif volume < 80:
                self.volumeBtn.setIcon(QIcon(QPixmap(u":/icons/volume-medium.png")))
            else:
                self.volumeBtn.setIcon(QIcon(QPixmap(u":/icons/volume-max.png")))

    @pyqtSlot(bool)
    def muteStatusChanged(self, status):
        """
        Method called when mute button has been toggled to new value.
        Mute or un-mute audio playback.
        @type status: bool
        """
        self.mediaPlayer.setMute(status)

        if status:
            logger.debug(u"Mute button checked, MUTING audio...")
            self.volumeBtn.setIcon(QIcon(QPixmap(u":/icons/mute.png")))
            self.oldVolumeValue = self.volumeSlider.value()
            self.volumeSlider.blockSignals(True)
            self.volumeSlider.setValue(0)
            self.volumeSlider.blockSignals(False)

            self.mediaMuteAction.setText(u"Unmute")
            self.mediaMuteAction.setIcon(QIcon(QPixmap(u":/icons/volume-max.png")))
        else:
            logger.debug(u"Mute button checked, UN-MUTING audio...")

            if not self.oldVolumeValue:
                self.oldVolumeValue = 20
                self.volumeSlider.setValue(self.oldVolumeValue)
            else:
                self.volumeSlider.blockSignals(True)
                self.volumeSlider.setValue(self.oldVolumeValue)
                self.volumeSlider.blockSignals(False)
                self.volumeChanged(self.oldVolumeValue)

            self.mediaMuteAction.setText(u"Mute")
            self.mediaMuteAction.setIcon(QIcon(QPixmap(u":/icons/mute.png")))

    @pyqtSlot()
    def openAboutDialog(self):
        logger.debug(u"Opening 'About' dialog")
        aboutDialog = QDialog(self)
        aboutDialog.setWindowFlags(aboutDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        aboutDialog.setWindowTitle(u"About Woofer player")

        layout = QHBoxLayout()
        layout.setMargin(20)

        if os.path.isfile(u'LICENSE.txt'):
            path_to_licence = unicode(os.path.dirname(os.path.realpath(sys.argv[0])), sys.getfilesystemencoding())
            path_to_licence = path_to_licence.split(os.sep)
            path_to_licence = u"/".join(path_to_licence) + u"/LICENSE.txt"
            path_to_licence = u"file:///" + path_to_licence
        else:
            logger.error(u"LICENSE.txt file was not found in woofer root dir!")
            path_to_licence = u"http://www.gnu.org/licenses/gpl-2.0.html"

        text = u"Woofer player is <strong>free and open-source cross-platform</strong> music player " \
               u"that plays most multimedia files, CDs, DVDs and also various online streams. " \
               u"Whole written in Python and Qt provides easy, reliable, " \
               u"and high quality playback thanks to LibVLC library developed by " \
               u"<a href='http://www.videolan.org/index.cs.html'>VideoLAN community</a>.<br/>" \
               u"<br/>" \
               u"Created by: Milan Herbig &lt; milanherbig at gmail.com &gt;<br/>" \
               u"Web: <a href='http://www.wooferplayer.com'>www.wooferplayer.com</a><br/>" \
               u"Source: GitHub repository &lt; <a href='%s'>LICENCE GPL v2</a> &gt;<br/>" \
               u"Version: 0.7a" % path_to_licence

        textLabel = QLabel()
        textLabel.setTextFormat(Qt.RichText)
        textLabel.setOpenExternalLinks(True)
        textLabel.setWordWrap(True)
        textLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        textLabel.setText(text)

        iconLabel = QLabel()
        iconLabel.setPixmap(QPixmap(u":/icons/app_icon.png").scaled(128, 128, transformMode=Qt.SmoothTransformation))
        iconLabel.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        layout.addWidget(iconLabel)
        layout.addWidget(textLabel)

        aboutDialog.setLayout(layout)
        aboutDialog.setFixedWidth(480)
        aboutDialog.setFixedHeight(aboutDialog.minimumSizeHint().height())
        aboutDialog.exec_()
        logger.debug(u"'About' dialog closed")

    def closeEvent(self, event):
        """
        Method called when close event caught.
        Quits all threads, saves settings, etc. before application exit.
        :type event: QCloseEvent
        """
        self.hkHook.stop_listening()

        self.scannerThread.quit()
        self.parserThread.quit()
        self.logCleanerThread.quit()
        self.fileRemoverThread.quit()
        self.hkHookThread.quit()
        event.accept()              # emits quit events

        self.mediaPlayer.stop()
        self.saveSettings()








