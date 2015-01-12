# -*- coding: utf-8 -*-

"""
This is a template for GUI test.
"""

import sys
import os
import unittest


import sip
# set PyQt API to v2
sip.setapi('QDate', 2)
sip.setapi('QDateTime', 2)
sip.setapi('QString', 2)
sip.setapi('QTextStream', 2)
sip.setapi('QTime', 2)
sip.setapi('QUrl', 2)
sip.setapi('QVariant', 2)

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtTest import QTest


# set sys.argv like application is being launched normally
root_launcher = os.path.abspath(os.path.join("..", "..", "woofer.py"))
assert os.path.isfile(root_launcher)
sys.argv = [root_launcher]


class UserInterfaceTest(unittest.TestCase):
    def setUp(self):
        self.app = QApplication(sys.argv)
        self.app.setOrganizationName("WooferPlayer")
        self.app.setOrganizationDomain("com.woofer.player")
        self.app.setApplicationName("Woofer")
        QSettings().clear()

        import dialogs.main_dialog
        self.mainApp = dialogs.main_dialog.MainApp('PRODUCTION', None)

    def test_something(self):
        self.fail()

    def test_close(self):
        self.mainApp.close()
        self.app.quit()
