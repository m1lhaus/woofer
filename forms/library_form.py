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
All GUI components from library dialog initialized here.
"""

import logging

from PyQt4.QtGui import *
from PyQt4.QtCore import *

logger = logging.getLogger(__name__)


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