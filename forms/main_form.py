# -*- coding: utf-8 -*-

"""
All GUI components stored here.
"""

__version__ = "$Id$"

import icons_rc
import logging
import time

from PySide.QtGui import *
from PySide.QtCore import *
from tools import misc

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class MediaSeeker(QSlider):
    """
    Custom QSlider with implemented direct jumping and left-mouse-button semaphore.
    - when left mouse button is pressed, seeker will not sync
    """

    mouseLBPressed = False

    def __init__(self, parent=None):
        super(MediaSeeker, self).__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
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
        super(MediaSeeker, self).mouseReleaseEvent(event)

        if event.button() == Qt.LeftButton:
            self.mouseLBPressed = False


class VolumeSeeker(QSlider):
    """
    Custom QSlider with implemented direct jumping.
    """

    def __init__(self, parent=None):
        super(VolumeSeeker, self).__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(100)
        self.setMaximumWidth(80)
        self.setOrientation(Qt.Horizontal)

    def mousePressEvent(self, event):
        """
        @type event: QMouseEvent
        """
        if event.button() == Qt.LeftButton:
            # when direct jumping, do this first and then call parent method or slider will not respond to mouse move
            newValue = self.minimum() + ((self.maximum()-self.minimum()) * event.x()) / self.width()
            self.setValue(newValue)
            event.accept()

        super(VolumeSeeker, self).mousePressEvent(event)


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

    def __init__(self, parent=None):
        super(MainTreeBrowserTreeView, self).__init__(parent)
        self._expandedItems = []
        self._mode = None

        self.expanded.connect(self.itemExpanded)
        self.collapsed.connect(self.itemCollapsed)

    def restoreState(self):
        """
        Restores previously expanded items in mainTreeBrowser for each mode (FILES, PLAYLISTS, RADIOS)
        """
        logger.debug("Restoring mainTreeBrowser state for mode enum %s ...", self._mode)

        settings = QSettings()

        # self.thread().msleep(2000)
        t0 = time.time()

        # FILES mode
        if self._mode == MainTreeBrowserTreeView.FILES:
            model = self.model()
            expandedItems = settings.value("gui/mtbtw/expanded/files", [])

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

        # PLAYLISTS mode
        elif self._mode == MainTreeBrowserTreeView.PLAYLISTS:
            pass

        # RADIOS mode
        elif self._mode == MainTreeBrowserTreeView.RADIOS:
            pass

        print (time.time() - t0) * 1000

    def saveState(self):
        """
        Saves list of expanded items to settings platform depending on current mode.
        """
        logger.debug("Saving mainTreeBrowser state for mode enum %s ...", self._mode)

        settings = QSettings()

        # FILES mode
        if self._mode == MainTreeBrowserTreeView.FILES:
            settings.setValue("gui/mtbtw/expanded/files", self._expandedItems)

        # PLAYLISTS mode
        elif self._mode == MainTreeBrowserTreeView.PLAYLISTS:
            pass

        # RADIOS mode
        elif self._mode == MainTreeBrowserTreeView.RADIO:
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
            raise ValueError("Given mode %s is not implemented!" % mode)
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

    @Slot(QModelIndex)
    def itemExpanded(self, index):
        fileInfo = self.model().fileInfo(index)
        filePath = fileInfo.absoluteFilePath()
        self._expandedItems.append(filePath)

    @Slot(QModelIndex)
    def itemCollapsed(self, index):
        fileInfo = self.model().fileInfo(index)
        filePath = fileInfo.absoluteFilePath()
        self._expandedItems.remove(filePath)


