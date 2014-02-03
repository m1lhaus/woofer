# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uic\library.ui'
#
# Created: Thu Jan 30 16:52:36 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_libraryDialog(object):
    def setupUi(self, libraryDialog):
        libraryDialog.setObjectName("libraryDialog")
        libraryDialog.resize(480, 256)
        self.gridLayout = QtGui.QGridLayout(libraryDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtGui.QLabel(libraryDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.folderList = QtGui.QListWidget(libraryDialog)
        self.folderList.setObjectName("folderList")
        self.gridLayout.addWidget(self.folderList, 1, 0, 1, 1)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.addBtn = QtGui.QPushButton(libraryDialog)
        self.addBtn.setObjectName("addBtn")
        self.verticalLayout.addWidget(self.addBtn)
        self.removeBtn = QtGui.QPushButton(libraryDialog)
        self.removeBtn.setObjectName("removeBtn")
        self.verticalLayout.addWidget(self.removeBtn)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.gridLayout.addLayout(self.verticalLayout, 1, 1, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(libraryDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 2)

        self.retranslateUi(libraryDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), libraryDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), libraryDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(libraryDialog)

    def retranslateUi(self, libraryDialog):
        libraryDialog.setWindowTitle(QtGui.QApplication.translate("libraryDialog", "Media libraries", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("libraryDialog", "Add folders for quick access:", None, QtGui.QApplication.UnicodeUTF8))
        self.addBtn.setText(QtGui.QApplication.translate("libraryDialog", "Add", None, QtGui.QApplication.UnicodeUTF8))
        self.removeBtn.setText(QtGui.QApplication.translate("libraryDialog", "Remove", None, QtGui.QApplication.UnicodeUTF8))

