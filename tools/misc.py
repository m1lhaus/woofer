# -*- coding: utf-8 -*-

"""
Various tools and functions
"""

__version__ = "$Id$"


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
