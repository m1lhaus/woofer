# -*- coding: utf-8 -*-

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
            raise Exception(u"Given file descriptor num: %s is not supported!" % fdnum)

        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        if buf == '\n':
            self.orig_output.write(buf)
        else:
            if isinstance(buf, str):
                buf = unicode(buf, u'utf-8')
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
    msg_format = u"%(threadName)-10s  %(name)-30s %(lineno)-.5d  %(levelname)-8s %(asctime)-20s  %(message)s"
    console_formatter = logging.Formatter(msg_format)

    # --- BASIC CONFIGURATION ---
    if mode == "DEBUG":
        log_path = os.path.join(tools.LOG_DIR, u"debug_woofer_%s.log" % date.strftime("%Y-%m-%d_%H-%M-%S"))
        level = logging.DEBUG
    elif mode == "PRODUCTION":
        level = logging.WARNING
        log_path = os.path.join(tools.LOG_DIR, u"production_woofer_%s.log" % date.strftime("%Y-%m-%d_%H-%M-%S"))
    else:
        raise NotImplementedError(u"Logging mode is not implemented!")

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