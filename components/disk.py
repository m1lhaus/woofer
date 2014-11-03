# -*- coding: utf-8 -*-

"""
Disk components
- Recursive disk browser for searching media files on folder tree.
"""


import os
import logging
import send2trash

from tools.misc import ErrorMessages

from PyQt5.QtCore import *

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class RecursiveBrowser(QObject):
    """
    Recursive disk browser for searching media files on folder tree.
    Data are transferred via Signal/Slot mechanism.
    Runs in separated thread!
    """

    parseDataSignal = pyqtSignal(list)

    SEND_LIMIT = 5     # cca 50ms blocks for parsing

    def __init__(self, fileNamesFilter, followSym=False):
        """
        @param fileNamesFilter: Which files or file extensions we looking for.
        @param followSym: Follow symbolic links. WARNING! Beware of cyclic symlinks!
        @type fileNamesFilter: tuple of str
        @type followSym: bool
        """
        super(RecursiveBrowser, self).__init__()
        self.followSym = followSym
        self.fileNamesFilter = tuple([ext.replace('*', '') for ext in fileNamesFilter])     # i.e. remove * from *.mp3

        logger.debug("Recursive browser initialized.")

    @pyqtSlot(str)
    def scanFiles(self, targetDir):
        """
        Thread worker! Called asynchronously from main thread.
        The final data are sent to media parser in another thread.
        @type targetDir: str
        """
        # if target dir is already a file
        if targetDir.endswith(self.fileNamesFilter):
            logger.debug("Scanned target dir is a file.")
            self.parseDataSignal.emit([targetDir])
            self.parseDataSignal.emit([])             # end flag for media parser
            return

        flags = QDirIterator.Subdirectories | QDirIterator.FollowSymlinks if self.followSym else QDirIterator.Subdirectories
        dirIter = QDirIterator(targetDir, flags)
        result = []
        n = 0

        logger.debug("Dir iterator initialized, starting recursive search and parsing.")
        while dirIter.hasNext():
            path = dirIter.next()
            if path.endswith(self.fileNamesFilter):    # little bit slower than using regex (few ms), but more readable
                result.append(path)

                n += 1
                if n == self.SEND_LIMIT:
                    self.parseDataSignal.emit(result)
                    n = 0
                    result = []

        if result:
            self.parseDataSignal.emit(result)

        logger.debug("Recursive search finished, sending finish_parser flag.")
        self.parseDataSignal.emit([])

    @pyqtSlot()
    def finish(self):
        """
        Called to to job after all work is finished (media files are all parsed).
        Not used for now.
        """
        pass


class MoveToTrash(QObject):
    """
    Asynchronous file remover.
    Runs in separated thread!
    """

    finishedSignal = pyqtSignal(int, str, str)

    def __init__(self):
        super(MoveToTrash, self).__init__()

    @pyqtSlot(str)
    def remove(self, path):
        """
        Main worker method.
        Called asynchronously (signal/slot) to remove file/folder from disk to Trash.
        @type path: str
        """
        if os.path.isfile(path):
            folder_or_file = "file"
        elif os.path.isdir(path):
            folder_or_file = "folder"
        else:
            logger.error("Given path for removing '%s' does not exist!", path)
            self.finishedSignal.emit(ErrorMessages.ERROR, "Given path for removing '%s' does not exist!" % path, "")
            return

        logger.debug("Removing %s '%s' from disk - sending to trash...", folder_or_file, path)

        try:
            send2trash.send2trash(path)
        except OSError as e:
            logger.exception("Unable to send %s '%s' to trash!", folder_or_file, path)
            self.finishedSignal.emit(ErrorMessages.ERROR, "Unable to move path to Trash path '%s'!" % path,
                                     e.args if len(e.args) > 1 else e.args[0])

        else:
            logger.debug("Path send to trash successfully.")
            self.finishedSignal.emit(ErrorMessages.INFO, "%s '%s' successfully removed from disk" %
                                    (folder_or_file.capitalize(), os.path.basename(path)), "")
