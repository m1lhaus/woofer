# -*- coding: utf-8 -*-

"""
Comment.
"""

__version__ = "$Id$"

import sys

from PySide.QtGui import *
from PySide.QtCore import *

import MainApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainApp.MainApp()
    main.show()
    app.exec_()