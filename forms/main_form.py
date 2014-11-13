# -*- coding: utf-8 -*-

"""
All GUI components from main dialog initialized here.
"""

import icons_rc
import logging

from PyQt4.QtGui import *
from PyQt4.QtCore import *

logger = logging.getLogger(__name__)


class MediaSeeker(QSlider):
    """
    Custom QSlider with implemented direct jumping and left-mouse-button semaphore.
    - when left mouse button is pressed, seeker will not sync
    """

    mouseLBPressed = False

    def __init__(self, parent=None):
        super(MediaSeeker, self).__init__(parent)
        self.setMinimum(0)
        self.setMaximum(99)
        self.setOrientation(Qt.Horizontal)

    def mousePressEvent(self, event):
        """
        @type event: QMouseEvent
        """
        if event.button() == Qt.LeftButton:
            # when direct jumping, do this first and then call parent method or slider will not respond to mouse move
            self.mouseLBPressed = True
            newValue = self.minimum() + ((self.maximum()-self.minimum()) * event.x()) / self.width()
            self.setValue(newValue)
            event.accept()

        super(MediaSeeker, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        @type event: QMouseEvent
        """
        if event.button() == Qt.LeftButton:
            self.mouseLBPressed = False

        super(MediaSeeker, self).mouseReleaseEvent(event)


class VolumePopup(QWidget):

    def __init__(self, parent=None):
        super(VolumePopup, self).__init__(parent)

        # setup Ui
        self.volumeSlider = QSlider(Qt.Vertical, self)
        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(self.volumeSlider.maximum())

        self.muteBtn = QPushButton(self)
        self.muteBtn.setIcon(QIcon(QPixmap(u":/icons/mute.png")))
        self.muteBtn.setIconSize(QSize(16, 16))
        self.muteBtn.setCheckable(True)
        self.muteBtn.setFlat(True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.addWidget(self.volumeSlider)
        self.layout.addWidget(self.muteBtn)
        self.setLayout(self.layout)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setFixedSize(self.sizeHint().width(), 200)

        # self.volumeSlider.valueChanged.connect(self.volumeChanged)

    def changeEvent(self, event):
        """
        @type event: QEvent
        """
        super(VolumePopup, self).changeEvent(event)

        # on window activation change, hide widget if not active (has focus) anymore
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow():
                self.close()


class PlaylistTable(QTableWidget):

    def __init__(self, parent):
        super(PlaylistTable, self).__init__(parent)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setTabKeyNavigation(False)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setGridStyle(Qt.DotLine)
        self.setColumnCount(4)
        self.setRowCount(0)
        self.setHorizontalHeaderItem(0, QTableWidgetItem())
        self.setHorizontalHeaderItem(1, QTableWidgetItem())
        self.setHorizontalHeaderItem(2, QTableWidgetItem())
        self.setHorizontalHeaderItem(3, QTableWidgetItem())
        self.horizontalHeader().setDefaultSectionSize(200)
        self.verticalHeader().setDefaultSectionSize(19)
        self.setColumnHidden(self.columnCount() - 1, True)
        header = self.horizontalHeader()
        header.setResizeMode(0, QHeaderView.Stretch)
        header.setResizeMode(1, QHeaderView.Fixed)
        header.setResizeMode(2, QHeaderView.ResizeToContents)
        self.setColumnWidth(1, 100)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.enterShortcut = QShortcut(QKeySequence(Qt.Key_Return), self, context=Qt.WidgetShortcut)
        self.delShortcut = QShortcut(QKeySequence(Qt.Key_Delete), self, context=Qt.WidgetShortcut)
        self.shiftDelShortcut = QShortcut(QKeySequence(Qt.SHIFT + Qt.Key_Delete), self, context=Qt.WidgetShortcut)
        self.enterShortcut.setAutoRepeat(False)
        self.delShortcut.setAutoRepeat(False)
        self.shiftDelShortcut.setAutoRepeat(False)


class MainTreeBrowserTreeView(QTreeView):

    FILES = 0
    PLAYLISTS = 1
    RADIOS = 2

    def __init__(self, parent, folderCombo):
        """

        :type parent:
        :type folderCombo: QComboBox
        :return:
        """
        super(MainTreeBrowserTreeView, self).__init__(parent)
        self._expandedItems = []

        self._mode = None
        self.folderCombo = folderCombo

        self.expanded.connect(self.itemExpanded)
        self.collapsed.connect(self.itemCollapsed)

    def restoreSettings(self):
        """
        Restores previously expanded items in mainTreeBrowser for each mode (FILES, PLAYLISTS, RADIOS)
        """
        logger.debug(u"Restoring mainTreeBrowser state for mode enum %s ...", self._mode)
        settings = QSettings()

        # FILES mode
        if self._mode == MainTreeBrowserTreeView.FILES:
            expandedItems = settings.value(u"gui/mtbtw/expanded/files", [])
            rootFolder = settings.value(u"gui/mtbtw/root/files", u'/')
            model = self.model()

            # find and expand restored paths from settings storage
            if expandedItems:
                self._expandedItems = expandedItems

                # for each path try find its index in fileSystemModel
                for filePath in self._expandedItems:
                    index = model.index(filePath)

                    # expand item in tree, else remove record from list if not found on disk
                    if index is not None:
                        self.expand(index)
                    else:
                        self._expandedItems.remove(filePath)

            # restore media folder root index from last session
            if rootFolder != u'/':
                targetIndex = self.folderCombo.findText(rootFolder)
                if targetIndex != -1:
                    self.folderCombo.setCurrentIndex(targetIndex)
                # else:
                #     print "ERROR index .. delete me!!!"

        # PLAYLISTS mode
        elif self._mode == MainTreeBrowserTreeView.PLAYLISTS:
            pass

        # RADIOS mode
        elif self._mode == MainTreeBrowserTreeView.RADIOS:
            pass

    def saveSettings(self):
        """
        Saves list of expanded items to settings platform depending on current mode.
        """
        logger.debug(u"Saving mainTreeBrowser state for mode enum %s ...", self._mode)
        settings = QSettings()

        # FILES mode
        if self._mode == MainTreeBrowserTreeView.FILES:
            currentRootFolder = self.folderCombo.currentText()
            currentRootFolderIndex = self.folderCombo.currentIndex()
            expandedItems = []

            # if some folder is set as root
            if currentRootFolderIndex != 0:
                # save only folder which are nested under the currentRootFolder
                for item in self._expandedItems:
                    # print item, currentRootFolder
                    if item.startswith(currentRootFolder):
                        expandedItems.append(item)

            # if MyComputer (root) is set as current root folder
            else:
                expandedItems = self._expandedItems
                currentRootFolder = u'/'                 # ... == MyComputer == root

            settings.setValue(u"gui/mtbtw/expanded/files", expandedItems)
            settings.setValue(u"gui/mtbtw/root/files", currentRootFolder)

        # PLAYLISTS mode
        elif self._mode == MainTreeBrowserTreeView.PLAYLISTS:
            pass

        # RADIOS mode
        elif self._mode == MainTreeBrowserTreeView.RADIOS:
            pass

    def setMode(self, mode):
        """
        Change mode to:
            FILES = 0
            PLAYLISTS = 1
            RADIOS = 2
        @type mode: int
        """
        if mode not in range(0, 4):
            raise ValueError(u"Given mode %s is not implemented!" % mode)
        self._mode = mode

    def getMode(self):
        """
        Returns current mode number:
            FILES = 0
            PLAYLISTS = 1
            RADIOS = 2
        @rtype: int
        """
        return self._mode

    @pyqtSlot('QModelIndex')
    def itemExpanded(self, index):
        fileInfo = self.model().fileInfo(index)
        filePath = fileInfo.absoluteFilePath()
        if filePath not in self._expandedItems:
            self._expandedItems.append(filePath)

    @pyqtSlot('QModelIndex')
    def itemCollapsed(self, index):
        fileInfo = self.model().fileInfo(index)
        filePath = fileInfo.absoluteFilePath()
        self._expandedItems.remove(filePath)

        # removes also nested paths
        for i, item in enumerate(self._expandedItems):
            if item.startswith(filePath):
                del self._expandedItems[i]


class MainForm(object):
    """
    Build main form
    """

    def setupUi(self, MainWindow):
        MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(973, 497)
        icon = QIcon()
        icon.addPixmap(QPixmap(u":/icons/app_icon.png"), QIcon.Normal, QIcon.Off)
        MainWindow.setWindowIcon(icon)

        # start MAIN LAYOUT
        self.centralwidget = QWidget(MainWindow)
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(6)

        # start SPLITTER
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.layoutWidget = QWidget(self.splitter)

        # LEFT LAYOUT
        # -----------
        self.mainLeftVLayout = QVBoxLayout(self.layoutWidget)
        self.mainLeftVLayout.setSpacing(0)
        self.mainLeftVLayout.setContentsMargins(0, 0, 0, 0)
        # SOURCE BROWSER
        self.sourceBrowser = QTreeWidget(self.layoutWidget)
        self.sourceBrowser.setMaximumHeight(110)
        self.sourceBrowser.setAnimated(True)
        self.sourceBrowser.setColumnCount(2)
        self.sourceBrowser.setColumnHidden(1, True)     # there is hidden id value in second column
        item_0 = QTreeWidgetItem(self.sourceBrowser)
        icon1 = QIcon(QPixmap(u":/icons/music-cd.png"))
        item_0.setIcon(0, icon1)
        item_1 = QTreeWidgetItem(item_0)
        icon2 = QIcon(QPixmap(u":/icons/folder.png"))
        item_1.setIcon(0, icon2)
        item_1 = QTreeWidgetItem(item_0)
        icon3 = QIcon(QPixmap(u":/icons/playlist.png"))
        item_1.setIcon(0, icon3)
        item_0 = QTreeWidgetItem(self.sourceBrowser)
        icon4 = QIcon(QPixmap(u":/icons/radio.png"))
        item_0.setIcon(0, icon4)
        self.mainLeftVLayout.addWidget(self.sourceBrowser)
        # FOLDER SELECTION
        self.filterHLayout = QHBoxLayout()
        self.filterHLayout.setSpacing(1)
        self.filterHLayout.setContentsMargins(3, 1, 1, 1)
        self.folderLbl = QLabel(self.layoutWidget)
        self.filterHLayout.addWidget(self.folderLbl)
        self.folderCombo = QComboBox(self.layoutWidget)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.folderCombo.sizePolicy().hasHeightForWidth())
        self.folderCombo.setSizePolicy(sizePolicy)
        self.filterHLayout.addWidget(self.folderCombo)
        self.libraryBtn = QPushButton(self.layoutWidget)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.libraryBtn.sizePolicy().hasHeightForWidth())
        self.libraryBtn.setSizePolicy(sizePolicy)
        icon5 = QIcon(QPixmap(u":/icons/settings.png"))
        self.libraryBtn.setIcon(icon5)
        self.libraryBtn.setIconSize(QSize(16, 16))
        self.filterHLayout.addWidget(self.libraryBtn)
        self.mainLeftVLayout.addLayout(self.filterHLayout)
        # SOURCE ITEM BROWSER
        self.mainTreeBrowser = MainTreeBrowserTreeView(self.layoutWidget, self.folderCombo)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHeightForWidth(self.mainTreeBrowser.sizePolicy().hasHeightForWidth())
        self.mainTreeBrowser.setSizePolicy(sizePolicy)
        self.mainTreeBrowser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mainLeftVLayout.addWidget(self.mainTreeBrowser)
        self.layoutWidget1 = QWidget(self.splitter)

        # RIGHT LAYOUT
        # -----------
        self.mainRightVLayout = QVBoxLayout(self.layoutWidget1)
        self.mainRightVLayout.setSpacing(1)
        self.mainRightVLayout.setContentsMargins(0, 0, 0, 0)
        # PLAYLIST
        self.playlistTable = PlaylistTable(self.layoutWidget1)
        self.mainRightVLayout.addWidget(self.playlistTable)
        # CONTROLS
        self.controlsFrame = QFrame(self.layoutWidget1)
        self.controlsFrame.setFrameShape(QFrame.StyledPanel)
        self.controlsFrame.setFrameShadow(QFrame.Plain)
        self.verticalLayout = QVBoxLayout(self.controlsFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.controlsHLayout = QHBoxLayout()
        self.controlsHLayout.setContentsMargins(9, 9, 9, 9)
        self.timeLbl = QLabel(self.controlsFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(self.timeLbl.sizePolicy().hasHeightForWidth())
        self.timeLbl.setSizePolicy(sizePolicy)
        self.controlsHLayout.addWidget(self.timeLbl)
        self.repeatBtn = QPushButton(self.controlsFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.repeatBtn.sizePolicy().hasHeightForWidth())
        self.repeatBtn.setSizePolicy(sizePolicy)
        self.repeatBtn.setMinimumSize(QSize(30, 30))
        icon6 = QIcon(QPixmap(u":/icons/media-repeat.png"))
        self.repeatBtn.setIcon(icon6)
        self.repeatBtn.setIconSize(QSize(16, 16))
        self.repeatBtn.setFlat(True)
        self.repeatBtn.setCheckable(True)
        self.controlsHLayout.addWidget(self.repeatBtn)
        self.previousBtn = QPushButton(self.controlsFrame)
        self.previousBtn.setMinimumSize(QSize(30, 30))
        icon7 = QIcon(QPixmap(u":/icons/media-previous.png"))
        self.previousBtn.setIcon(icon7)
        self.previousBtn.setIconSize(QSize(24, 24))
        self.controlsHLayout.addWidget(self.previousBtn)

        self.playPauseBtn = QPushButton(self.controlsFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.playPauseBtn.sizePolicy().hasHeightForWidth())
        self.playPauseBtn.setSizePolicy(sizePolicy)
        icon8 = QIcon(QPixmap(u":/icons/media-play.png"))
        self.playPauseBtn.setIcon(icon8)
        self.playPauseBtn.setIconSize(QSize(32, 32))
        self.controlsHLayout.addWidget(self.playPauseBtn)

        self.stopBtn = QPushButton(self.controlsFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.stopBtn.sizePolicy().hasHeightForWidth())
        self.stopBtn.setSizePolicy(sizePolicy)
        icon9 = QIcon(QPixmap(u":/icons/media-stop.png"))
        self.stopBtn.setIcon(icon9)
        self.stopBtn.setIconSize(QSize(32, 32))
        self.controlsHLayout.addWidget(self.stopBtn)
        self.nextBtn = QPushButton(self.controlsFrame)
        self.nextBtn.setMinimumSize(QSize(30, 30))
        icon10 = QIcon(QPixmap(u":/icons/media-next.png"))
        self.nextBtn.setIcon(icon10)
        self.nextBtn.setIconSize(QSize(24, 24))
        self.controlsHLayout.addWidget(self.nextBtn)
        self.shuffleBtn = QPushButton(self.controlsFrame)
        self.shuffleBtn.setMinimumSize(QSize(30, 30))
        icon11 = QIcon(QPixmap(u":/icons/media-shuffle.png"))
        self.shuffleBtn.setIcon(icon11)
        self.shuffleBtn.setIconSize(QSize(16, 16))
        self.shuffleBtn.setFlat(True)
        self.shuffleBtn.setCheckable(True)
        self.controlsHLayout.addWidget(self.shuffleBtn)
        spacerItem = QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.controlsHLayout.addItem(spacerItem)
        self.volumePopup = VolumePopup(self)
        self.seekerSlider = MediaSeeker(self)
        self.volumeSlider = self.volumePopup.volumeSlider
        self.muteBtn = self.volumePopup.muteBtn
        self.volumeBtn = QPushButton(self.controlsFrame)
        self.volumeBtn.setMinimumSize(QSize(10, 30))
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.volumeBtn.setSizePolicy(sizePolicy)
        icon12 = QIcon(QPixmap(u":/icons/volume-max.png"))
        self.volumeBtn.setIcon(icon12)
        self.volumeBtn.setIconSize(QSize(16, 16))
        self.volumeBtn.setFlat(True)
        self.controlsHLayout.addWidget(self.seekerSlider)
        self.controlsHLayout.addWidget(self.volumeBtn)
        self.verticalLayout.addLayout(self.controlsHLayout)
        self.mainRightVLayout.addWidget(self.controlsFrame)
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        # MAIN MENU
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setGeometry(QRect(0, 0, 973, 21))
        self.menuMedia = QMenu(self.menubar)
        self.menuPlaylist = QMenu(self.menubar)
        self.menuTools = QMenu(self.menubar)
        self.menuHelp = QMenu(self.menubar)

        self.mediaPlayPauseAction = QAction(QIcon(u":/icons/media-play.png"), u"&Play", MainWindow)
        self.mediaPlayPauseAction.setShortcut(QKeySequence(Qt.Key_F6))
        self.mediaPlayPauseAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaStopAction = QAction(QIcon(u":/icons/media-stop.png"), u"&Stop", MainWindow)
        self.mediaStopAction.setShortcut(QKeySequence(Qt.Key_F7))
        self.mediaStopAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaNextAction = QAction(QIcon(u":/icons/media-next.png"), u"&Next", MainWindow)
        self.mediaNextAction.setShortcut(QKeySequence(Qt.Key_F8))
        self.mediaNextAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaPreviousAction = QAction(QIcon(u":/icons/media-previous.png"), u"Pre&vious", MainWindow)
        self.mediaPreviousAction.setShortcut(QKeySequence(Qt.Key_F5))
        self.mediaPreviousAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaShuffleAction = QAction(QIcon(u":/icons/media-shuffle.png"), u"Shu&ffle", MainWindow)
        self.mediaShuffleAction.setCheckable(True)
        self.mediaRepeatAction = QAction(QIcon(u":/icons/media-repeat.png"), u"&Repeat", MainWindow)
        self.mediaRepeatAction.setCheckable(True)
        self.mediaMuteAction = QAction(QIcon(u":/icons/mute.png"), u"&Mute", MainWindow)
        self.mediaMuteAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_M))
        self.mediaMuteAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaQuitAction = QAction(QIcon(u":/icons/quit.png"), u"&Quit", MainWindow)
        self.mediaQuitAction.setShortcut(QKeySequence(QKeySequence.Quit))
        self.mediaQuitAction.setShortcutContext(Qt.ApplicationShortcut)
        # self.playlistPlayAction = QAction(QIcon(u":/icons/media-play.png"), u"&Play files...", MainWindow)
        # self.playlistAddAction = QAction(QIcon(u":/icons/media-next.png"), u"&Add files...", MainWindow)
        self.playlistSaveAction = QAction(QIcon(u":/icons/save.png"), u"&Save playlist", MainWindow)
        self.playlistSaveAction.setEnabled(False)
        self.playlistLoadAction = QAction(QIcon(u":/icons/open.png"), u"&Load playlist", MainWindow)
        self.playlistLoadAction.setEnabled(False)
        self.playlistClearAction = QAction(QIcon(u":/icons/delete.png"), u"&Clear current playlist", MainWindow)
        self.toolsSettingsAction = QAction(QIcon(u":/icons/settings.png"), u"&Settings", MainWindow)
        self.toolsSettingsAction.setEnabled(False)
        self.helpHelpAction = QAction(QIcon(u":/icons/help.png"), u"&Help", MainWindow)
        self.helpHelpAction.setEnabled(False)
        self.helpAboutAction = QAction(QIcon(u":/icons/info.png"), u"&About", MainWindow)

        self.menubar.addAction(self.menuMedia.menuAction())
        self.menubar.addAction(self.menuPlaylist.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menuMedia.addActions([self.mediaPlayPauseAction, self.mediaStopAction, self.mediaNextAction, self.mediaPreviousAction])
        self.menuMedia.addSeparator()
        self.menuMedia.addActions([self.mediaShuffleAction, self.mediaRepeatAction, self.mediaMuteAction])
        self.menuMedia.addSeparator()
        self.menuMedia.addAction(self.mediaQuitAction)
        # self.menuPlaylist.addActions([self.playlistPlayAction, self.playlistAddAction])
        # self.menuPlaylist.addSeparator()
        self.menuPlaylist.addActions([self.playlistSaveAction, self.playlistLoadAction])
        self.menuPlaylist.addSeparator()
        self.menuPlaylist.addAction(self.playlistClearAction)
        self.menuTools.addAction(self.toolsSettingsAction)
        self.menuHelp.addActions([self.helpHelpAction, self.helpAboutAction])

        # STATUSBAR
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setStyleSheet("QStatusBar::item {border: none;}")    # remove statusbar separator
        MainWindow.setStatusBar(self.statusbar)
        self.progressBar = QProgressBar(self)
        self.progressLabel = QLabel(self)
        self.progressBar.setMaximumSize(200, self.progressBar.minimumSizeHint().height())
        self.progressCancelBtn = QPushButton()
        icon_progressCancelBtn = QIcon(QPixmap(u":/icons/remove_close.png"))
        self.progressCancelBtn.setIcon(icon_progressCancelBtn)
        self.progressCancelBtn.setIconSize(QSize(10, 10))
        self.progressCancelBtn.setFixedSize(QSize(self.progressBar.sizeHint().height(), self.progressBar.sizeHint().height()))
        self.statusbar.addPermanentWidget(self.progressLabel)
        self.statusbar.addPermanentWidget(self.progressBar)
        self.statusbar.addPermanentWidget(self.progressCancelBtn)
        self.progressLabel.hide()
        self.progressBar.hide()
        self.progressCancelBtn.hide()
        self.stBarMsgIcon = QLabel(self)
        self.stBarMsgText = QLabel(self)
        self.statusbar.addWidget(self.stBarMsgIcon)
        self.statusbar.addWidget(self.stBarMsgText)
        self.stBarMsgIcon.hide()
        self.stBarMsgText.hide()

        self.retranslateUi(MainWindow)
        self.sourceBrowser.expandAll()
        self.timeLbl.setFixedSize(self.timeLbl.minimumSizeHint())       # prevent 1px oscillation

        # disable Playlist and Radios - not implemented yet
        self.sourceBrowser.topLevelItem(0).child(1).setDisabled(True)
        self.sourceBrowser.topLevelItem(1).setDisabled(True)

    def retranslateUi(self, MainWindow):
        self.sourceBrowser.headerItem().setText(0, "Playback source")
        self.sourceBrowser.headerItem().setText(1, "ID")
        __sortingEnabled = self.sourceBrowser.isSortingEnabled()
        self.sourceBrowser.setSortingEnabled(False)
        self.sourceBrowser.topLevelItem(0).setText(0, "Music")
        self.sourceBrowser.topLevelItem(0).child(0).setText(0, "Folders")
        self.sourceBrowser.topLevelItem(0).child(0).setText(1, "0")
        self.sourceBrowser.topLevelItem(0).child(1).setText(0, "Playlists")
        self.sourceBrowser.topLevelItem(0).child(1).setText(1, "1")
        self.sourceBrowser.topLevelItem(1).setText(0, "Radios")
        self.sourceBrowser.topLevelItem(1).setText(1, "2")
        self.sourceBrowser.setSortingEnabled(__sortingEnabled)
        self.folderLbl.setText("Folder:")
        self.libraryBtn.setToolTip("Edit media library")
        self.playlistTable.horizontalHeaderItem(0).setText("Title")
        self.playlistTable.horizontalHeaderItem(1).setText("Favorite")
        self.playlistTable.horizontalHeaderItem(2).setText("Duration")
        self.playlistTable.horizontalHeaderItem(3).setText("Path")
        self.timeLbl.setText("00:00:00")
        self.playPauseBtn.setShortcut("Ctrl+Alt+P")
        self.menuMedia.setTitle("&Media")
        self.menuPlaylist.setTitle("&Playlist")
        self.menuTools.setTitle("&Tools")
        self.menuHelp.setTitle("&Help")
