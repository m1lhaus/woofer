# -*- coding: utf-8 -*-

"""
Comment.
"""

__version__ = "$Id$"

import sys

from PySide.QtGui import QApplication

import MainApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainApp.MainApp()
    main.show()
    app.exec_()