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
Scheduler/maintenance modules.
"""

import codecs
import logging
import os
import time
import ujson
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime

from PyQt5.QtCore import *

import tools
from . import network

logger = logging.getLogger(__name__)


class LogCleaner(QObject):
    """
    Cleans old log text files, which are no longer needed.
    Every time user opens Woofer player, new log file is created.
    This behaviour leeds to high amount of redundant (nothing saying) log files.
    Log file is important only when error occurs and user want to participate and provide logs.
    Log cleaner runs in separated thread.
    Worker method: LogCleaner.clean()
    """

    def __init__(self):
        super(LogCleaner, self).__init__()
        self.log_dir = tools.LOG_DIR
        self.delay = 5 * (60 * 1000)                        # 5 minutes in ms

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.clean)
        self._stop = False

        logger.debug("LogCleaner initialized")

    def start(self):
        """
        Called directly from another thread to schedule cleaner launch.
        """
        logger.debug("Scheduling log cleaner - delay %s", self.delay)
        self._timer.start(self.delay)
        self._stop = False

    def stop(self):
        """
        Called directly from another thread to stop cleaner.
        """
        self._stop = True

    @pyqtSlot()
    def clean(self):
        """
        Deletes old files from './log' folder.
        Thread worker called by class timer.
        """
        if not os.path.isdir(self.log_dir):
            logger.error("Log dir under '%s' doesn't exist!", self.log_dir)

        logger.debug("Launching scheduled log file cleaning...")

        now = time.time()
        one_day = 86400
        time_past_limit = now - (7 * one_day)
        for ffile in os.listdir(self.log_dir):
            fpath = os.path.join(self.log_dir, ffile)

            # if file is older than X days, than remove the file
            if not self._stop and os.stat(fpath).st_mtime < time_past_limit:
                try:
                    tools.removeFile(fpath)
                except OSError:
                    logger.exception("Unable to remove log file: %s", fpath)

        logger.debug("Scheduled log file cleaning completed.")


class Updater(QObject):
    """
    Updater component which controls update-checking procedure, update downloading and setup.
    Component lives separately in its own thread!
    """

    errorSignal = pyqtSignal(int, str, str)

    updaterStartedSignal = pyqtSignal(int)                      # total size
    updateStatusSignal = pyqtSignal(int, int)                   # downloaded size, total size
    updaterFinishedSignal = pyqtSignal(int, str)            # status, file path

    readyForUpdateOnRestartSignal = pyqtSignal(str)         # path to new updater.exe
    availableUpdatePackageSignal = pyqtSignal(str, int)     # version (tag) name, package size
    startDownloadingPackageSignal = pyqtSignal()

    TERMINATE_DELAY = 3000

    def __init__(self):
        super(Updater, self).__init__()
        self.init_delay = 1000                              # check-for-updates delay in ms
        self.mutex = QMutex()

        self._github_api_url = "https://api.github.com/repos/m1lhaus/woofer/releases"
        self._github_release_url = "https://github.com/m1lhaus/woofer/releases/download/"

        self._package_url = None
        self._init_timer = QTimer(self)
        self._init_timer.setSingleShot(True)
        self._init_timer.timeout.connect(self.downloadReleaseInfo)
        self._downloader = None
        self._downloaderThread = None

        # %TEMP%/woofer_update
        self.download_dir = os.path.join(QDir.toNativeSeparators(QDir.tempPath()), "woofer_updater")
        self.extracted_pkg = os.path.join(self.download_dir, "extracted")

    @pyqtSlot()
    def start(self):
        """
        Method which starts (schedules) updater component.
        Method must NOT be called from MainThread directly!
        Instead should be called as slot from "scheduler thread" where it lives.
        """
        if os.path.isdir(self.download_dir):
            logger.debug("Removing download dir...")
            tools.removeFolder(self.download_dir)

        if not QSettings().value("components/scheduler/Updater/check_updates", True, bool):
            logger.debug("Checking for updates is turned off, updater will NOT be scheduled")
            return

        os.makedirs(self.extracted_pkg)

        logger.debug("Scheduling updater - delay %s", self.init_delay)
        self._init_timer.start(self.init_delay)

    def stop(self):
        """
        DIRECTLY CALLED method called directly from another thread.
        Stops downloading progress immediately.
        """
        mutexLocker = QMutexLocker(self.mutex)
        try:
            logger.debug("Stopping updater ...")
            if self._downloader:
                self._downloader.stopDownload()
        finally:
            mutexLocker.unlock()

    @pyqtSlot()
    def downloadReleaseInfo(self):
        """
        Thread worker. Called as slot from timer inside the thread after init_delay.
        Object is to retrieve JSON file from GitHub which contain information about Woofer releases.
        """
        def checkConnection(address, timeout=5):
            try:
                response = urllib.request.urlopen(address, timeout=timeout)
            except urllib.error.URLError:
                return False
            else:
                logger.debug("Successfully connected to %s", address)
                return True

        if not checkConnection(self._github_api_url):
            logger.debug("Unable connect to the Github server, probably no internet connection")
            return

        self._downloaderThread = QThread(self)
        self._downloader = network.Downloader(self._github_api_url, self.download_dir)
        self._downloader.moveToThread(self._downloaderThread)

        self._downloaderThread.started.connect(self._downloader.startDownload)
        self._downloader.downloaderFinishedSignal.connect(self.parseReleaseInfo)
        self._downloader.errorSignal.connect(self.errorSignal.emit)             # propagate to upper level

        self._downloaderThread.start()

    @pyqtSlot(int, str)
    def parseReleaseInfo(self, status, filepath):
        """
        Thread worker. Called as slot from downloader which downloads JSON file from GitHub.
        Method takes downloaded JSON file and parses information about latest Woofer version.
        If there is a newer version, it will be downloaded or user will be notified.
        @param status: downloader status (completed, error, stopped, etc.)
        @type status: int
        @param filepath: where downloaded file is stored
        @type filepath: unicode
        """
        # close previous downloader, all should be released from memory
        self._downloaderThread.quit()
        self._downloaderThread.wait(self.TERMINATE_DELAY)                # terminate delay

        if status != network.Downloader.COMPLETED:
            logger.error("Release info file downloader does NOT finished properly, returned status: %s", status)
            return

        try:
            with codecs.open(filepath, 'r', encoding="utf-8") as fobject:
                release_info = ujson.load(fobject)           # unicode is default encoding
        except IOError:
            logger.exception("Unable to open downloaded release info file '%s'!", filepath)
            return
        except ValueError:
            logger.exception("Unable to parse release info data from GitHub JSON file!")
            return

        # get current version
        try:
            with codecs.open(tools.BUILD_INFO_FILE, 'r', encoding="utf-8") as fobject:
                build_info = ujson.load(fobject)
        except IOError:
            logger.error("Unable to open build-info file at '%s'" % tools.BUILD_INFO_FILE)
            return
        except ValueError:
            logger.exception("Unable to parse build info data from build-info file!")
            return

        current_version = "v" + build_info["version"].lower()
        current_date = datetime.strptime(build_info["date"], '%Y-%m-%d %H:%M')

        settings = QSettings()
        take_pre_rls = settings.value("components/scheduler/Updater/pre-release", False, bool)
        logger.debug("%s update channel selected", ("Pre-release" if take_pre_rls else "Stable"))

        # analyze JSON from GitHub - find latest release
        latest_rls = None
        latest_date = datetime.fromtimestamp(0)
        for rls in release_info:
            if rls.get("prerelease", False) and not take_pre_rls:       # skip pre-release if ignored
                continue

            date_object = datetime.strptime(rls["published_at"], '%Y-%m-%dT%H:%M:%SZ')
            if date_object > latest_date:
                latest_date = date_object
                latest_rls = rls

        # compare latest found release to this current release (is newer and has different version number ?)
        if latest_rls and latest_rls["tag_name"].lower() != current_version and latest_date > current_date:
            logger.debug("Newer version %s published at %s found", latest_rls["tag_name"], latest_date)

            for asset in latest_rls["assets"]:
                # find only Windows binaries
                if asset["name"].startswith("woofer_win_%sbit" % tools.PLATFORM):
                    self._package_url = self._github_release_url + latest_rls["tag_name"] + "/" + asset["name"]

                    if settings.value("components/scheduler/Updater/auto_updates", False, bool):
                        logger.debug("Automatic update process is initialized")
                        self.downloadUpdatePackage()
                    else:
                        # notify user
                        self.startDownloadingPackageSignal.connect(self.downloadUpdatePackage)
                        self.availableUpdatePackageSignal.emit(str(latest_rls["tag_name"].lower()), int(asset["size"]))

                    break

        else:
            logger.debug("No newer version found")

    @pyqtSlot()
    def downloadUpdatePackage(self):
        """
        Method to initiate and setup downloading the update package if available.
        Called as slot automatically (auto-update) or by user (update button clicked).
        """
        logger.debug("Initializing update package download")

        self._downloaderThread = QThread(self)
        self._downloader = network.Downloader(self._package_url, self.download_dir)
        self._downloader.moveToThread(self._downloaderThread)

        self._downloaderThread.started.connect(self._downloader.startDownload)
        self._downloader.blockDownloadedSignal.connect(self.updateStatusSignal.emit)             # propagate to GUI
        self._downloader.downloaderStartedSignal.connect(self.updaterStartedSignal.emit)         # propagate to GUI
        self._downloader.downloaderFinishedSignal.connect(self.testDownloadedPackage)
        self._downloader.downloaderFinishedSignal.connect(self.updaterFinishedSignal.emit)       # propagate to GUI
        self._downloader.errorSignal.connect(self.errorSignal.emit)                  # propagate

        self._downloaderThread.start()

    @pyqtSlot(int, str)
    def testDownloadedPackage(self, status, zip_filepath):
        """
        Thread worker. Called as slot from downloader which downloads Woofer ZIP file from GitHub.
        Method takes downloaded ZIP file, makes CRC tests and extracts it to directory.
        Finally signal is sent to main GUI thread, where "Update on restart" message is displayed and
        update process on restart is scheduled.
        @param status: downloader status (completed, error, stopped, etc.)
        @type status: int
        @param zip_filepath: where downloaded file is stored
        @type zip_filepath: unicode
        """
        # close previous downloader, all should be released from memory
        self._downloaderThread.quit()
        self._downloaderThread.wait(self.TERMINATE_DELAY)

        if status != network.Downloader.COMPLETED:
            logger.debug("Update package downloading did NOT finish properly")
            return

        try:
            the_zip_file = zipfile.ZipFile(zip_filepath)
            ret = the_zip_file.testzip()
        except zipfile.BadZipfile:
            logger.exception("Downloaded file '%s' is not valid ZIP file! File is probably corrupted!", zip_filepath)
            return
        except IOError:
            logger.exception("Downloaded file '%s' not found!", zip_filepath)
            return
        except Exception:
            logger.exception("Unexpected error when checking downloaded ZIP file '%s'", zip_filepath)
            return

        if ret is not None:
            logger.error("Downloaded ZIP file '%s' corrupted!", zip_filepath)
            return

        try:
            tools.extractZIPFiles(src=zip_filepath, dst=self.extracted_pkg)
        except Exception:
            logger.exception("Error when extracting downloaded update ZIP file!")
            return

        updater_exe = os.path.join(self.extracted_pkg, "updater.exe")
        if not os.path.join(updater_exe):
            logger.error("Unable to find 'updater.exe' script in '%s'!", self.extracted_pkg)

        logger.debug("Update package is extracted and ready to be applied")
        self.readyForUpdateOnRestartSignal.emit(updater_exe)