class MainForm(object):
    """
    Build main form
    """

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(973, 497)
        icon = QIcon()
        icon.addPixmap(QPixmap(":/new/icons/icons/app_icon.png"), QIcon.Normal, QIcon.Off)
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
        icon1 = QIcon(QPixmap(":/new/icons/icons/music-cd.png"))
        item_0.setIcon(0, icon1)
        item_1 = QTreeWidgetItem(item_0)
        icon2 = QIcon(QPixmap(":/new/icons/icons/folder.png"))
        item_1.setIcon(0, icon2)
        item_1 = QTreeWidgetItem(item_0)
        icon3 = QIcon(QPixmap(":/new/icons/icons/playlist.png"))
        item_1.setIcon(0, icon3)
        item_0 = QTreeWidgetItem(self.sourceBrowser)
        icon4 = QIcon(QPixmap(":/new/icons/icons/radio.png"))
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
        icon5 = QIcon(QPixmap(":/new/icons/icons/settings.png"))
        self.libraryBtn.setIcon(icon5)
        self.filterHLayout.addWidget(self.libraryBtn)
        self.mainLeftVLayout.addLayout(self.filterHLayout)
        # SOURCE ITEM BROWSER
        self.mainTreeBrowser = MainTreeBrowserTreeView(self.layoutWidget)
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
        self.playlist = PlaylistTable(self.layoutWidget1)
        self.mainRightVLayout.addWidget(self.playlist)
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
        icon6 = QIcon(QPixmap(":/new/icons/icons/media-repeat.png"))
        self.repeatBtn.setIcon(icon6)
        self.repeatBtn.setIconSize(QSize(16, 16))
        self.repeatBtn.setFlat(True)
        self.controlsHLayout.addWidget(self.repeatBtn)
        self.previousBtn = QPushButton(self.controlsFrame)
        self.previousBtn.setMinimumSize(QSize(30, 30))
        icon7 = QIcon(QPixmap(":/new/icons/icons/media-previous.png"))
        self.previousBtn.setIcon(icon7)
        self.previousBtn.setIconSize(QSize(24, 24))
        self.controlsHLayout.addWidget(self.previousBtn)
        self.playPauseBtn = QPushButton(self.controlsFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.playPauseBtn.sizePolicy().hasHeightForWidth())
        self.playPauseBtn.setSizePolicy(sizePolicy)
        icon8 = QIcon(QPixmap(":/new/icons/icons/media-play.png"))
        self.playPauseBtn.setIcon(icon8)
        self.playPauseBtn.setIconSize(QSize(32, 32))
        self.controlsHLayout.addWidget(self.playPauseBtn)
        self.stopBtn = QPushButton(self.controlsFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.stopBtn.sizePolicy().hasHeightForWidth())
        self.stopBtn.setSizePolicy(sizePolicy)
        icon9 = QIcon(QPixmap(":/new/icons/icons/media-stop.png"))
        self.stopBtn.setIcon(icon9)
        self.stopBtn.setIconSize(QSize(32, 32))
        self.controlsHLayout.addWidget(self.stopBtn)
        self.nextBtn = QPushButton(self.controlsFrame)
        self.nextBtn.setMinimumSize(QSize(30, 30))
        icon10 = QIcon(QPixmap(":/new/icons/icons/media-next.png"))
        self.nextBtn.setIcon(icon10)
        self.nextBtn.setIconSize(QSize(24, 24))
        self.controlsHLayout.addWidget(self.nextBtn)
        self.shuffleBtn = QPushButton(self.controlsFrame)
        self.shuffleBtn.setMinimumSize(QSize(30, 30))
        icon11 = QIcon(QPixmap(":/new/icons/icons/media-shuffle.png"))
        self.shuffleBtn.setIcon(icon11)
        self.shuffleBtn.setIconSize(QSize(16, 16))
        self.shuffleBtn.setFlat(True)
        self.controlsHLayout.addWidget(self.shuffleBtn)
        spacerItem = QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.controlsHLayout.addItem(spacerItem)
        self.seekerSlider = MediaSeeker(self)
        self.volumeSlider = VolumeSeeker(self)
        self.controlsHLayout.addWidget(self.seekerSlider)
        self.controlsHLayout.addWidget(self.volumeSlider)
        self.verticalLayout.addLayout(self.controlsHLayout)
        self.mainRightVLayout.addWidget(self.controlsFrame)
        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        # MAIN MENU
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setGeometry(QRect(0, 0, 973, 21))
        self.menuFile = QMenu(self.menubar)
        self.menuPlayback = QMenu(self.menubar)
        self.menuEdit = QMenu(self.menubar)
        self.menuHelp = QMenu(self.menubar)
        self.actionAbout = QAction(MainWindow)
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuPlayback.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        # STATUSBAR
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setStyleSheet("QStatusBar::item {border: none;}")    # remove statusbar separator
        MainWindow.setStatusBar(self.statusbar)
        self.progressBar = QProgressBar(self)
        self.progressLabel = QLabel(self)
        self.progressBar.setMaximumSize(200, self.progressBar.minimumSizeHint().height())
        self.progressCancelBtn = QPushButton()
        icon_progressCancelBtn = QIcon(QPixmap(":/new/icons/icons/remove_close.png"))
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

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QApplication.translate("MainWindow", "Woofer", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.headerItem().setText(0, QApplication.translate("MainWindow", "Playback source", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.headerItem().setText(1, QApplication.translate("MainWindow", "ID", None, QApplication.UnicodeUTF8))
        __sortingEnabled = self.sourceBrowser.isSortingEnabled()
        self.sourceBrowser.setSortingEnabled(False)
        self.sourceBrowser.topLevelItem(0).setText(0, QApplication.translate("MainWindow", "Music", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.topLevelItem(0).child(0).setText(0, QApplication.translate("MainWindow", "Folders", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.topLevelItem(0).child(0).setText(1, QApplication.translate("MainWindow", "0", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.topLevelItem(0).child(1).setText(0, QApplication.translate("MainWindow", "Playlists", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.topLevelItem(0).child(1).setText(1, QApplication.translate("MainWindow", "1", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.topLevelItem(1).setText(0, QApplication.translate("MainWindow", "Radios", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.topLevelItem(1).setText(1, QApplication.translate("MainWindow", "2", None, QApplication.UnicodeUTF8))
        self.sourceBrowser.setSortingEnabled(__sortingEnabled)
        self.folderLbl.setText(QApplication.translate("MainWindow", "Folder:", None, QApplication.UnicodeUTF8))
        self.libraryBtn.setToolTip(QApplication.translate("MainWindow", "Edit media library", None, QApplication.UnicodeUTF8))
        self.playlist.horizontalHeaderItem(0).setText(QApplication.translate("MainWindow", "Title", None, QApplication.UnicodeUTF8))
        self.playlist.horizontalHeaderItem(1).setText(QApplication.translate("MainWindow", "Favorite", None, QApplication.UnicodeUTF8))
        self.playlist.horizontalHeaderItem(2).setText(QApplication.translate("MainWindow", "Duration", None, QApplication.UnicodeUTF8))
        self.playlist.horizontalHeaderItem(3).setText(QApplication.translate("MainWindow", "Path", None, QApplication.UnicodeUTF8))
        self.timeLbl.setText(QApplication.translate("MainWindow", "00:00:00", None, QApplication.UnicodeUTF8))
        self.playPauseBtn.setShortcut(QApplication.translate("MainWindow", "Ctrl+Alt+P", None, QApplication.UnicodeUTF8))
        self.menuFile.setTitle(QApplication.translate("MainWindow", "Media", None, QApplication.UnicodeUTF8))
        self.menuPlayback.setTitle(QApplication.translate("MainWindow", "Playback", None, QApplication.UnicodeUTF8))
        self.menuEdit.setTitle(QApplication.translate("MainWindow", "Edit", None, QApplication.UnicodeUTF8))
        self.menuHelp.setTitle(QApplication.translate("MainWindow", "Help", None, QApplication.UnicodeUTF8))
        self.actionAbout.setText(QApplication.translate("MainWindow", "About", None, QApplication.UnicodeUTF8))
