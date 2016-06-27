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
All GUI components from main dialog initialized here.
"""

from . import icons_rc
import logging
import os

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from components.translator import tr

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
        self.setEnabled(False)
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
        self.volumeSlider.setMaximum(150)
        self.volumeSlider.setValue(100)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.volumeSlider.setSizePolicy(sizePolicy)
        self.volumeSlider.valueChanged.connect(self.volumeChanged)

        self.volumeValue = QLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.volumeValue.setText(str(self.volumeSlider.value()))
        self.volumeValue.setSizePolicy(sizePolicy)
        self.volumeValue.setAlignment(Qt.AlignCenter)

        self.muteBtn = QPushButton(self)
        self.muteBtn.setIcon(QIcon(QPixmap(":/icons/mute.png")))
        self.muteBtn.setIconSize(QSize(16, 16))
        self.muteBtn.setCheckable(True)
        self.muteBtn.setFlat(True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.addWidget(self.volumeSlider)
        self.layout.addWidget(self.volumeValue)
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

    @pyqtSlot(int)
    def volumeChanged(self, value):
        self.volumeValue.setText(str(value) + "%")


class PlaylistTable(QTableWidget):

    def __init__(self, parent):
        super(PlaylistTable, self).__init__(parent)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setTabKeyNavigation(False)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setGridStyle(Qt.DotLine)
        self.setColumnCount(4)
        self.setRowCount(0)
        self.setHorizontalHeaderItem(0, QTableWidgetItem())
        self.setHorizontalHeaderItem(1, QTableWidgetItem())
        self.setHorizontalHeaderItem(2, QTableWidgetItem())
        self.setHorizontalHeaderItem(3, QTableWidgetItem())
        vheader = self.verticalHeader()
        vheader.setDefaultSectionSize(vheader.defaultSectionSize())
        vheader.setSectionResizeMode(QHeaderView.Fixed)
        hheader = self.horizontalHeader()
        hheader.setSectionResizeMode(0, QHeaderView.Interactive)
        hheader.setSectionResizeMode(1, QHeaderView.Stretch)
        hheader.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hheader.setDefaultSectionSize(300)
        self.setColumnHidden(self.columnCount() - 1, True)
        self.setColumnWidth(1, 100)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.enterShortcut = QShortcut(QKeySequence(Qt.Key_Return), self, context=Qt.WidgetShortcut)
        self.delShortcut = QShortcut(QKeySequence(Qt.Key_Delete), self, context=Qt.WidgetShortcut)
        self.shiftDelShortcut = QShortcut(QKeySequence(Qt.SHIFT + Qt.Key_Delete), self, context=Qt.WidgetShortcut)
        self.enterShortcut.setAutoRepeat(False)
        self.delShortcut.setAutoRepeat(False)
        self.shiftDelShortcut.setAutoRepeat(False)


class MainTreeBrowserTreeView(QTreeView):

    def __init__(self, parent, folderCombo):
        """
        :type parent:
        :type folderCombo: QComboBox
        :return:
        """
        super(MainTreeBrowserTreeView, self).__init__(parent)
        self._expandedItems = []

        self.folderCombo = folderCombo

        self.expanded.connect(self.itemExpanded)
        self.collapsed.connect(self.itemCollapsed)

    def restoreSettings(self):
        """
        Restores previously expanded items in mainTreeBrowser for each mode (FILES, PLAYLISTS, RADIOS)
        """
        logger.debug("Restoring mainTreeBrowser state ...")
        settings = QSettings()
        expandedItems = settings.value("gui/MainTreeBrowserTreeView/expanded/files", [])
        rootFolder = settings.value("gui/MainTreeBrowserTreeView/root/files", tr['HOME_DIR'])
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
        targetIndex = self.folderCombo.findText(rootFolder)
        if targetIndex != -1:
            self.folderCombo.setCurrentIndex(targetIndex)
        pass

    def saveSettings(self):
        """
        Saves list of expanded items to settings platform depending on current mode.
        """
        logger.debug("Saving mainTreeBrowser state ...")
        settings = QSettings()
        currentText = self.folderCombo.currentText()
        if currentText == tr['HOME_DIR']:
            currentRootFolder = QDir.homePath()
        elif currentText == tr['MY_COMPUTER']:
            currentRootFolder = QDir.rootPath()
        else:
            currentRootFolder = currentText
        # currentRootFolderIndex = self.folderCombo.currentIndex()
        expandedItems = []

        # save only folder which are nested under the currentRootFolder
        for item in self._expandedItems:
            if item.startswith(currentRootFolder):
                expandedItems.append(item)

        settings.setValue("gui/MainTreeBrowserTreeView/expanded/files", expandedItems)
        settings.setValue("gui/MainTreeBrowserTreeView/root/files", currentText)

    @pyqtSlot(QModelIndex)
    def itemExpanded(self, index):
        fileInfo = self.model().fileInfo(index)
        filePath = fileInfo.absoluteFilePath()
        if filePath not in self._expandedItems:
            self._expandedItems.append(filePath)

    @pyqtSlot(QModelIndex)
    def itemCollapsed(self, index):
        fileInfo = self.model().fileInfo(index)
        filePath = fileInfo.absoluteFilePath()
        try:
            self._expandedItems.remove(filePath)
        except Exception:
            pass

        # removes also nested paths
        for i, item in enumerate(self._expandedItems):
            if item.startswith(filePath):
                del self._expandedItems[i]


class MainForm(object):
    """
    Build main form
    """

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 400)
        icon = QIcon()
        icon.addPixmap(QPixmap(":/icons/app_icon.png"), QIcon.Normal, QIcon.Off)
        MainWindow.setWindowIcon(icon)

        # start MAIN LAYOUT
        self.centralwidget = QWidget(MainWindow)
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setContentsMargins(3, 3, 3, 3)
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(0)

        # start SPLITTER
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setHandleWidth(6)
        self.layoutWidget = QWidget(self.splitter)

        # LEFT LAYOUT
        # -----------
        self.mainLeftVLayout = QVBoxLayout(self.layoutWidget)
        self.mainLeftVLayout.setSpacing(0)
        self.mainLeftVLayout.setContentsMargins(0, 0, 0, 0)
        # FOLDER SELECTION
        self.filterHLayout = QHBoxLayout()
        self.filterHLayout.setSpacing(0)
        self.filterHLayout.setContentsMargins(0, 2, 0, 2)
        self.folderLbl = QLabel(self.layoutWidget)
        self.filterHLayout.addWidget(self.folderLbl)
        self.folderLbl.setVisible(False)
        self.folderCombo = QComboBox(self.layoutWidget)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # sizePolicy.setHeightForWidth(self.folderCombo.sizePolicy().hasHeightForWidth())
        self.folderCombo.setSizePolicy(sizePolicy)
        self.filterHLayout.addWidget(self.folderCombo)
        self.libraryBtn = QPushButton(self.layoutWidget)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # sizePolicy.setHeightForWidth(self.libraryBtn.sizePolicy().hasHeightForWidth())
        self.libraryBtn.setSizePolicy(sizePolicy)
        icon5 = QIcon(QPixmap(":/icons/settings.png"))
        self.libraryBtn.setIcon(icon5)
        self.libraryBtn.setIconSize(QSize(16, 16))
        self.filterHLayout.addWidget(self.libraryBtn)
        self.mainLeftVLayout.addLayout(self.filterHLayout)
        if os.name == "nt":         # windows fix
            self.folderCombo.setStyleSheet("margin-top: 1px;"
                                           "margin-bottom: 1px;"
                                           "padding-left: 4px;")
        # FILE BROWSER
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
        self.mainRightVLayout.setSpacing(0)
        self.mainRightVLayout.setContentsMargins(0, 0, 0, 0)
        # PLAYLIST
        self.playlistTable = PlaylistTable(self.layoutWidget1)
        self.mainRightVLayout.addWidget(self.playlistTable)
        # CONTROLS
        self.controlsFrame = QFrame(self.layoutWidget1)
        self.controlsFrame.setFrameShape(QFrame.NoFrame)
        self.controlsFrame.setFrameShadow(QFrame.Plain)
        self.verticalLayout = QVBoxLayout(self.controlsFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.controlsHLayout = QHBoxLayout()
        self.controlsHLayout.setContentsMargins(9, 6, 9, 3)
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
        icon6 = QIcon(QPixmap(":/icons/media-repeat.png"))
        self.repeatBtn.setIcon(icon6)
        self.repeatBtn.setIconSize(QSize(16, 16))
        self.repeatBtn.setFlat(True)
        self.repeatBtn.setCheckable(True)
        self.controlsHLayout.addWidget(self.repeatBtn)
        self.previousBtn = QPushButton(self.controlsFrame)
        self.previousBtn.setMinimumSize(QSize(30, 30))
        icon7 = QIcon(QPixmap(":/icons/media-previous.png"))
        self.previousBtn.setIcon(icon7)
        self.previousBtn.setIconSize(QSize(24, 24))
        self.controlsHLayout.addWidget(self.previousBtn)

        self.playPauseBtn = QPushButton(self.controlsFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.playPauseBtn.sizePolicy().hasHeightForWidth())
        self.playPauseBtn.setSizePolicy(sizePolicy)
        icon8 = QIcon(QPixmap(":/icons/media-play.png"))
        self.playPauseBtn.setIcon(icon8)
        self.playPauseBtn.setIconSize(QSize(32, 32))
        self.controlsHLayout.addWidget(self.playPauseBtn)

        self.stopBtn = QPushButton(self.controlsFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.stopBtn.sizePolicy().hasHeightForWidth())
        self.stopBtn.setSizePolicy(sizePolicy)
        icon9 = QIcon(QPixmap(":/icons/media-stop.png"))
        self.stopBtn.setIcon(icon9)
        self.stopBtn.setIconSize(QSize(32, 32))
        self.controlsHLayout.addWidget(self.stopBtn)
        self.nextBtn = QPushButton(self.controlsFrame)
        self.nextBtn.setMinimumSize(QSize(30, 30))
        icon10 = QIcon(QPixmap(":/icons/media-next.png"))
        self.nextBtn.setIcon(icon10)
        self.nextBtn.setIconSize(QSize(24, 24))
        self.controlsHLayout.addWidget(self.nextBtn)
        self.shuffleBtn = QPushButton(self.controlsFrame)
        self.shuffleBtn.setMinimumSize(QSize(30, 30))
        icon11 = QIcon(QPixmap(":/icons/media-shuffle.png"))
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

        # volume icons
        self.maxVolumeIcon = QIcon(QPixmap(":/icons/volume-max.png"))
        self.mediumVolumeIcon = QIcon(QPixmap(":/icons/volume-medium.png"))
        self.lowVolumeIcon = QIcon(QPixmap(":/icons/volume-low.png"))
        self.minVolumeIcon = QIcon(QPixmap(":/icons/volume-min.png"))
        color = QColor()
        color.setHsv(0, 255, 210)
        self.colorVolumePixmap = QPixmap(":/icons/volume-max.png")
        color_mask = QPixmap(self.colorVolumePixmap.size())
        color_mask.fill(color)
        color_mask.setMask(self.colorVolumePixmap.createMaskFromColor(Qt.transparent))

        self.volumeBtn.setIcon(self.maxVolumeIcon)
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

        self.mediaPlayPauseAction = QAction(QIcon(":/icons/media-play.png"), tr['PLAY'], MainWindow)
        self.mediaPlayPauseAction.setShortcut(QKeySequence(Qt.Key_F6))
        self.mediaPlayPauseAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaStopAction = QAction(QIcon(":/icons/media-stop.png"), tr['STOP'], MainWindow)
        self.mediaStopAction.setShortcut(QKeySequence(Qt.Key_F7))
        self.mediaStopAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaNextAction = QAction(QIcon(":/icons/media-next.png"), tr['NEXT'], MainWindow)
        self.mediaNextAction.setShortcut(QKeySequence(Qt.Key_F8))
        self.mediaNextAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaPreviousAction = QAction(QIcon(":/icons/media-previous.png"), tr['PREVIOUS'], MainWindow)
        self.mediaPreviousAction.setShortcut(QKeySequence(Qt.Key_F5))
        self.mediaPreviousAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaShuffleAction = QAction(QIcon(":/icons/media-shuffle.png"), tr['SHUFFLE'], MainWindow)
        self.mediaShuffleAction.setCheckable(True)
        self.mediaRepeatAction = QAction(QIcon(":/icons/media-repeat.png"), tr['REPEAT'], MainWindow)
        self.mediaRepeatAction.setCheckable(True)
        self.mediaMuteAction = QAction(QIcon(":/icons/mute.png"), tr['MUTE'], MainWindow)
        self.mediaMuteAction.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_M))
        self.mediaMuteAction.setShortcutContext(Qt.ApplicationShortcut)
        self.mediaQuitAction = QAction(QIcon(":/icons/quit.png"), tr['QUIT'], MainWindow)
        self.mediaQuitAction.setShortcut(QKeySequence(QKeySequence.Quit))
        self.mediaQuitAction.setShortcutContext(Qt.ApplicationShortcut)
        # self.playlistPlayAction = QAction(QIcon(u":/icons/media-play.png"), u"&Play files...", MainWindow)
        # self.playlistAddAction = QAction(QIcon(u":/icons/media-next.png"), u"&Add files...", MainWindow)
        self.playlistSaveAction = QAction(QIcon(":/icons/save.png"), tr['SAVE_PLAYLIST'], MainWindow)
        self.playlistSaveAction.setEnabled(False)
        self.playlistLoadAction = QAction(QIcon(":/icons/open.png"), tr['LOAD_PLAYLIST'], MainWindow)
        self.playlistLoadAction.setEnabled(False)
        self.playlistClearAction = QAction(QIcon(":/icons/delete.png"), tr['CLEAR_PLAYLIST'], MainWindow)
        self.toolsSettingsAction = QAction(QIcon(":/icons/settings.png"), tr['SETTINGS'], MainWindow)
        # self.toolsSettingsAction.setEnabled(False)
        # self.helpHelpAction = QAction(QIcon(u":/icons/help.png"), u"&Help", MainWindow)
        # self.helpHelpAction.setEnabled(False)
        # self.helpHelpAction.setVisible(False)
        self.helpAboutAction = QAction(QIcon(":/icons/info.png"), tr['ABOUT'], MainWindow)

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
        self.menuHelp.addAction(self.helpAboutAction)

        # STATUSBAR
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setSizeGripEnabled(False)
        self.statusbar.setStyleSheet("QStatusBar::item {border: none;}")    # remove statusbar separator
        self.statusbar.setFixedHeight(24)
        MainWindow.setStatusBar(self.statusbar)
        self.progressBar = QProgressBar(self)
        self.progressBar.setTextVisible(False)
        self.progressLabel = QLabel(self)
        self.progressBar.setMaximumSize(200, self.progressBar.sizeHint().height())
        self.progressCancelBtn = QPushButton()
        icon_progressCancelBtn = QIcon(QPixmap(":/icons/remove_close.png"))
        self.progressCancelBtn.setIcon(icon_progressCancelBtn)
        self.progressCancelBtn.setIconSize(QSize(8, 8))
        self.progressCancelBtn.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.progressCancelBtn.setText(tr['CANCEL'])
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
        self.timeLbl.setFixedSize(self.timeLbl.minimumSizeHint())       # prevent 1px oscillation

    def retranslateUi(self, MainWindow):
        self.folderLbl.setText(tr['SOURCE_FOLDER_TITLE'])
        self.libraryBtn.setToolTip(tr['MEDIA_LIBRARY_TOOLTIP'])
        self.playlistTable.horizontalHeaderItem(0).setText(tr['PLAYLIST_TITLE'])
        self.playlistTable.horizontalHeaderItem(1).setText(tr['PLAYLIST_FNAME'])
        self.playlistTable.horizontalHeaderItem(2).setText(tr['PLAYLIST_DURATION'])
        self.playlistTable.horizontalHeaderItem(3).setText(tr['PLAYLIST_PATH'])
        self.timeLbl.setText("00:00:00")
        # self.playPauseBtn.setShortcut("Ctrl+Alt+P")
        self.menuMedia.setTitle(tr['MEDIA'])
        self.menuPlaylist.setTitle(tr['PLAYLIST'])
        self.menuTools.setTitle(tr['TOOLS'])
        self.menuHelp.setTitle(tr['HELP'])
