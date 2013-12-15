# -*- coding: utf-8 -*-

"""
Main application GUI module
"""

__version__ = "$Id$"

import logging

from PySide.QtGui import *
from PySide.QtCore import *

from forms.mainform import Ui_MainWindow

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class MainApp(QMainWindow, Ui_MainWindow):
    """
    Main application GUI form.
    - setup main window dialog
    - connects signals from dialogs widgets
    """

    def __init__(self):
        super(MainApp, self).__init__()
        self.setupUi(self)
