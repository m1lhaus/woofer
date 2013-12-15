# -*- coding: utf-8 -*-

"""
Main application debug launcher.
"""

__version__ = "$Id: launcher.py 6 2013-10-05 15:51:01Z m1lhaus $"

import logging
import components.log

components.log.setup_logging("DEBUG")
logger = logging.getLogger(__name__)

import sys

from PySide.QtGui import QApplication

from dialogs.main_app import MainApp

if __name__ == "__main__":
    logger.debug("Initializing application launcher in debug mode")

    app = QApplication(sys.argv)
    main = MainApp()
    main.show()
    app.exec_()