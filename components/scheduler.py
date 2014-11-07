# -*- coding: utf-8 -*-

"""
Scheduler/maintenance modules.
"""

import logging
import os
import time
import sys

from PyQt4.QtCore import *


logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)


class LogCleaner(QObject):
    """
    Cleans old log text files, which are no longer needed.
    Every time user opens Woofer player, new log file is created.
    This behaviour leeds to high amount of redundant (nothing saying) log files.
    Log file is important only when error occurs and user want to participate and provide logs.
    Log cleaner runs in separated thread.
    """

    def __init__(self):
        super(LogCleaner, self).__init__()

        self.LOG_DIR = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), 'log')
        self.DELAY = 5 * (60 * 1000)                        # 5 minutes in ms

        logger.debug(u"LogCleaner initialized")

    def start(self):
        logger.debug(u"Scheduling log cleaner - delay %s", self.DELAY)
        QTimer.singleShot(self.DELAY, self.clean)

    def clean(self):
        """
        Thread worker.
        Deletes old files from /log folder.
        :return:
        """
        if not os.path.isdir(self.LOG_DIR):
            logger.error(u"Log dir under '%s' doesn't exist!", self.LOG_DIR)

        logger.debug(u"Launching scheduled log file cleaning...")

        now = time.time()
        one_day = 86400
        time_past_limit = now - (7 * one_day)
        for ffile in os.listdir(self.LOG_DIR):
            fpath = unicode(os.path.join(self.LOG_DIR, ffile), sys.getfilesystemencoding())

            # if file is older than X days, than remove the file
            if os.stat(fpath).st_mtime < time_past_limit:
                try:
                    os.remove(fpath)
                except OSError:
                    logger.exception(u"Unable to remove log file: %s", fpath)

        logger.debug(u"Scheduled log file cleaning completed.")
