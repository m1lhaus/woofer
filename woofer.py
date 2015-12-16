#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Woofer - free open-source cross-platform music player
# Copyright (C) 2015 Milan Herbig <milanherbig[at]gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

"""
Main application launcher. Method application_start(string) is used to start the application.
PRODUCTION mode is set as default if started from console.
"""

import sys
import argparse
import os
import logging

import components.log
import components.translator
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
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except ImportError, e:
    raise Exception(u"%s! PyQt4 library is required!" % e.message)

try:
    import send2trash
except ImportError, e:
    raise Exception(u"%s! Send2Trash package is required!" % e.message)

try:
    import ujson
except ImportError, e:
    raise Exception(u"%s! ujson package is required!" % e.message)

if os.name == 'posix':
    try:
        import Xlib
    except ImportError, e:
        raise Exception(u"%s! Python-Xlib libraries are required on Linux platform!" % e.message)


logger = logging.getLogger(__name__)


def foundLibVLC():
    """
    Check if libvlc.py found valid dll.
    @rtype: bool
    """
    if components.libvlc.dll is not None:
        logger.debug(u"Using libvlc.dll found at: %s",
                     unicode(str(components.libvlc.plugin_path), sys.getfilesystemencoding()))
        return True
    else:
        return False


def findCmdHelpFile():
    if os.path.isfile(os.path.join(tools.APP_ROOT_DIR, 'cmdargs.exe')):      # built exe dist
        return os.path.join(tools.APP_ROOT_DIR, 'cmdargs.exe')
    elif os.path.isfile(os.path.join(tools.APP_ROOT_DIR, 'cmdargs.py')):
        return os.path.join(tools.APP_ROOT_DIR, 'cmdargs.py')
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
                                  u"please report this issue on http://m1lhaus.github.io/woofer immediately. "
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
                       u"The application probably doesn't have write permissions.")
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
    app.setOrganizationDomain("com.woofer.player")
    app.setApplicationName("Woofer")
    # QSettings().clear()

    # init logging module
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
        else:
            os.startfile(cmd_args_file)         # opens console application window with help

        logging.shutdown()                      # quit application
        sys.exit()

    # start server and detect another instance
    import components.network
    applicationServer = components.network.LocalServer("com.woofer.player")
    try:
        if applicationServer.another_instance_running:
            if args.input:
                applicationServer.sendMessage(r"play %s" % args.input)      # play input file immediately
            else:
                applicationServer.sendMessage(r"open")                      # raise application on top
            raise Exception(u"Another instance is running")

        # init LibVLC binaries
        import components.libvlc            # import for libvlc check
        if not foundLibVLC():
            displayLibVLCError(os.name)
            raise Exception(u"LibVLC libraries not found")

        # init translator module
        settings = QSettings()
        lang_code = settings.value("components/translator/Translator/language", "en_US.ini")
        tr = components.translator.init(lang_code)

        # start gui application
        import dialogs.main_dialog
        logger.debug(u"Initializing gui application and all components...")
        mainApp = dialogs.main_dialog.MainApp(env, args.input)
        applicationServer.messageReceivedSignal.connect(mainApp.messageFromAnotherInstance)
        mainApp.show()
        app.exec_()

        logger.debug(u"MainThread loop stopped.")
    finally:
        if not applicationServer.exit():
            logger.error(u"Local server components are not closed properly!")

        logger.debug(u"Application has been closed")
        logging.shutdown()
