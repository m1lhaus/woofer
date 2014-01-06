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

from dialogs.main_dialog import MainApp

if __name__ == "__main__":
    logger.debug("Initializing application launcher")

    app = QApplication(sys.argv)
    app.setApplicationName("Woofer")

    main = MainApp()
    main.show()

    app.exec_()