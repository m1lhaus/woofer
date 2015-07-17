# -*- coding: utf-8 -*-

import logging

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from forms.setting_form import Ui_settingsDialog

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog, Ui_settingsDialog):
    """
    Dialog where user can edit settings and preferences:
    """

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)

        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)

        self.settings = QSettings()

        self.followSymChBox.setChecked(self.settings.value(u"components/disk/RecursiveBrowser/follow_symlinks", False, bool))
        self.saveRestoreSessionChBox.setChecked(self.settings.value(u"session/saveRestoreSession", True, bool))
        self.saveRestoreSessionChBox.setEnabled(False)
        self.clearSessionBtn.setEnabled(False)
        self.checkUpdatesChBox.setChecked(self.settings.value(u"components/scheduler/Updater/check_updates", True, bool))
        self.downUpdatesChBox.setChecked(self.settings.value(u"components/scheduler/Updater/auto_updates", False, bool))
        current_idx = 1 if self.settings.value(u"components/scheduler/Updater/pre-release", False, bool) else 0
        self.channelCombo.setCurrentIndex(current_idx)

        self.setupSignals()

    def setupSignals(self):
        self.buttonBox.clicked.connect(self.buttonClicked)

    def resetDefaults(self):
        logger.debug(u"Resetting factory default settings to GUI")
        self.followSymChBox.setChecked(False)
        self.saveRestoreSessionChBox.setChecked(True)
        self.checkUpdatesChBox.setChecked(True)
        self.channelCombo.setCurrentIndex(0)
        self.downUpdatesChBox.setChecked(False)

    @pyqtSlot('QPushButton')
    def buttonClicked(self, button):
        """
        Called when some button from buttonBox is clicked.
        @type button: QPushButton
        """
        if self.buttonBox.buttonRole(button) == QDialogButtonBox.ResetRole:
            self.resetDefaults()

    @pyqtSlot()
    def accept(self):
        """
        Called when Save button is clicked.
        """
        logger.debug(u"Settings dialog accepted, updating and saving QSettings")

        self.settings.setValue(u"components/disk/RecursiveBrowser/follow_symlinks", self.followSymChBox.isChecked())
        self.settings.setValue(u"session/saveRestoreSession", self.saveRestoreSessionChBox.isChecked())
        self.settings.setValue(u"components/scheduler/Updater/check_updates", self.checkUpdatesChBox.isChecked())
        self.settings.setValue(u"components/scheduler/Updater/auto_updates", self.downUpdatesChBox.isChecked())
        pre_rls = True if self.channelCombo.currentIndex() == 1 else False
        self.settings.setValue(u"components/scheduler/Updater/pre-release", pre_rls)

        super(SettingsDialog, self).accept()