# -*- coding: utf-8 -*-

"""
Main application launcher. Method application_start(string) is used to start the application.
PRODUCTION mode is set as default if started from console.
"""

__version__ = "$Id$"

import sys
import logging
import components.log


logger = logging.getLogger(__name__)


def versiontuple(v):
    """
        converts string like "0.8.1" to tuple (0, 8, 1)
    """
    return tuple(map(int, (v.split("."))))


def check_requirements():
    if sys.version_info < (2, 7) or sys.version_info >= (3, 0):
        raise Exception("must use python 2.7")

    try:
        import send2trash
    except:
        raise Exception('send2trash library is missing')

    # try:
    #     import PySide
    # except:
    #     raise Exception('PySide library is missing')
    #
    # if versiontuple(PySide.__version__) < versiontuple('1.2.0'):
    #     raise Exception('PySide 1.2 or higher is required, current version is %s' % (PySide.__version__))


# APPLICATION LAUNCHER
def application_start(environment):
    """
    :param environment: DEBUG or PRODUCTION string is expected
    """
    check_requirements()

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
        raise RuntimeError('Could not set API version (%s): did you import PyQt4 directly?' % e)



    from PyQt4 import QtCore
    from PyQt4 import QtGui

    from dialogs.main_dialog import MainApp

    # QtCore.Signal = QtCore.pyqtSignal
    # QtCore.Slot = QtCore.pyqtSlot

    components.log.setup_logging(environment)
    logger.debug(u"Initializing application launcher in %s mode" % environment)

    app = QtGui.QApplication(sys.argv)
    app.setOrganizationName(u"WooferPlayer")
    app.setOrganizationDomain(u"wooferplayer.com")
    app.setApplicationName(u"Woofer")
    main = MainApp()
    main.show()

    app.exec_()


if __name__ == "__main__":
    application_start(u'PRODUCTION')