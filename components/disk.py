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
Disk components
- Threaded recursive disk browser for searching media files in folder tree.
- Threaded dir/file remover (sends files to Trash)
"""

import os
import sys
import logging
import send2trash

from PyQt4.QtCore import *

import tools

logger = logging.getLogger(__name__)


class RecursiveBrowser(QObject):
    """
    Recursive disk browser for searching media files in folder tree.
    Data are transferred via Signal/Slot mechanism.
    Runs in separated thread!
    Worker method: RecursiveBrowser.scanFiles(unicode_path)
    """

    parseDataSignal = pyqtSignal(list)
    errorSignal = pyqtSignal(int, unicode, unicode)

    def __init__(self, names_filter):
        """
        @param names_filter: Which files or file extensions we looking for.
        @type names_filter: tuple of str
        """
        super(RecursiveBrowser, self).__init__()
        self._stop = False

        self.block_size = 5                                         # send limit / parsing this block takes about 50ms
        self.follow_sym = QSettings().value("components/disk/RecursiveBrowser/follow_symlinks", False, bool)
        self.names_filter = tuple([ext.replace('*', '') for ext in names_filter])           # i.e. remove * from *.mp3
        self.iteratorFlags = QDirIterator.Subdirectories | QDirIterator.FollowSymlinks if self.follow_sym else QDirIterator.Subdirectories

        logger.debug(u"Recursive disk browser initialized.")

    @pyqtSlot(unicode)
    def scanFiles(self, target_dir):
        """
        Thread worker! Called from main thread via signal/slot.
        The final data are sent to media parser in another thread.
        @type target_dir: unicode
        """
        self._stop = False
        if not os.path.exists(target_dir):
            logger.error(u"Path given to RecursiveDiskBrowser doesn't exist!")
            self.errorSignal.emit(tools.ErrorMessages.ERROR, u"Path given to disk scanner doesn't exist!", u"%s not found!" % target_dir)
            self.parseDataSignal.emit([])             # end flag for media parser
            return

        # if target dir is already a file
        if target_dir[-5:].lower().endswith(self.names_filter) and os.path.isfile(target_dir):
            logger.debug(u"Scanned target dir is a file. Sending path and finish_parser flag.")
            self.parseDataSignal.emit([target_dir])
            self.parseDataSignal.emit([])             # end flag for media parser
            return

        n = 0
        result = []
        dirIterator = QDirIterator(target_dir, self.iteratorFlags)

        logger.debug(u"Dir iterator initialized, starting recursive search and parsing.")
        while not self._stop and dirIterator.hasNext():
            path = dirIterator.next()
            if path[-5:].lower().endswith(self.names_filter):
                result.append(os.path.normpath(path))

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

    def stop(self):
        logger.debug("Stopping disk scanning...")
        self._stop = True


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
            self.errorSignal.emit(tools.ErrorMessages.ERROR, u"Given path for removing does not exist!",
                                  u"%s not found!" % path)
            return
        logger.debug(u"Removing %s '%s' from disk - sending to trash...", folder_or_file, path)

        try:
            send2trash.send2trash(path)
        except OSError, exception:
            logger.exception(u"Unable to send %s '%s' to trash!", folder_or_file, path)
            self.errorSignal.emit(tools.ErrorMessages.ERROR, u"Unable move to Trash path '%s'!" % path,
                                  u"Details: %s" % str(exception).decode(sys.getfilesystemencoding()))

        else:
            logger.debug(u"%s send to Trash successfully.", folder_or_file.capitalize())
            self.errorSignal.emit(tools.ErrorMessages.INFO, u"%s '%s' successfully removed from disk" %
                                 (folder_or_file.capitalize(), os.path.basename(path)), u"")

    def stop(self):
        """
        Called directly from another thread to immediately stop worker.
        Convention method. May be reimplemented in future.
        """
        pass