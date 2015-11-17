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


from PyQt4 import QtCore, QtGui

from components.translator import tr


class Ui_settingsDialog(object):
    def setupUi(self, settingsDialog):
        settingsDialog.setObjectName("settingsDialog")
        settingsDialog.resize(351, 251)
        settingsDialog.setModal(True)
        self.verticalLayout_2 = QtGui.QVBoxLayout(settingsDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.frame = QtGui.QFrame(settingsDialog)
        self.frame.setFrameShape(QtGui.QFrame.Box)
        self.frame.setFrameShadow(QtGui.QFrame.Sunken)
        self.frame.setObjectName("frame")
        self.verticalLayout = QtGui.QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName("verticalLayout")
        self.fileBrowserLbl = QtGui.QLabel(self.frame)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.fileBrowserLbl.setFont(font)
        self.fileBrowserLbl.setObjectName("fileBrowserLbl")
        self.verticalLayout.addWidget(self.fileBrowserLbl)
        self.followSymChBox = QtGui.QCheckBox(self.frame)
        self.followSymChBox.setChecked(True)
        self.followSymChBox.setObjectName("followSymChBox")
        self.verticalLayout.addWidget(self.followSymChBox)
        self.sessionLbl = QtGui.QLabel(self.frame)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.sessionLbl.setFont(font)
        self.sessionLbl.setObjectName("sessionLbl")
        self.verticalLayout.addWidget(self.sessionLbl)
        self.sessionLayout = QtGui.QHBoxLayout()
        self.sessionLayout.setObjectName("sessionLayout")
        self.saveRestoreSessionChBox = QtGui.QCheckBox(self.frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.saveRestoreSessionChBox.sizePolicy().hasHeightForWidth())
        self.saveRestoreSessionChBox.setSizePolicy(sizePolicy)
        self.saveRestoreSessionChBox.setChecked(True)
        self.saveRestoreSessionChBox.setObjectName("saveRestoreSessionChBox")
        self.sessionLayout.addWidget(self.saveRestoreSessionChBox)
        self.clearSessionBtn = QtGui.QPushButton(self.frame)
        self.clearSessionBtn.setObjectName("clearSessionBtn")
        self.sessionLayout.addWidget(self.clearSessionBtn)
        self.verticalLayout.addLayout(self.sessionLayout)
        self.updaterLbl = QtGui.QLabel(self.frame)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.updaterLbl.setFont(font)
        self.updaterLbl.setObjectName("updaterLbl")
        self.verticalLayout.addWidget(self.updaterLbl)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.checkUpdatesChBox = QtGui.QCheckBox(self.frame)
        self.checkUpdatesChBox.setChecked(True)
        self.checkUpdatesChBox.setObjectName("checkUpdatesChBox")
        self.horizontalLayout.addWidget(self.checkUpdatesChBox)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.channelLbl = QtGui.QLabel(self.frame)
        self.channelLbl.setObjectName("channelLbl")
        self.horizontalLayout.addWidget(self.channelLbl)
        self.channelCombo = QtGui.QComboBox(self.frame)
        self.channelCombo.setObjectName("channelCombo")
        self.channelCombo.addItem("")
        self.channelCombo.addItem("")
        self.horizontalLayout.addWidget(self.channelCombo)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.downUpdatesChBox = QtGui.QCheckBox(self.frame)
        self.downUpdatesChBox.setChecked(True)
        self.downUpdatesChBox.setObjectName("downUpdatesChBox")
        self.verticalLayout.addWidget(self.downUpdatesChBox)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.languageLbl = QtGui.QLabel(self.frame)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.languageLbl.setFont(font)
        self.languageLbl.setObjectName("languageLbl")
        self.horizontalLayout_2.addWidget(self.languageLbl)
        self.languageCombo = QtGui.QComboBox(self.frame)
        self.languageCombo.setObjectName("languageCombo")
        self.horizontalLayout_2.addWidget(self.languageCombo)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout_2.addWidget(self.frame)
        self.buttonBox = QtGui.QDialogButtonBox(settingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.RestoreDefaults|QtGui.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout_2.addWidget(self.buttonBox)

        settingsDialog.setWindowTitle(tr['SETTINGS_TITLE'])
        self.fileBrowserLbl.setText(tr['SETTINGS_FILE_BROWSER'])
        self.followSymChBox.setText(tr['SETTINGS_FOLLOW_SYMLINKS'])
        self.sessionLbl.setText(tr['SETTINGS_SESSION'])
        self.saveRestoreSessionChBox.setText(tr['SETTINGS_SAVE_RESTORE_SESSION'])
        self.clearSessionBtn.setText(tr['SETTINGS_CLEAR_SESSION'])
        self.updaterLbl.setText(tr['SETTINGS_UPDATER'])
        self.checkUpdatesChBox.setText(tr['SETTINGS_CHECK_UPDATES'])
        self.channelLbl.setText(tr['SETTINGS_UPDATER_CHANNEL'])
        self.channelCombo.setItemText(0, "Stable")
        self.channelCombo.setItemText(1, "Pre-releases")
        self.downUpdatesChBox.setText(tr['SETTINGS_AUTO_UPDATES'])
        self.languageLbl.setText(tr['SETTINGS_LANGUAGE'])

        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), settingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), settingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(settingsDialog)
