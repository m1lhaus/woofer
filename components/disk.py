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
import scandir
from PyQt4.QtCore import *

import tools
from components.translator import tr


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
        target_dir = os.path.abspath(target_dir)
        if not os.path.exists(target_dir):
            logger.error(u"Path given to RecursiveDiskBrowser doesn't exist!")
            self.errorSignal.emit(tools.ErrorMessages.ERROR, tr['SCANNER_DIR_NOT_FOUND_ERROR'], target_dir)
            self.parseDataSignal.emit([])             # end flag for media parser
            return

        # if target dir is already a file
        if target_dir.lower().endswith(self.names_filter) and os.path.isfile(target_dir):
            logger.debug(u"Scanned target dir is a file. Sending path and finish_parser flag.")
            self.parseDataSignal.emit([target_dir, ])
        else:
            logger.debug(u"Starting recursive file-search and parsing.")
            for root, dirs, files in scandir.walk(target_dir, followlinks=self.follow_sym):
                # remove dirs starting with dot and sort the result
                for i, ddir in reversed(list(enumerate(dirs))):
                    if ddir[0] == ".":
                        del dirs[i]
                dirs.sort()

                # find all music files in current rootdir
                music = [os.path.join(root, ffile) for ffile in files if ffile.lower().endswith(self.names_filter)]
                if music:
                    music.sort()
                    self.parseDataSignal.emit(music)

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
        logger.debug(u"Stopping disk scanning...")
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
        if not os.path.exists(path):
            logger.error(u"Given path for removing '%s' does not exist!", path)
            self.errorSignal.emit(tools.ErrorMessages.ERROR, tr['REMOVING_FILE_FOLDER_ERROR'] % os.path.basename(path),
                                  tr['FILE_FOLDER_NOT_FOUND'])
            return
        logger.debug(u"Removing file/folder '%s' from disk - sending to trash...", path)

        try:
            send2trash.send2trash(path)
        except OSError, exception:
            logger.exception(u"Unable to send file/folder '%s' to trash!", path)
            self.errorSignal.emit(tools.ErrorMessages.ERROR, tr['REMOVING_FILE_FOLDER_ERROR'] % os.path.basename(path),
                                  tr['ERROR_DETAILS'] % str(exception).decode(sys.getfilesystemencoding()))

        else:
            logger.debug(u"File/folder sent to Trash successfully.")
            self.errorSignal.emit(tools.ErrorMessages.INFO, tr['REMOVING_FILE_FOLDER_SUCCESS'] % os.path.basename(path), u"")

    def stop(self):
        """
        Called directly from another thread to immediately stop worker.
        Convention method. May be reimplemented in future.
        """
        pass