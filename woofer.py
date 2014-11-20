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

import components.log
import tools

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

if os.name == 'posix':
    try:
        import Xlib
    except ImportError, e:
        raise Exception(u"%s! Python-Xlib libraries are required on Linux platform!" % e.message)


import components.libvlc               # import for libvlc check
import components.localserver
from dialogs import main_dialog


logger = logging.getLogger(__name__)


def foundLibVLC():
    """
    Check if libvlc.py found valid dll.
    @rtype: bool
    """
    if components.libvlc.dll is not None:
        logger.debug(u"Using libvlc.dll found at: %s", unicode(str(components.libvlc.plugin_path), sys.getfilesystemencoding()))
        return True
    else:
        return False


def findCmdHelpFile():
    if os.path.isfile('cmdargs.exe'):      # built exe dist
        return 'cmdargs.exe'
    elif os.path.isfile('cmdargs.py'):
        return 'cmdargs.py'
    else:
        raise Exception(u"Script cmdargs.py/exe was not found!")


def displayLibVLCError(platform):
    if platform == 'nt':
        logger.error(u"LibVLC dll not found, dll instance is None! Root path: %s" % tools.APP_ROOT_DIR)
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


def displayLoggerError(e_msg):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setWindowTitle(u"Critical error")
        msgBox.setText(u"Initialization of logger component failed. "
                       u"The application doesn't seem to have write permissions.")
        msgBox.setInformativeText(u"Details:\n" + e_msg)
        msgBox.exec_()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=u"Woofer player is free and open-source cross-platform music player.",
                                     add_help=False)
    parser.add_argument('input', nargs='?', type=str,
                        help='Media file path.')
    parser.add_argument('-d', "--debug", action='store_true',
                        help=u"debug/verbose mode")
    parser.add_argument('-h', "--help", action='store_true',
                        help=u"show this help message and exit")
    args = parser.parse_args()

    env = 'DEBUG' if args.debug else 'PRODUCTION'

    # init Qt application
    app = QApplication(sys.argv)
    app.setOrganizationName("WooferPlayer")
    app.setOrganizationDomain("wooferplayer.com")
    app.setApplicationName("Woofer")

    try:
        components.log.setup_logging(env)
    except Exception as exception:
        displayLoggerError(unicode(str(exception), sys.getfilesystemencoding()))
        sys.exit(-1)

    logger.debug(u"Mode: '%s' Python '%s.%s.%s' PyQt: '%s' Qt: '%s'", env, sys.version_info[0], sys.version_info[1],
                 sys.version_info[2], PYQT_VERSION_STR, QT_VERSION_STR)

    # if -h/--help console argument is given, display help content
    if args.help:
        logger.debug(u"Help cmd arg given, opening cmd help file...")
        cmd_args_file = findCmdHelpFile()

        # if not running built win32 dist
        if not tools.IS_WIN32_EXE:
            parser.print_help()

        # win32gui apps has no stdout/stderr, so cmd help has to be opened in new window
        elif cmd_args_file:
            os.startfile(cmd_args_file)         # opens console application window with help

        else:
            logger.error(u"File cmdargs.exe/cmdargs.py not found!")

        sys.exit(0)

    # start server and detect another instance
    applicationServer = components.localserver.LocalServer("wooferplayer.com")
    if applicationServer.another_instance_running:
        if args.input:
            applicationServer.sendMessage(r"play %s" % args.input)
        else:
            applicationServer.sendMessage(r"open")

    elif not foundLibVLC():
        displayLibVLCError(os.name)

    else:
        mainApp = main_dialog.MainApp(env, args.input)
        applicationServer.messageReceivedSignal.connect(mainApp.messageFromAnotherInstance)
        mainApp.show()
        app.exec_()

        logger.debug(u"MainThread loop stopped.")

    if not applicationServer.exit():
        logger.error(u"Local server components are not closed properly!")

    logger.debug(u"Application has been closed")
    logging.shutdown()