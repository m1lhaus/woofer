#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main application launcher. Method application_start(string) is used to start the application.
PRODUCTION mode is set as default if started from console.
"""

import sys
import os
import logging
import argparse

if sys.version_info < (3, 0):
    raise Exception("Application requires Python 3!")

try:
    import send2trash
except ImportError as e:
    raise Exception("%s! Send2Trash package is required!" % e.msg)

try:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
except ImportError as e:
    raise Exception("%s! PyQt5 library is required!" % e.msg)

# requirements for system-wide hooks
if os.name == 'posix':
    try:
        import Xlib
    except ImportError as e:
        raise Exception("%s! Python3-Xlib libraries are required on Linux platform!" % e.msg)


from components import libvlc               # import for libvlc check
from components import log
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Woofer player is free and open-source cross-platform music player.")

    # parser.add_argument("input", type=str,
    #                     help="Input JSON file with videos.")
    # parser.add_argument("extractors", type=str, nargs="+",
    #                     help="Image descriptors.")
    # parser.add_argument("-o", "--output", type=str, default="",
    #                     help="Output root directory where result will be stored in format: "
    #                          "'output_dir'/method/category/video.avi/data.npz")
    # optional
    # parser.add_argument("-j", "--jobs", type=int, default=1,
    #                     help="Number of parallel jobs (multiprocessing). ONLY FOR LOCAL USAGE!")
    # parser.add_argument("-p", "--priority", type=str, default="normal",
    #                     help="Process priority. Normal priority is set as default. ONLY FOR LOCAL USAGE!")
    parser.add_argument('-d', "--debug", action='store_true',
                        help="Debug/verbose mode. Prints debug information on screen.")

    args = parser.parse_args()

    env = 'DEBUG' if args.debug else 'PRODUCTION'
    log.setup_logging(env)
    logger.debug("Mode: '%s' Python '%s.%s.%s' PyQt: '%s' Qt: '%s'", env, sys.version_info[0], sys.version_info[1],
                 sys.version_info[2], PYQT_VERSION_STR, QT_VERSION_STR)

    # init Qt application
    app = QApplication(sys.argv)
    app.setOrganizationName("WooferPlayer")
    app.setOrganizationDomain("wooferplayer.com")
    app.setApplicationName("Woofer")

    sharedMemoryLock, error_str = obtainSharedMemoryLock()

    # init check
    if not sharedMemoryLock:
        displayAnotherInstanceError(error_str)
    elif not foundLibVLC():
        displayLibVLCError(os.name)
    else:

        # run the application
        mainApp = main_dialog.MainApp()
        mainApp.show()

        logger.debug("Starting MainThread loop...")
        app.exec_()
        logger.debug("MainThread loop stopped. Application has been closed successfully.")