# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uic\settings.ui'
#
# Created: Sun Nov 15 19:34:03 2015
#      by: PyQt4 UI code generator 4.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_settingsDialog(object):
    def setupUi(self, settingsDialog):
        settingsDialog.setObjectName(_fromUtf8("settingsDialog"))
        settingsDialog.resize(351, 251)
        settingsDialog.setModal(True)
        self.verticalLayout_2 = QtGui.QVBoxLayout(settingsDialog)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.frame = QtGui.QFrame(settingsDialog)
        self.frame.setFrameShape(QtGui.QFrame.Box)
        self.frame.setFrameShadow(QtGui.QFrame.Sunken)
        self.frame.setObjectName(_fromUtf8("frame"))
        self.verticalLayout = QtGui.QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.fileBrowserLbl = QtGui.QLabel(self.frame)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.fileBrowserLbl.setFont(font)
        self.fileBrowserLbl.setObjectName(_fromUtf8("fileBrowserLbl"))
        self.verticalLayout.addWidget(self.fileBrowserLbl)
        self.followSymChBox = QtGui.QCheckBox(self.frame)
        self.followSymChBox.setChecked(True)
        self.followSymChBox.setObjectName(_fromUtf8("followSymChBox"))
        self.verticalLayout.addWidget(self.followSymChBox)
        self.sessionLbl = QtGui.QLabel(self.frame)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.sessionLbl.setFont(font)
        self.sessionLbl.setObjectName(_fromUtf8("sessionLbl"))
        self.verticalLayout.addWidget(self.sessionLbl)
        self.sessionLayout = QtGui.QHBoxLayout()
        self.sessionLayout.setObjectName(_fromUtf8("sessionLayout"))
        self.saveRestoreSessionChBox = QtGui.QCheckBox(self.frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.saveRestoreSessionChBox.sizePolicy().hasHeightForWidth())
        self.saveRestoreSessionChBox.setSizePolicy(sizePolicy)
        self.saveRestoreSessionChBox.setChecked(True)
        self.saveRestoreSessionChBox.setObjectName(_fromUtf8("saveRestoreSessionChBox"))
        self.sessionLayout.addWidget(self.saveRestoreSessionChBox)
        self.clearSessionBtn = QtGui.QPushButton(self.frame)
        self.clearSessionBtn.setObjectName(_fromUtf8("clearSessionBtn"))
        self.sessionLayout.addWidget(self.clearSessionBtn)
        self.verticalLayout.addLayout(self.sessionLayout)
        self.updaterLbl = QtGui.QLabel(self.frame)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.updaterLbl.setFont(font)
        self.updaterLbl.setObjectName(_fromUtf8("updaterLbl"))
        self.verticalLayout.addWidget(self.updaterLbl)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.checkUpdatesChBox = QtGui.QCheckBox(self.frame)
        self.checkUpdatesChBox.setChecked(True)
        self.checkUpdatesChBox.setObjectName(_fromUtf8("checkUpdatesChBox"))
        self.horizontalLayout.addWidget(self.checkUpdatesChBox)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.channelLbl = QtGui.QLabel(self.frame)
        self.channelLbl.setObjectName(_fromUtf8("channelLbl"))
        self.horizontalLayout.addWidget(self.channelLbl)
        self.channelCombo = QtGui.QComboBox(self.frame)
        self.channelCombo.setObjectName(_fromUtf8("channelCombo"))
        self.channelCombo.addItem(_fromUtf8(""))
        self.channelCombo.addItem(_fromUtf8(""))
        self.horizontalLayout.addWidget(self.channelCombo)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.downUpdatesChBox = QtGui.QCheckBox(self.frame)
        self.downUpdatesChBox.setChecked(True)
        self.downUpdatesChBox.setObjectName(_fromUtf8("downUpdatesChBox"))
        self.verticalLayout.addWidget(self.downUpdatesChBox)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.languageLbl = QtGui.QLabel(self.frame)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.languageLbl.setFont(font)
        self.languageLbl.setObjectName(_fromUtf8("languageLbl"))
        self.horizontalLayout_2.addWidget(self.languageLbl)
        self.languageCombo = QtGui.QComboBox(self.frame)
        self.languageCombo.setObjectName(_fromUtf8("languageCombo"))
        self.horizontalLayout_2.addWidget(self.languageCombo)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout_2.addWidget(self.frame)
        self.buttonBox = QtGui.QDialogButtonBox(settingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.RestoreDefaults|QtGui.QDialogButtonBox.Save)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout_2.addWidget(self.buttonBox)

        self.retranslateUi(settingsDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), settingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), settingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(settingsDialog)

    def retranslateUi(self, settingsDialog):
        settingsDialog.setWindowTitle(_translate("settingsDialog", "Settings", None))
        self.fileBrowserLbl.setText(_translate("settingsDialog", "File browser:", None))
        self.followSymChBox.setText(_translate("settingsDialog", "Follow symbolic links", None))
        self.sessionLbl.setText(_translate("settingsDialog", "Session:", None))
        self.saveRestoreSessionChBox.setText(_translate("settingsDialog", "Automatically save and restore last session", None))
        self.clearSessionBtn.setText(_translate("settingsDialog", "Clear session", None))
        self.updaterLbl.setText(_translate("settingsDialog", "Updater:", None))
        self.checkUpdatesChBox.setText(_translate("settingsDialog", "Automatically check updates", None))
        self.channelLbl.setText(_translate("settingsDialog", "Channel:", None))
        self.channelCombo.setItemText(0, _translate("settingsDialog", "Stable", None))
        self.channelCombo.setItemText(1, _translate("settingsDialog", "Pre-releases", None))
        self.downUpdatesChBox.setText(_translate("settingsDialog", "Automatically download and install new updates", None))
        self.languageLbl.setText(_translate("settingsDialog", "Language:", None))

