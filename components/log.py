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
-   Stream redirector - copies all stderr stream to logger as error messages
-   Custom configuration and setup for logger
    - set logging level
    - set default handler to file
    - set ERROR logs to stderr
    - add DEBUG and INFO logs to stdout (only in DEBUG mode)
"""

import logging
import os
import sys
import datetime

import tools


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects stdout/stderr writes to a logger instance.
    """

    def __init__(self, fdnum, logger, log_level=logging.INFO):
        if fdnum == 0:
            sys.stdout = self
            self.orig_output = sys.__stdout__
        elif fdnum == 1:
            sys.stderr = self
            self.orig_output = sys.__stderr__
        else:
            raise Exception("Given file descriptor num: %s is not supported!" % fdnum)

        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        # buf = buf.decode(sys.getfilesystemencoding())
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def __getattr__(self, name):
        return self.orig_output.__getattribute__(name)              # pass all other methods to original fd


class InfoFilter(logging.Filter):
    """
    Logging filter. Filters out ERROR messages and higher.
    """
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


def setup_logging(mode):
    if not os.path.isdir(tools.LOG_DIR):
        os.mkdir(tools.LOG_DIR)

    date = datetime.datetime.now()
    msg_format = "%(threadName)-10s  %(name)-30s %(lineno)-.5d  %(levelname)-8s %(asctime)-20s  %(message)s"
    console_formatter = logging.Formatter(msg_format)

    # --- BASIC CONFIGURATION ---
    if mode == "DEBUG":
        log_path = os.path.join(tools.LOG_DIR, "debug_woofer_%s.log" % date.strftime("%Y-%m-%d_%H-%M-%S"))
        level = logging.DEBUG
    elif mode == "PRODUCTION":
        level = logging.WARNING
        log_path = os.path.join(tools.LOG_DIR, "production_woofer_%s.log" % date.strftime("%Y-%m-%d_%H-%M-%S"))
    else:
        raise NotImplementedError("Logging mode is not implemented!")

    logging.basicConfig(level=level, format=msg_format, filename=log_path)
    # ---------------------------

    logger = logging.getLogger('')      # get root logger

    # redirects all stderr output (exceptions, etc.) to logger ERROR level
    sys.stderr = StreamToLogger(1, logger, logging.ERROR)

    # if not win32gui application, add console handlers
    if not tools.IS_WIN32_EXE:
        # setup logging warning and errors to stderr
        console_err = logging.StreamHandler(stream=sys.__stderr__)      # write to original stderr, not to the logger
        console_err.setLevel(logging.WARNING)
        console_err.setFormatter(console_formatter)
        logger.addHandler(console_err)

        # add console handler with the DEBUG level
        if level == logging.DEBUG:
            console_std = logging.StreamHandler(stream=sys.__stdout__)
            console_std.setLevel(logging.DEBUG)
            console_std.addFilter(InfoFilter())
            console_std.setFormatter(console_formatter)
            logger.addHandler(console_std)