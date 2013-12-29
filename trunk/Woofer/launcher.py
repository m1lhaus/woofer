# -*- coding: utf-8 -*-

"""
Main application launcher.
"""

__version__ = "$Id$"

import logging
import components.log

components.log.setup_logging("PRODUCTION")
logger = logging.getLogger(__name__)

import sys

from PySide.QtGui import QApplication

from dialogs.main_app import MainApp

if __name__ == "__main__":
    logger.debug("Initializing application launcher")

    app = QApplication(sys.argv)
    main = MainApp()
    main.show()
    app.exec_()