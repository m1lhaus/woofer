# -*- coding: utf-8 -*-

"""
Custom configuration and setup for logger
- set logging level
- set default handler to file
- set ERROR logs to stderr
- add DEBUG and INFO logs to stdout (only in DEBUG mode)
"""


import logging
import os
import sys
import datetime


class InfoFilter(logging.Filter):
    """
    Logging filter. Filters out ERROR messages and higher.
    """
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


def setup_logging(mode):

    root_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    log_dir = os.path.join(root_dir, 'log')
    date = datetime.datetime.now()

    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)

    msg_format = "%(threadName)-10s  %(name)-30s %(lineno)-.5d  %(levelname)-8s %(asctime)-20s  %(message)s"
    console_formatter = logging.Formatter(msg_format)

    # --- BASIC CONFIGURATION ---
    if mode == "DEBUG":
        log_path = os.path.join(log_dir, "debug_woofer_%s.log" % date.strftime("%Y-%m-%d_%H-%M-%S"))
        level = logging.DEBUG
    elif mode == "PRODUCTION":
        level = logging.WARNING
        log_path = os.path.join(log_dir, "production_woofer_%s.log" % date.strftime("%Y-%m-%d_%H-%M-%S"))
    else:
        raise NotImplementedError("Logging mode is not implemented!")

    logging.basicConfig(level=level, format=msg_format, filename=log_path)
    # ---------------------------

    # ----- CONSOLE HANDLERS ----
    # setup logging warning and errors to stderr
    console_err = logging.StreamHandler(stream=sys.stderr)
    console_err.setLevel(logging.WARNING)
    console_err.setFormatter(console_formatter)
    logging.getLogger('').addHandler(console_err)

    # add console handler with the DEBUG level
    if level == logging.DEBUG:
        console_std = logging.StreamHandler(stream=sys.stdout)
        console_std.setLevel(logging.DEBUG)
        console_std.addFilter(InfoFilter())
        console_std.setFormatter(console_formatter)
        logging.getLogger('').addHandler(console_std)
    # ----------------------------