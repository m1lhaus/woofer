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

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from components.translator import tr

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
        self.buttonBox.button(QDialogButtonBox.Save).setText(tr['BUTTON_SAVE'])
        self.buttonBox.button(QDialogButtonBox.Cancel).setText(tr['BUTTON_CANCEL'])
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 2)

        self.retranslateUi(libraryDialog)

    def retranslateUi(self, libraryDialog):
        libraryDialog.setWindowTitle(tr['MEDIA_LIBRARY'])
        self.label.setText(tr['ADD_MEDIALIB_FOLDER_LBL'])
        self.addBtn.setText(tr['ADD'])
        self.removeBtn.setText(tr['REMOVE'])