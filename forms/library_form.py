# -*- coding: utf-8 -*-

"""
All GUI components from library dialog initialized here.
"""

import logging

from PyQt4.QtGui import *
from PyQt4.QtCore import *

logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)


class Ui_libraryDialog(object):
    def setupUi(self, libraryDialog):
        libraryDialog.setObjectName("libraryDialog")
        libraryDialog.resize(480, 256)
        libraryDialog.setWindowFlags(libraryDialog.windowFlags() ^ Qt.WindowContextHelpButtonHint)

        self.gridLayout = QGridLayout(libraryDialog)

        self.label = QLabel(libraryDialog)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.folderList = QListWidget(libraryDialog)
        self.gridLayout.addWidget(self.folderList, 1, 0, 1, 1)

        # ADD and REMOVE buttons
        self.verticalLayout = QVBoxLayout()
        self.addBtn = QPushButton(libraryDialog)
        self.verticalLayout.addWidget(self.addBtn)
        self.removeBtn = QPushButton(libraryDialog)
        self.verticalLayout.addWidget(self.removeBtn)
        spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.gridLayout.addLayout(self.verticalLayout, 1, 1, 1, 1)

        self.buttonBox = QDialogButtonBox(libraryDialog)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 2)

        self.retranslateUi(libraryDialog)

    def retranslateUi(self, libraryDialog):
        libraryDialog.setWindowTitle(u"Media library")
        self.label.setText(u"Add folders for quick access:")
        self.addBtn.setText(u"Add")
        self.removeBtn.setText(u"Remove")