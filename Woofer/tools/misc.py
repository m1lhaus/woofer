# -*- coding: utf-8 -*-

"""
Various tools and functions
"""
__version__ = "$Id: misc.py 36 2014-02-20 21:23:02Z m1lhaus $"

import os
import sys
from contextlib import contextmanager

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


def unicode2bytes(string):
    """
    Converts string (basestring) to unicode and byte string (ascii str).
    @type string: str or unicode
    @rtype: (unicode, str)
    """
    assert isinstance(string, basestring)

    if isinstance(string, unicode):
        byte_str = string.encode("utf8")
        unicode_str = string
    else:
        byte_str = string
        unicode_str = unicode(string, "utf-8")

    return unicode_str, byte_str


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


@contextmanager
def stderr_redirected(to=os.devnull):
    """
    Redirects stderr to new device (nulldev is default).
    """

    fd = sys.stderr.fileno()

    def _redirect_stderr(to, py_to=None):
        print "fd", fd
        # sys.stderr.close()                          # + implicit flush()
        os.dup2(to.fileno(), fd)             # fd writes to 'to' file
        sys.stderr = os.fdopen(py_to.fileno(), 'w')         # Python writes to fd
        print "fd", fd
        # sys.stderr = os.fdopen(fd, 'w')         # Python writes to fd
        print sys.stderr.fileno()

    def get_back(old_stderr):
        print sys.stderr.fileno()
        os.dup2(3, fd)             # fd writes to 'to' file
        # sys.stderr.close()
        sys.stderr = os.fdopen(fd, 'w')         # Python writes to fd
        print sys.stderr.writable()
        print sys.stderr.fileno()

    with os.fdopen(os.dup(fd), 'w') as old_stderr:      # zavře 3
        with open(to, 'w') as f:                        # zavře 4ku
            _redirect_stderr(to=f, py_to=old_stderr)
        try:
            yield                                   # allow code to be run with the redirected stdout
        finally:
            pass
            # _redirect_stderr(to=old_stderr)         # restore stdout.
            get_back(old_stderr)                                        # buffering and flags such as
                                                    # CLOEXEC may be different


    # os.close(3)




