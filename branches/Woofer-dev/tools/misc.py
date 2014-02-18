# -*- coding: utf-8 -*-

"""
Various tools and functions
"""
__version__ = "$Id$"

import os
import sys


def enum(*sequential, **named):
    """
    Automatically or manually numbered enums. Enums are numbered from zero.
    Watch for number conflicts (auto + manual)!
    @param sequential: (i.e. 'WARNING', 'ERROR', 'CRITICAL')
    @param named: (i.e. DOG=100, CAT=101, MOUSE=102)
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


def moveToTrash(file_path):
    """
    Moves file/folder to Trash.
    @type file_path: str
    @raise OSError: Error with message and number.
    """
    from send2trash import send2trash
    send2trash(file_path)


class RedirectDescriptor(object):

    desc_backup = None

    def redirect_C_stderr_null(self):
        """
        Redirects stderr to new descriptor. For stdout is code identical.
        """
        sys.stderr.flush()                                  # flush all data
        new_desc = os.dup(sys.stderr.fileno())              # create new descriptor from original stderr (copy)
        self.desc_backup = new_desc                         # save descriptor number
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stderr.fileno())               # redirect C layer descriptor to null
        os.close(devnull)
        sys.stderr = os.fdopen(new_desc, 'w')               # but revert Python stderr to normal

    def redirect_C_stderr_back(self):
        """
        Redirects backuped stderr to original pipe.
        @raise AssertionError: No backup present.
        """
        assert self.desc_backup is not None
        sys.stderr.flush()
        os.dup2(self.desc_backup, 2)
        sys.stderr = os.fdopen(2, 'w')                      # backuped descriptor is closed automatically

