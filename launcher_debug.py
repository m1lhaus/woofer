#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Starts application in DEBUG mode.
"""

__version__ = "$Id$"


import launcher


if __name__ == "__main__":
    # launcher.StdErrRedirector.redirect_C_stderr_null()
    launcher.application_start('DEBUG')
    # launcher.StdErrRedirector.redirect_C_stderr_back()