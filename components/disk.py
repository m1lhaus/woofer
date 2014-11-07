# -*- coding: utf-8 -*-

"""
Disk components
- Recursive disk browser for searching media files on folder tree.
"""


import os
import logging
import send2trash

from PyQt4.QtCore import *

from tools.misc import ErrorMessages


logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)


class RecursiveBrowser(QObject):
    """
    Recursive disk browser for searching media files on folder tree.
    Runs in separated thread!
    Data are transferred via Signal/Slot mechanism.
    """
    parseData = pyqtSignal(list)

    SEND_LIMIT = 5     # cca 50ms blocks for parsing

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

        logger.debug(u"Recursive browser initialized.")

    @pyqtSlot(unicode)
    def scanFiles(self, targetDir):
        """
        Thread worker! Called asynchronously from main thread.
        The final data are sent to media parser in another thread.
        @type targetDir: unicode
        """
        # if target dir is already a file
        if targetDir.endswith(self.nameFilter):
            logger.debug(u"Scanned target dir is a file.")
            self.parseData.emit([targetDir])
            self.parseData.emit([])             # end flag for media parser
            return

        flags = QDirIterator.Subdirectories | QDirIterator.FollowSymlinks if self.followSym else QDirIterator.Subdirectories
        dirIter = QDirIterator(targetDir, flags)
        result = []
        n = 0

        logger.debug(u"Dir iterator initialized, starting recursive search and parsing.")
        while dirIter.hasNext():
            path = dirIter.next()
            if path.endswith(self.nameFilter):
                result.append(path)

                n += 1
                if n == self.SEND_LIMIT:
                    self.parseData.emit(result)
                    n = 0
                    result = []

        if result:
            self.parseData.emit(result)

        logger.debug(u"Recursive search finished, sending finish_parser flag.")
        self.parseData.emit([])

    @pyqtSlot()
    def finish(self):
        """
        Called to to job after all work is finished (media files are all parsed).
        Not used!
        """
        pass


class MoveToTrash(QObject):
    """
    Asynchronous file remover - lives in own thread!
    """

    finished = pyqtSignal(int, unicode, unicode)

    def __init__(self):
        super(MoveToTrash, self).__init__()

    @pyqtSlot(unicode)
    def remove(self, path):
        """
        Main worker method.
        Called asynchronously (signal/slot) to remove file/folder from disk to Trash.
        @type path: unicode
        """
        if os.path.isfile(path):
            folder_or_file = u"file"
        elif os.path.isdir(path):
            folder_or_file = u"folder"
        else:
            logger.error(u"Given path for removing '%s' does not exist!", path)
            self.finished.emit(ErrorMessages.ERROR, u"Given path for removing '%s' does not exist!" % path, u"")
            return

        logger.debug(u"Removing %s '%s' from disk - sending to trash...", folder_or_file, path)

        try:
            send2trash.send2trash(path)
        except OSError, exception:
            logger.exception(u"Unable to send %s '%s' to trash!", folder_or_file, path)
            self.finished.emit(ErrorMessages.ERROR, u"Unable to move path to Trash path '%s'!" % path,
                               u"Details: %s" % exception.message)

        else:
            logger.debug(u"Path send to trash successfully.")
            self.finished.emit(ErrorMessages.INFO, u"%s '%s' successfully removed from disk" %
                               (folder_or_file.capitalize(), os.path.basename(path)), u"")
