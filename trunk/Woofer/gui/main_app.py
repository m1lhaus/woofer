# -*- coding: utf-8 -*-

"""
Comment.
"""

__version__ = "$Id$"

from PySide.QtGui import *
from PySide.QtCore import *

from forms.mainform import Ui_MainWindow


class MainApp(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super(MainApp, self).__init__()
        self.setupUi(self)
