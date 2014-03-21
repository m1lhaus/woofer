# -*- coding: utf-8 -*-

"""
Disk components module
- RecursiveBrowser - recursively browses given path in separated thread
"""

__version__ = "$Id: disk.py 40 2014-03-16 16:32:37Z m1lhaus $"

import logging

from PySide.QtGui import *
from PySide.QtCore import *

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class RecursiveBrowser(QObject):
    """
    Recursive disk browser for searching media files on folder tree.
    Runs in separated thread! Data are transferred via Signal/Slot mechanism.
    """

    parseData = Signal(list)

    SEND_LIMIT = 25

    def __init__(self, nameFilter=None, followSym=False):
        """
        @param nameFilter: Which file extensions we looking for.
        @param followSym: Follow symbolic links. WARNING! Beware of cyclic symlinks!
        @type nameFilter: tuple of str
        @type followSym: bool
        """
        super(RecursiveBrowser, self).__init__()
        self.followSym = followSym
        self.nameFilter = nameFilter

        logger.debug("Recursive browser initialized.")

    @Slot(unicode)
    def scanFiles(self, targetDir):
        """
        Thread worker! Called asynchronously from main thread.
        The final data are sent to media parser in another thread.
        @type targetDir: unicode
        """
        # if target dir is already a file
        if targetDir.endswith(self.nameFilter):
            logger.debug("Scanned target dir is a file.")
            self.parseData.emit([targetDir])
            self.parseData.emit([])             # end flag for media parser
            return

        flags = QDirIterator.Subdirectories | QDirIterator.FollowSymlinks if self.followSym else QDirIterator.Subdirectories
        dirIter = QDirIterator(targetDir, flags)
        result = []
        n = 0

        logger.debug("Dir iterator initialized, starting recursive search and parsing.")
        while dirIter.hasNext():
            path = dirIter.next()
            if path.endswith(self.nameFilter):
                result.append(path)

                n += 1
                if n == self.SEND_LIMIT:
                    self.parseData.emit(result)
                    result = []
                    n = 0

        if result:
            self.parseData.emit(result)

        logger.debug("Recursive search finished, sending finish_parser flag.")
        self.parseData.emit([])
