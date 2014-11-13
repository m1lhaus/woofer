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

        self.log_dir = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), 'log')
        self.delay = 5 * (60 * 1000)                        # 5 minutes in ms

        logger.debug(u"LogCleaner initialized")

    def start(self):
        logger.debug(u"Scheduling log cleaner - delay %s", self.delay)
        QTimer.singleShot(self.delay, self.clean)

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
            fpath = unicode(os.path.join(self.log_dir, ffile), sys.getfilesystemencoding())

            # if file is older than X days, than remove the file
            if os.stat(fpath).st_mtime < time_past_limit:
                try:
                    os.remove(fpath)
                except OSError:
                    logger.exception(u"Unable to remove log file: %s", fpath)

        logger.debug(u"Scheduled log file cleaning completed.")
