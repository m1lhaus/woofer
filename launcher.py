# -*- coding: utf-8 -*-

"""
Main application launcher.
"""

__version__ = "$Id$"

import logging
import components.log

components.log.setup_logging(u"PRODUCTION")
logger = logging.getLogger(__name__)

import sys

from PySide.QtGui import QApplication

from dialogs.main_dialog import MainApp

if __name__ == "__main__":
    logger.debug(u"Initializing application launcher")

    app = QApplication(sys.argv)
    app.setOrganizationName(u"WooferPlayer")
    app.setOrganizationDomain(u"wooferplayer.com")
    app.setApplicationName(u"Woofer")
    main = MainApp()
    main.show()
    app.exec_()