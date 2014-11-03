#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main application launcher. Method application_start(string) is used to start the application.
PRODUCTION mode is set as default if started from console.
"""


import sys
import os
import logging
import components.log


if sys.version_info < (3, 0):
    raise Exception("Application requires Python 3!")

# try:
#     import sip
# except ImportError as e:
#     raise Exception("%s! Sip package (PyQt4) is required!" % e.message)
# else:
#     # set PyQt API to v2
#     sip.setapi('QDate', 2)
#     sip.setapi('QDateTime', 2)
#     sip.setapi('QString', 2)
#     sip.setapi('QTextStream', 2)
#     sip.setapi('QTime', 2)
#     sip.setapi('QUrl', 2)
#     sip.setapi('QVariant', 2)

try:
    import send2trash
except ImportError as e:
    raise Exception("%s! Send2Trash package is required!" % e.message)

try:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
except ImportError as e:
    raise Exception("%s! PyQt4 library is required!" % e.message)

# requirements for system-wide hooks
if os.name == 'nt':
    try:
        import pywintypes
        import pythoncom
    except ImportError as e:
        raise Exception("%s! PyWin32 libraries (package) are required on Windows platform!" % e.message)

    try:
        import pyHook
    except ImportError as e:
        raise Exception("%s! pyHook package is required on Windows platform!" % e.message)

elif os.name == 'posix':
    try:
        import Xlib
    except ImportError as e:
        raise Exception("%s! Python-Xlib libraries are required on Linux platform!" % e.message)


import components.libvlc as libvlc               # import for libvlc check
from dialogs import main_dialog


logger = logging.getLogger(__name__)


def obtainSharedMemoryLock():
    logger.debug("Checking if another instance is running...")

    shareMemoryLock = QSharedMemory()
    shareMemoryLock.setKey("wooferplayer.com")
    if shareMemoryLock.attach(QSharedMemory.ReadOnly):
        return None, ""

    logger.debug("Trying to create shared memory segment for id 'wooferplayer.com'")
    if not shareMemoryLock.create(1, QSharedMemory.ReadOnly):
        return None, shareMemoryLock.errorString()

    logger.debug("No other instance is running.")
    return shareMemoryLock, ""


def foundLibVLC():
    """
    Check if libvlc.py found valid dll.
    @rtype: bool
    """
    if libvlc.dll is not None:
        logger.debug("Using libvlc.dll found at: %s", libvlc.plugin_path)
        return True
    else:
        return False


def displayAnotherInstanceError(error_str):
    if not error_str:
        logger.debug("Another instance of Woofer Player is running! Closing application.")
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle("Another instance is running")
        msgBox.setText("Another instance of Woofer player is running.")
        msgBox.setInformativeText("If no instance of Woofer player is running, "
                                  "please contact us on www.wooferplayer.com")
        msgBox.exec_()
    else:
        logger.error("Unable to create shared memory segment, reason: %s", error_str)
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setWindowTitle("Initialization error")
        msgBox.setText("Unable to create shared memory segment.\nReason: %s" % error_str)
        msgBox.setInformativeText("Please contact us on www.wooferplayer.com for further information.")
        msgBox.exec_()


def displayLibVLCError(platform):
    if platform == 'nt':
        logger.error("LibVLC dll not found, dll instance is None! Working path: %s" % os.getcwd())
        msgBox = QMessageBox()
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setWindowTitle("Critical error")
        msgBox.setText("Woofer player was unable to find core playback DLL libraries!")
        msgBox.setInformativeText("If you are using distributed binary package, "
                                  "please report this issue on www.wooferplayer.com immediately. "
                                  "You can try to install "
                                  "<a href='http://www.videolan.org/vlc/#download'>VLC media player</a> "
                                  "as temporary workaround. Woofer player can use their libraries.")
        msgBox.exec_()
    elif platform == 'posix':
        logger.warning("Libvlc background not found!")
        msgBox = QMessageBox()
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle("Dependency not found")
        msgBox.setText("Woofer player was unable to find core LibVLC libraries!")
        msgBox.setInformativeText("Please install appropriate VLC media player 2.x from your repository "
                                  "or you can download last version directly from "
                                  "<a href='http://www.videolan.org/vlc/#download'>VideoLAN</a>.")
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
    logger.debug("Logger mode set to %s, now initializing main application loop.", environment)

    # init Qt application
    app = QApplication(sys.argv)
    app.setOrganizationName("WooferPlayer")
    app.setOrganizationDomain("wooferplayer.com")
    app.setApplicationName("Woofer")

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

    logger.debug("Starting MainThread loop...")
    app.exec_()
    logger.debug("MainThread loop stopped. Application has been closed successfully.")


if __name__ == "__main__":
    startApplication('PRODUCTION')