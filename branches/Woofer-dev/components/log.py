# -*- coding: utf-8 -*-

"""
Custom configuration and setup for logger
- set default handler to file
- add console stream (optional)
"""

__version__ = "$Id$"

import logging
import os
import sys
import datetime


def setup_logging(mode="PRODUCTION"):

    root_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    log_dir = os.path.join(root_dir, 'log')
    date = datetime.datetime.now()

    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)

    if mode == "DEBUG":
        level = logging.DEBUG
        log_path = os.path.join(log_dir, "debug_woofer_%s.log" % date.strftime("%Y-%m-%d"))
    else:
        level = logging.WARNING
        log_path = os.path.join(log_dir, "production_woofer_%s.log" % date.strftime("%Y-%m-%d"))

    # set up logging to file
    logging.basicConfig(level=level, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', filename=log_path)

    # define console handler with same level as file handler
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)

    # set up logging to console as well
    logging.getLogger('').addHandler(console)