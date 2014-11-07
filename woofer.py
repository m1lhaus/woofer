#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main application launcher. Method application_start(string) is used to start the application.
PRODUCTION mode is set as default if started from console.
"""

__version__ = "$Id: woofer.py 141 2014-10-25 20:40:10Z m1lhaus $"

import sys
import os
import logging
import components.log


if sys.version_info < (2, 7) or sys.version_info >= (3, 0):
    raise Exception(u"Application requires Python 2.7!")

try:
    import sip
except ImportError, e:
    raise Exception(u"%s! Sip package (PyQt4) is required!" % e.message)
else:
    # set PyQt API to v2
    sip.setapi('QDate', 2)
    sip.setapi('QDateTime', 2)
    sip.setapi('QString', 2)
    sip.setapi('QTextStream', 2)
    sip.setapi('QTime', 2)
    sip.setapi('QUrl', 2)
    sip.setapi('QVariant', 2)

try:
    import send2trash
except ImportError, e:
    raise Exception(u"%s! Send2Trash package is required!" % e.message)

try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except ImportError, e:
    raise Exception(u"%s! PyQt4 library is required!" % e.message)

# requirements for system-wide hooks
if os.name == 'nt':
    try:
        import pythoncom
        import pywintypes
    except ImportError, e:
        raise Exception(u"%s! PyWin32 libraries (package) are required on Windows platform!" % e.message)

    try:
        import pyHook
    except ImportError, e:
        raise Exception(u"%s! pyHook package is required on Windows platform!" % e.message)

elif os.name == 'posix':
    try:
        import Xlib
    except ImportError, e:
        raise Exception(u"%s! Python-Xlib libraries are required on Linux platform!" % e.message)


import components.libvlc               # import for libvlc check
from dialogs import main_dialog


logger = logging.getLogger(__name__)


def obtainSharedMemoryLock():
    logger.debug(u"Checking if another instance is running...")

    shareMemoryLock = QSharedMemory()
    shareMemoryLock.setKey(u"wooferplayer.com")
    if shareMemoryLock.attach(QSharedMemory.ReadOnly):
        return None, ""

    logger.debug(u"Trying to create shared memory segment for id 'wooferplayer.com'")
    if not shareMemoryLock.create(1, QSharedMemory.ReadOnly):
        return None, shareMemoryLock.errorString()

    logger.debug(u"No other instance is running.")
    return shareMemoryLock, ""


def foundLibVLC():
    """
    Check if libvlc.py found valid dll.
    @rtype: bool
    """
    if components.libvlc.dll is not None:
        logger.debug(u"Using libvlc.dll found at: %s", components.libvlc.plugin_path)
        return True
    else:
        return False


def displayAnotherInstanceError(error_str):
    if not error_str:
        logger.debug(u"Another instance of Woofer Player is running! Closing application.")
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle(u"Another instance is running")
        msgBox.setText(u"Another instance of Woofer player is running.")
        msgBox.setInformativeText(u"If no instance of Woofer player is running, "
                                  u"please contact us on www.wooferplayer.com")
        msgBox.exec_()
    else:
        logger.error(u"Unable to create shared memory segment, reason: %s", error_str)
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setWindowTitle(u"Initialization error")
        msgBox.setText(u"Unable to create shared memory segment.\nReason: %s" % error_str)
        msgBox.setInformativeText(u"Please contact us on www.wooferplayer.com for further information.")
        msgBox.exec_()


def displayLibVLCError(platform):
    if platform == 'nt':
        logger.error(u"LibVLC dll not found, dll instance is None! Working path: %s" % os.getcwd())
        msgBox = QMessageBox()
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setWindowTitle(u"Critical error")
        msgBox.setText(u"Woofer player was unable to find core playback DLL libraries!")
        msgBox.setInformativeText(u"If you are using distributed binary package, "
                                  u"please report this issue on www.wooferplayer.com immediately. "
                                  u"You can try to install "
                                  u"<a href='http://www.videolan.org/vlc/#download'>VLC media player</a> "
                                  u"as temporary workaround. Woofer player can use their libraries.")
        msgBox.exec_()
    elif platform == 'posix':
        logger.warning(u"Libvlc background not found!")
        msgBox = QMessageBox()
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle(u"Dependency not found")
        msgBox.setText(u"Woofer player was unable to find core LibVLC libraries!")
        msgBox.setInformativeText(u"Please install appropriate VLC media player 2.x from your repository "
                                  u"or you can download last version directly from "
                                  u"<a href='http://www.videolan.org/vlc/#download'>VideoLAN</a>.")
        msgBox.exec_()
    else:
        raise NotImplementedError("Unknown platform: %s" % platform)


# *******************************************
# APPLICATION LAUNCHER
# *******************************************
def startApplication(environment):
    """
    Initializes Qt libraries and Woofer application.
    @param environment: DEBUG or PRODUCTION string is expected
    """
    components.log.setup_logging(environment)
    logger.debug(u"Logger mode set to %s, now initializing main application loop.", environment)

    # init Qt application
    app = QApplication(sys.argv)
    app.setOrganizationName(u"WooferPlayer")
    app.setOrganizationDomain(u"wooferplayer.com")
    app.setApplicationName(u"Woofer")

    sharedMemoryLock, error_str = obtainSharedMemoryLock()
    if not sharedMemoryLock:
        displayAnotherInstanceError(error_str)
        return True

    if not foundLibVLC():
        displayLibVLCError(os.name)
        return True

    # run the application
    mainApp = main_dialog.MainApp()
    mainApp.show()

    logger.debug(u"Starting MainThread loop...")
    app.exec_()
    logger.debug(u"MainThread loop stopped. Application has been closed successfully.")


if __name__ == "__main__":
    startApplication('PRODUCTION')