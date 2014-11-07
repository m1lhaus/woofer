#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main application launcher. Method application_start(string) is used to start the application.
PRODUCTION mode is set as default if started from console.
"""

import sys
import argparse
import os
import logging

from components import log


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


def findCmdHelpFile():
    cmd_args_file = None
    exe = False
    if os.path.isfile('cmdargs.exe'):      # built exe dist
        cmd_args_file = 'cmdargs.exe'
        exe = True
    elif os.path.isfile('cmdargs.py'):
        cmd_args_file = 'cmdargs.py'

    return cmd_args_file, exe


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
        logger.error(u"LibVLC dll not found, dll instance is None! Root path: %s" % os.path.dirname(os.path.realpath(sys.argv[0])))
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
        raise NotImplementedError(u"Unknown platform: %s" % platform)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=u"Woofer player is free and open-source cross-platform music player.",
                                     add_help=False)
    parser.add_argument('-d', "--debug", action='store_true',
                        help=u"debug/verbose mode")
    parser.add_argument('-h', "--help", action='store_true',
                        help=u"show this help message and exit")
    args = parser.parse_args()

    env = 'DEBUG' if args.debug else 'PRODUCTION'
    log.setup_logging(env)
    logger.debug(u"Mode: '%s' Python '%s.%s.%s' PyQt: '%s' Qt: '%s'", env, sys.version_info[0], sys.version_info[1],
                 sys.version_info[2], PYQT_VERSION_STR, QT_VERSION_STR)

    # if -h/--help console argument is given, display help content
    if args.help:
        logger.debug(u"Help cmd arg given, opening cmd help file...")
        cmd_args_file, exe = findCmdHelpFile()

        # if not running built win32 dist
        if not exe:
            parser.print_help()

        # win32gui apps has no stdout/stderr, so cmd help has to be opened in new window
        elif cmd_args_file:
            os.startfile(cmd_args_file)         # opens console application window with help

        else:
            logger.error(u"File cmdargs.exe/cmdargs.py not found!")

        sys.exit(0)

    # init Qt application
    app = QApplication(sys.argv)
    app.setOrganizationName(u"WooferPlayer")
    app.setOrganizationDomain(u"wooferplayer.com")
    app.setApplicationName(u"Woofer")

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

        logger.debug(u"Starting MainThread loop...")
        app.exec_()
        logger.debug(u"MainThread loop stopped. Application has been closed successfully.")