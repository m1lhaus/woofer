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
from PyQt5.QtCore import *

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
    errorSignal = pyqtSignal(int, str, str)

    def __init__(self, names_filter):
        """
        @param names_filter: Which files or file extensions we looking for.
        @type names_filter: tuple of str
        """
        super(RecursiveBrowser, self).__init__()
        self._stop = False

        self.names_filter = tuple([ext.replace('*', '') for ext in names_filter])           # i.e. remove * from *.mp3

        logger.debug("Recursive disk browser initialized.")

    @pyqtSlot(str)
    def scanFiles(self, target_dir):
        """
        Thread worker! Called from main thread via signal/slot.
        The final data are sent to media parser in another thread.
        @type target_dir: unicode
        """
        self._stop = False
        target_dir = os.path.abspath(target_dir)
        if not os.path.exists(target_dir):
            logger.error("Path given to RecursiveDiskBrowser doesn't exist!")
            self.errorSignal.emit(tools.ErrorMessages.ERROR, tr['SCANNER_DIR_NOT_FOUND_ERROR'], target_dir)
            self.parseDataSignal.emit([])             # end flag for media parser
            return

        # if target dir is already a file
        if target_dir.lower().endswith(self.names_filter) and os.path.isfile(target_dir):
            logger.debug("Scanned target dir is a file. Sending path and finish_parser flag.")
            self.parseDataSignal.emit([target_dir, ])
        else:
            logger.debug("Starting recursive file-search and parsing.")
            follow_sym = QSettings().value("components/disk/RecursiveBrowser/follow_symlinks", False, bool)
            for root, dirs, files in os.walk(target_dir, followlinks=follow_sym):
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

        logger.debug("Recursive search finished, sending finish_parser flag.")
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

    errorSignal = pyqtSignal(int, str, str)             # same as finished signal when no errors

    def __init__(self):
        super(MoveToTrash, self).__init__()

    @pyqtSlot(str)
    def remove(self, path):
        """
        Main worker method.
        Called asynchronously (signal/slot) to remove file/folder from disk to Trash.
        @type path: unicode
        """
        if not os.path.exists(path):
            logger.error("Given path for removing '%s' does not exist!", path)
            self.errorSignal.emit(tools.ErrorMessages.ERROR, tr['REMOVING_FILE_FOLDER_ERROR'] % os.path.basename(path),
                                  tr['FILE_FOLDER_NOT_FOUND'])
            return
        logger.debug("Removing file/folder '%s' from disk - sending to trash...", path)

        try:
            send2trash.send2trash(path)
        except OSError as exception:
            logger.exception("Unable to send file/folder '%s' to trash!", path)
            self.errorSignal.emit(tools.ErrorMessages.ERROR, tr['REMOVING_FILE_FOLDER_ERROR'] % os.path.basename(path),
                                  tr['ERROR_DETAILS'] % str(exception))

        else:
            logger.debug("File/folder sent to Trash successfully.")
            self.errorSignal.emit(tools.ErrorMessages.INFO, tr['REMOVING_FILE_FOLDER_SUCCESS'] % os.path.basename(path), "")

    def stop(self):
        """
        Called directly from another thread to immediately stop worker.
        Convention method. May be reimplemented in future.
        """
        pass