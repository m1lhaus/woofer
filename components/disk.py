# -*- coding: utf-8 -*-

"""
Disk components
- Threaded recursive disk browser for searching media files in folder tree.
- Threaded dir/file remover (sends files to Trash)
"""

import os
import sys
import logging
import send2trash

from PyQt4.QtCore import *

from tools import ErrorMessages

logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)


class RecursiveBrowser(QObject):
    """
    Recursive disk browser for searching media files in folder tree.
    Data are transferred via Signal/Slot mechanism.
    Runs in separated thread!
    Worker method: RecursiveBrowser.scanFiles(unicode_path)

    @param names_filter: Which files or file extensions we looking for.
    @param follow_sym: Follow symbolic links. WARNING! Beware of cyclic symlinks!
    @type names_filter: tuple of str
    @type follow_sym: bool
    """

    parseDataSignal = pyqtSignal(list)
    errorSignal = pyqtSignal(int, unicode, unicode)

    def __init__(self, names_filter, follow_sym=False):
        super(RecursiveBrowser, self).__init__()
        self.block_size = 5                                         # send limit / parsing this block takes about 50ms
        self.follow_sym = follow_sym
        self.names_filter = tuple([ext.replace('*', '') for ext in names_filter])           # i.e. remove * from *.mp3
        self.iteratorFlags = QDirIterator.Subdirectories | QDirIterator.FollowSymlinks if follow_sym else QDirIterator.Subdirectories

        logger.debug(u"Recursive disk browser initialized.")

    @pyqtSlot(unicode)
    def scanFiles(self, target_dir):
        """
        Thread worker! Called from main thread via signal/slot.
        The final data are sent to media parser in another thread.
        @type target_dir: unicode
        """
        if not os.path.exists(target_dir):
            logger.error(u"Path given to RecursiveDiskBrowser doesn't exist!")
            self.errorSignal.emit(ErrorMessages.ERROR, u"Path given to disk scanner doesn't exist!", u"%s not found!" % target_dir)
            self.parseDataSignal.emit([])             # end flag for media parser
            return

        # if target dir is already a file
        if target_dir.endswith(self.names_filter):
            logger.debug(u"Scanned target dir is a file. Sending path and finish_parser flag.")
            self.parseDataSignal.emit([target_dir])
            self.parseDataSignal.emit([])             # end flag for media parser
            return

        n = 0
        result = []
        dirIterator = QDirIterator(target_dir, self.iteratorFlags)

        logger.debug(u"Dir iterator initialized, starting recursive search and parsing.")
        while dirIterator.hasNext():
            path = dirIterator.next()
            if path.endswith(self.names_filter):
                result.append(path)

                n += 1
                if n == self.block_size:
                    self.parseDataSignal.emit(result)
                    n = 0
                    result = []

        if result:
            self.parseDataSignal.emit(result)

        logger.debug(u"Recursive search finished, sending finish_parser flag.")
        self.parseDataSignal.emit([])

    @pyqtSlot()
    def finish(self):
        """
        Called to to job after all work is finished (media files are all parsed).
        Not used!
        """
        pass


class MoveToTrash(QObject):
    """
    Threaded file remover - uses send2trash package.
    Lives in own thread!
    Worker method: MoveToTrash.remove()
    """

    errorSignal = pyqtSignal(int, unicode, unicode)             # same as finished signal when no errors

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
            self.errorSignal.emit(ErrorMessages.ERROR, u"Given path for removing does not exist!",
                                  u"%s not found!" % path)
            return
        logger.debug(u"Removing %s '%s' from disk - sending to trash...", folder_or_file, path)

        try:
            send2trash.send2trash(path)
        except OSError, exception:
            logger.exception(u"Unable to send %s '%s' to trash!", folder_or_file, path)
            self.errorSignal.emit(ErrorMessages.ERROR, u"Unable move to Trash path '%s'!" % path,
                                  u"Details: %s" % unicode(exception.message, sys.getfilesystemencoding()))         # TODO: test on Windows

        else:
            logger.debug(u"%s send to Trash successfully.", folder_or_file.capitalize())
            self.errorSignal.emit(ErrorMessages.INFO, u"%s '%s' successfully removed from disk" %
                                 (folder_or_file.capitalize(), os.path.basename(path)), u"")
