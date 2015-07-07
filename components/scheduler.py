# -*- coding: utf-8 -*-

"""
Scheduler/maintenance modules.
"""

import logging
import os
import time
import json
import codecs
import zipfile
import shutil
from datetime import datetime

from PyQt4.QtCore import *

import tools
import network

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

        logger.debug(u"LogCleaner initialized")

    def start(self):
        logger.debug(u"Scheduling log cleaner - delay %s", self.delay)
        QTimer.singleShot(self.delay, self.clean)

    @pyqtSlot()
    def clean(self):
        """
        Deletes old files from /log folder.
        Thread worker.
        """
        if not os.path.isdir(self.log_dir):
            logger.error(u"Log dir under '%s' doesn't exist!", self.log_dir)

        logger.debug(u"Launching scheduled log file cleaning...")

        now = time.time()
        one_day = 86400
        time_past_limit = now - (7 * one_day)
        for ffile in os.listdir(self.log_dir):
            fpath = os.path.join(self.log_dir, ffile)

            # if file is older than X days, than remove the file
            if os.stat(fpath).st_mtime < time_past_limit:
                try:
                    os.remove(fpath)
                except OSError:
                    logger.exception(u"Unable to remove log file: %s", fpath)

        logger.debug(u"Scheduled log file cleaning completed.")


