#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main application launcher. Method application_start(string) is used to start the application.
PRODUCTION mode is set as default if started from console.
"""

__version__ = "$Id$"

import sys
import imp
import os
import logging
import components.log
from tools.misc import RedirectDescriptor


logger = logging.getLogger(__name__)
StdErrRedirector = RedirectDescriptor()


def versiontuple(v):
    """
    Converts string like "0.8.1" to tuple (0, 8, 1)
    """
    return tuple(map(int, (v.split("."))))


def check_requirements():
    """
    Looks for required packages.
    """
    logger.debug(u"Checking requirements")

    if sys.version_info < (2, 7) or sys.version_info >= (3, 0):
        raise Exception(u"Application requires Python 2.7!")

    try:
        imp.find_module('send2trash')
    except ImportError:
        raise Exception(u"Send2Trash package is required!")

    try:
        imp.find_module('PyQt4')
    except ImportError:
        raise Exception(u"PyQt4 library is missing")

    # requirements for system-wide hooks
    if os.name == 'nt':
        try:
            imp.find_module('pythoncom')
            imp.find_module('pywintypes')
        except ImportError:
            raise Exception(u"PyWin32 libraries (package) is required on Windows platform!")

        try:
            imp.find_module('pyHook')
        except ImportError:
            raise Exception(u"pyHook package is required on Windows platform!")

    elif os.name == 'posix':
        # todo
        pass


def set_pyqt_api2():
    """
    PyQt4 uses API v1 as default (QStrings, etc. ... deprecated).
    But PyQt4 can use newer v2 API (native python objects conversion).
    """
    logger.debug(u"Setting PyQt API to v2")
    import sip
    try:
        sip.setapi('QDate', 2)
        sip.setapi('QDateTime', 2)
        sip.setapi('QString', 2)
        sip.setapi('QTextStream', 2)
        sip.setapi('QTime', 2)
        sip.setapi('QUrl', 2)
        sip.setapi('QVariant', 2)
    except ValueError, e:
        raise RuntimeError(u'Could not set API version (%s): did you import PyQt4 directly?' % e)


# *******************************************
# *******************************************
# *******************************************
# APPLICATION LAUNCHER
# *******************************************
# *******************************************
# *******************************************
# *******************************************


def application_start(environment):
    """
    Initializes Qt libraries and Woofer application.
    @param environment: DEBUG or PRODUCTION string is expected
    """
    components.log.setup_logging(environment)
    logger.debug(u"Set logger to mode '%s'" % environment)

    check_requirements()
    set_pyqt_api2()

    logger.debug(u"All ready to go. Import PyQt libs and initializing main application loop.")
    from PyQt4 import QtCore
    from PyQt4 import QtGui
    from dialogs import main_dialog

    app = QtGui.QApplication(sys.argv)
    app.setOrganizationName(u"WooferPlayer")
    app.setOrganizationDomain(u"wooferplayer.com")
    app.setApplicationName(u"Woofer")

    # tries to connect to existing shared memory (another WooferPlayer instance)
    logger.debug(u"Checking if another instance is running...")
    sharedMemory = QtCore.QSharedMemory()
    sharedMemory.setKey(u"wooferplayer.com")
    if sharedMemory.attach(QtCore.QSharedMemory.ReadOnly):
        logger.debug(u"Another instance of Woofer Player is running! Closing application.")
        msgBox = QtGui.QMessageBox()
        msgBox.setIcon(QtGui.QMessageBox.Warning)
        msgBox.setWindowTitle(u"Another instance is running")
        msgBox.setText(u"Another instance of Woofer player is running.")
        msgBox.setInformativeText(u"If no instance of Woofer player is running, "
                                  u"please contact us on www.wooferplayer.com")
        msgBox.exec_()
        return

    logger.debug(u"Trying to create shared memory segment for id 'wooferplayer.com'")
    if not sharedMemory.create(1, QtCore.QSharedMemory.ReadOnly):
        logger.error(u"Unable to create shared memory segment, reason: %s", sharedMemory.errorString())

        msgBox = QtGui.QMessageBox()
        msgBox.setIcon(QtGui.QMessageBox.Critical)
        msgBox.setWindowTitle(u"Initialization error")
        msgBox.setText(u"Unable to create shared memory segment.\nReason: %s" % sharedMemory.errorString())
        msgBox.setInformativeText(u"Please contact us on www.wooferplayer.com for further information.")
        msgBox.exec_()
        return

    logger.debug(u"No other instance is running. Initializing Qt application.")

    main = main_dialog.MainApp()
    main.show()

    logger.debug(u"Starting MainThread loop...")

    app.exec_()

    logger.debug(u"MainThread loop stopped. Application has been closed successfully.")


if __name__ == "__main__":
    StdErrRedirector.redirect_C_stderr_null()
    application_start('PRODUCTION')
    StdErrRedirector.redirect_C_stderr_back()