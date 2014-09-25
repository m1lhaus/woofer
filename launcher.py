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


logger = logging.getLogger(__name__)


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
    logger.debug(u"Setting PyQt API tu v2")
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
    logger.debug(u"Setting logger to mode '%s'" % environment)
    components.log.setup_logging(environment)

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
    main = main_dialog.MainApp()
    main.show()
    app.exec_()


if __name__ == "__main__":
    application_start('PRODUCTION')