class Updater(QObject):

    errorSignal = pyqtSignal(int, unicode, unicode)

    updaterStartedSignal = pyqtSignal(int)                      # total size
    updateStatusSignal = pyqtSignal(int, int)                   # downloaded size, total size
    updaterFinishedSignal = pyqtSignal(int, unicode)            # status, file path
    readyForUpdateSignal = pyqtSignal(unicode)

    def __init__(self):
        super(Updater, self).__init__()

        self.delay = 1000
        self.github_api_url = u"https://api.github.com/repos/m1lhaus/woofer/releases"
        self.github_release_url = u"https://github.com/m1lhaus/woofer/releases/download/"

        # %TEMP%/woofer_update
        self.download_dir = os.path.join(QDir.toNativeSeparators(QDir.tempPath()), u"woofer_updater+ěščřžýáíé")
        self.extracted_pkg = os.path.join(self.download_dir, u"extracted")

        self.downloader = None
        self.downloaderThread = None

    @pyqtSlot()
    def start(self):
        """
        Method which starts (schedule) Updater.
        Method must NOT be called from MainThread directly!
        Instead should be called as slot from "scheduler thread" where it lives.
        """
        if not QSettings().value("components/scheduler/Updater/check_updates", True, bool):
            logger.debug(u"Checking for updates is turned off")
            return

        if os.path.isdir(self.extracted_pkg):
            logger.debug(u"Deleting folder with old update ...")
            shutil.rmtree(self.extracted_pkg)
        os.makedirs(self.extracted_pkg)

        logger.debug(u"Scheduling updater - delay %s", self.delay)
        QTimer.singleShot(self.delay, self.downloadReleaseInfo)

    def stop(self):
        """
        Outside public method. Stops downloading progress immediately.
        WARNING: Method is not protected by mutex!
        """
        logger.debug(u"Stopping updater ...")
        if self.downloader:
            self.downloader.stopDownload()

    @pyqtSlot()
    def downloadReleaseInfo(self):
        """
        Thread worker. Called as slot from time inside the thread.
        Object is to retrieve JSON file from GitHub which contain information about releases.
        """
        if not network.Downloader.internetConnection():
            logger.debug(u"Unable connect to the Google IP address, probably no internet connection")
            return

        self.downloaderThread = QThread(self)
        self.downloader = network.Downloader(self.github_api_url, self.download_dir)
        self.downloader.moveToThread(self.downloaderThread)

        self.downloaderThread.started.connect(self.downloader.startDownload)
        self.downloader.downloaderFinishedSignal.connect(self.parseReleaseInfo)
        self.downloader.errorSignal.connect(self.errorSignal.emit)                  # propagate

        self.downloaderThread.start()

    @pyqtSlot(int, unicode)
    def parseReleaseInfo(self, status, filepath):
        """
        Thread worker. Called as slot from downloader which downloads JSON file from GitHub.
        Method takes downloaded JSON file and parsers information about latest Woofer version.
        If there is a newer version, it will be downloaded.
        @param status: downloader status (completed, error, stopped, etc.)
        @type status: int
        @param filepath: where downloaded file is stored
        @type filepath: unicode
        """
        # close previous downloader, all should be released from memory
        self.downloaderThread.quit()
        self.downloaderThread.wait(3000)                # terminate delay

        if status != network.Downloader.COMPLETED:
            logger.error(u"Release info file downloader does NOT finished properly, returned status: %s", status)
            return

        try:
            with codecs.open(filepath, 'r', encoding="utf-8") as fobject:
                release_info = json.load(fobject)       # unicode should be default encoding
        except IOError:
            logger.exception(u"Unable to open downloaded release info file '%s'!", filepath)
            return
        except ValueError:
            logger.exception(u"Unable to parse release info data from GitHub JSON file!")
            return

        # get current version
        build_info_file = os.path.join(tools.misc.APP_ROOT_DIR, u"build.info")
        try:
            with codecs.open(build_info_file, 'r', encoding="utf-8") as fobject:
                build_info = json.load(fobject)
        except IOError:
            logger.error(u"Unable to open 'build.info' file in root directory!")
            return
        except ValueError:
            logger.exception(u"Unable to parse build info data from 'build.info' file!")
            return

        current_version = "v" + build_info["version"].lower()
        current_date = datetime.strptime(build_info["date"], '%Y-%m-%d %H:%M')

        settings = QSettings()
        take_pre_rls = settings.value("components/scheduler/Updater/pre-release", False, bool)

        # analyze JSON from GitHub - find latest release            # todo: consider only Windows releases
        latest_rls = release_info[0]
        latest_date = datetime.strptime(latest_rls["published_at"], '%Y-%m-%dT%H:%M:%SZ')
        for rls in release_info:
            if rls.get("prerelease", False) and not take_pre_rls:       # skip pre-release if ignored
                continue

            date_object = datetime.strptime(rls["published_at"], '%Y-%m-%dT%H:%M:%SZ')
            if date_object > latest_date:
                latest_date = date_object
                latest_rls = rls

        # compare latest found release to this current release (is newer and has different version number ?)
        if latest_rls["tag_name"].lower() != current_version and latest_date > current_date:
            logger.debug(u"Newer version %s published at %s found", latest_rls["tag_name"], latest_date)

            url = self.github_release_url + latest_rls["tag_name"] + "/" + latest_rls["assets"][0]["name"]
            self.downloaderThread = QThread(self)
            self.downloader = network.Downloader(url, self.download_dir)
            self.downloader.moveToThread(self.downloaderThread)

            self.downloaderThread.started.connect(self.downloader.startDownload)
            self.downloader.blockDownloadedSignal.connect(self.updateStatusSignal.emit)             # propagate to GUI
            self.downloader.downloaderFinishedSignal.connect(self.testDownloadedPackage)
            self.downloader.downloaderFinishedSignal.connect(self.updaterFinishedSignal.emit)       # propagate to GUI
            self.downloader.downloaderStartedSignal.connect(self.updaterStartedSignal.emit)         # propagate to GUI
            self.downloader.errorSignal.connect(self.errorSignal.emit)                  # propagate

            self.downloaderThread.start()

        else:
            logger.debug(u"No newer version found")

        tools.removeFile(filepath)

    @pyqtSlot(int, unicode)
    def testDownloadedPackage(self, status, zip_filepath):
        """
        Thread worker. Called as slot from downloader which downloads Woofer ZIP file from GitHub.
        Method takes downloaded ZIP file, makes CRC tests and extracts it to directory.
        Finally signal is sent to main GUI thread, where "Update" message is displayed and "
        Update on restart" is scheduled.
        @param status: downloader status (completed, error, stopped, etc.)
        @type status: int
        @param zip_filepath: where downloaded file is stored
        @type zip_filepath: unicode
        """
        # close previous downloader, all should be released from memory
        self.downloaderThread.quit()
        self.downloaderThread.wait(3000)        # terminate delay

        if status != network.Downloader.COMPLETED:
            return

        try:
            the_zip_file = zipfile.ZipFile(zip_filepath)
            ret = the_zip_file.testzip()
        except zipfile.BadZipfile:
            logger.exception(u"Downloaded file '%s' is not valid ZIP file! File is probably corrupted!", zip_filepath)
            return
        except IOError:
            logger.exception(u"Downloaded file '%s' not found!", zip_filepath)
            return
        except Exception:
            logger.exception(u"Unexpected error when checking downloaded ZIP file '%s'", zip_filepath)
            return

        if ret is not None:
            logger.error(u"Downloaded ZIP file '%s' corrupted!", zip_filepath)
            return

        try:
            tools.extractZIPFiles(src=zip_filepath, dst=self.extracted_pkg)
        except Exception:
            logger.exception(u"Error when extracting downloaded update ZIP file!")
            return

        updater_exe = os.path.join(self.extracted_pkg, u"updater.exe")
        if not os.path.join(updater_exe):
            logger.error(u"Unable to find 'updater.exe' script in '%s'!", self.extracted_pkg)

        logger.debug(u"Update package is extracted and ready to be applied")
        self.readyForUpdateSignal.emit(updater_exe)

        # tools.removeFile(zip_filepath)