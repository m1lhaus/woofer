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

import os
import sys
import logging

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import tools

from forms.setting_form import Ui_settingsDialog
from components.translator import tr

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog, Ui_settingsDialog):
    """
    Dialog where user can edit application settings and preferences
    """

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)

        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)

        if not sys.platform.startswith('win') or not tools.IS_WIN32_EXE:
            self.updaterLbl.setText(self.updaterLbl.text() + " " + tr['SETTINGS_UPDATES_DISABLED'])
            self.updaterLbl.setVisible(False)
            self.checkUpdatesChBox.setEnabled(False)
            self.checkUpdatesChBox.setVisible(False)
            self.downUpdatesChBox.setEnabled(False)
            self.downUpdatesChBox.setVisible(False)
            self.channelCombo.setEnabled(False)
            self.channelCombo.setVisible(False)
            self.channelLbl.setEnabled(False)
            self.channelLbl.setVisible(False)

        self.settings = QSettings()

        self.followSymChBox.setChecked(self.settings.value("components/disk/RecursiveBrowser/follow_symlinks", False, bool))
        self.saveRestoreSessionChBox.setChecked(self.settings.value("session/saveRestoreSession", True, bool))
        self.saveRestoreSessionChBox.setEnabled(False)
        self.clearSessionBtn.setEnabled(False)
        self.checkUpdatesChBox.setChecked(self.settings.value("components/scheduler/Updater/check_updates", True, bool))
        self.downUpdatesChBox.setChecked(self.settings.value("components/scheduler/Updater/auto_updates", False, bool))
        current_idx = 1 if self.settings.value("components/scheduler/Updater/pre-release", False, bool) else 0
        self.channelCombo.setCurrentIndex(current_idx)

        self.lang_files = os.listdir(os.path.join(tools.APP_ROOT_DIR, "lang"))
        current_lang = os.path.basename(tr.langfile)
        default_lang = os.path.basename(tr.default_langfile)
        try:
            current_idx = self.lang_files.index(current_lang)
        except ValueError:
            logger.warning("Current language %s cannot be found in lang. files", current_lang)
            current_idx = self.lang_files.index(default_lang)

        self.languageCombo.addItems(self.lang_files)
        self.languageCombo.setCurrentIndex(current_idx)

        self.setupSignals()

    def setupSignals(self):
        self.buttonBox.clicked.connect(self.buttonClicked)
        self.checkUpdatesChBox.stateChanged.connect(self.disableAutoUpdates)

    def resetDefaults(self):
        """
        Reset all GUI elements to their default values.
        Dialog must be accepted to propagate default settings to QSettings.
        """
        logger.debug("Resetting factory default settings to GUI")
        self.followSymChBox.setChecked(False)
        self.saveRestoreSessionChBox.setChecked(True)
        self.checkUpdatesChBox.setChecked(True)
        self.channelCombo.setCurrentIndex(0)
        self.downUpdatesChBox.setChecked(False)
        default_lang = os.path.basename(tr.default_langfile)
        self.languageCombo.setCurrentIndex(self.lang_files.index(default_lang))

    @pyqtSlot(QAbstractButton)
    def buttonClicked(self, button):
        """
        Called when some button from buttonBox is clicked.
        @type button: QPushButton
        """
        if self.buttonBox.buttonRole(button) == QDialogButtonBox.ResetRole:
            self.resetDefaults()

    @pyqtSlot(int)
    def disableAutoUpdates(self, update_check):
        """
        Called when user enables/disables checking for application updates.
        If checking for updates is turned off, then automatic updates (implicitly turned off) option is disabled .
        @param update_check: checkbox state - see Qt::CheckState
        """
        self.downUpdatesChBox.setEnabled(True if update_check == Qt.Checked else False)

    @pyqtSlot()
    def accept(self):
        """
        Called when Save button is clicked.
        """
        logger.debug("Settings dialog accepted, updating and saving QSettings")
        restart_dialog = False

        self.settings.setValue("components/disk/RecursiveBrowser/follow_symlinks", self.followSymChBox.isChecked())
        self.settings.setValue("session/saveRestoreSession", self.saveRestoreSessionChBox.isChecked())
        self.settings.setValue("components/scheduler/Updater/check_updates", self.checkUpdatesChBox.isChecked())
        self.settings.setValue("components/scheduler/Updater/auto_updates", self.downUpdatesChBox.isChecked())
        pre_rls = True if self.channelCombo.currentIndex() == 1 else False
        self.settings.setValue("components/scheduler/Updater/pre-release", pre_rls)
        language = self.languageCombo.currentText()
        old_language = self.settings.value("components/translator/Translator/language", "en_US.ini")
        if language != old_language:
            self.settings.setValue("components/translator/Translator/language", language)
            restart_dialog = True

        if restart_dialog:
            QMessageBox.information(self, "Woofer player", tr['INFO_RESTART_WOOFER'])

        super(SettingsDialog, self).accept()