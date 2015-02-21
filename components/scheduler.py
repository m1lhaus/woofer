# -*- coding: utf-8 -*-

"""
Scheduler/maintenance modules.
"""

import logging
import os
import time
import json
import codecs
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

    def __init__(self):
        super(Updater, self).__init__()

        self.delay = 1 * (1 * 1000)                        # 5 minutes in ms
        self.download_dir = u""         # QDir.toNativeSeparators(QDir.tempPath())

        self.downloader = None
        self.downloaderThread = None

    @pyqtSlot()
    def start(self):
        logger.debug(u"Scheduling updater - delay %s", self.delay)
        QTimer.singleShot(self.delay, self.downloadReleaseInfo)

    def stop(self):
        logger.debug(u"Stopping updater ...")
        if self.downloader:
            self.downloader.pauseDownload()

    @pyqtSlot()
    def downloadReleaseInfo(self):
        url = "https://api.github.com/repos/m1lhaus/woofer/releases"

        self.downloaderThread = QThread(self)
        self.downloader = network.Downloader(url, self.download_dir)
        self.downloader.moveToThread(self.downloaderThread)

        self.downloaderThread.started.connect(self.downloader.startDownload)
        self.downloader.completedSignal.connect(self.parseReleaseInfo)

        self.downloaderThread.start()

    @pyqtSlot(int, unicode)
    def parseReleaseInfo(self, status, filepath):
        # close ReleaseInfo downloader
        self.downloaderThread.quit()
        self.downloaderThread.wait(3000)        # terminate delay

        if status != network.Downloader.COMPLETED:
            logger.error(u"Unable to download release info file, returned status: %s", status)
            return

        if not os.path.isfile(filepath):
            logger.error(u"Unable to locate downloaded file '%s'!", filepath)

        try:
            with codecs.open(filepath, 'r', encoding="utf-8") as fobject:
                release_info = json.load(fobject)       # unicode should be default encoding
        except ValueError:
            logger.exception(u"Unable to parse release info data from GitHub JSON file!")
            return

        # get current vesion
        build_info_file = os.path.join(tools.misc.APP_ROOT_DIR, u"build.info")
        if not os.path.isfile(build_info_file):
            logger.error(u"Unable to locate 'build.info' file in root directory!")
            return

        try:
            with codecs.open(build_info_file, 'r', encoding="utf-8") as fobject:
                build_info = json.load(fobject)
        except ValueError:
            logger.exception(u"Unable to parse build info data from 'build.info' file!")
            return

        current_version = "v" + build_info["version"].lower()
        current_date = datetime.strptime(build_info["date"], '%Y-%m-%d %H:%M')

        # analyze JSON from GitHub todo: take/skip pre-releases
        latest_release = release_info[0]
        latest_date = datetime.strptime(latest_release["published_at"], '%Y-%m-%dT%H:%M:%SZ')
        for release in release_info:
            date_object = datetime.strptime(release["published_at"], '%Y-%m-%dT%H:%M:%SZ')

            if date_object > latest_date:
                latest_date = date_object
                latest_release = release

        # if latest_release["tag_name"].lower() != current_version and latest_date > current_date:
        #     logger.debug(u"Newer version %s published at %s found", latest_release["tag_name"], latest_date)

        url = "https://github.com/m1lhaus/woofer/releases/download/" + \
              latest_release["tag_name"] + "/" + \
              latest_release["assets"][0]["name"]

        self.downloaderThread = QThread(self)
        self.downloader = network.Downloader(url, self.download_dir)
        self.downloader.moveToThread(self.downloaderThread)

        self.downloaderThread.started.connect(self.downloader.startDownload)
        self.downloader.completedSignal.connect(self.scheduleApplicationUpdate)

        self.downloaderThread.start()

        # else:
        #     logger.debug(u"No newer version found")


    @pyqtSlot(int, unicode)
    def scheduleApplicationUpdate(self):
        # close ReleaseInfo downloader
        self.downloaderThread.quit()
        self.downloaderThread.wait(3000)        # terminate delay

        print "called"
