# -*- coding: utf-8 -*-

"""
"""

__version__ = "$Id$"

import logging

from PySide.QtGui import *
from PySide.QtCore import *


logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class RecursiveBrowser(QObject):

    scanFinished = Signal(list, bool)

    def __init__(self, targetDir, append, nameFilter=None, followSym=False):
        """
        @type targetDir: unicode
        @type nameFilter: tuple of str
        @type followSym: bool
        """
        super(RecursiveBrowser, self).__init__()
        self.targetDir = targetDir
        self.appendToPlayList = append
        self.followSym = followSym
        self.result = []
        self.nameFilter = nameFilter
        self.terminate = False

    def scanFiles(self):
        # print "sleeping 2 s"
        # self.thread().sleep(1)
        # print "scanning"
        flags = QDirIterator.Subdirectories | QDirIterator.FollowSymlinks if self.followSym else QDirIterator.Subdirectories
        dirIter = QDirIterator(self.targetDir, flags)

        self.result = []
        while not self.terminate and dirIter.hasNext():
            path = dirIter.next()
            if path.endswith(self.nameFilter):
                self.result.append(path)

        self.scanFinished.emit(self.result, self.appendToPlayList)
        # print len(self.result)

    def stopScanning(self):
        self.terminate = True