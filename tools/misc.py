# -*- coding: utf-8 -*-

"""
Various tools and functions
"""


import os
import sys


def check_binary_type(path):
    """
    Method reads PE header and get binary type (x32 vs x64)
    @param path: path to existing file (executable or dll)
    @rtype: bool
    """
    if not os.path.isfile(path):
        return None

    import struct

    bin_type = None
    IMAGE_FILE_MACHINE_I386 = 332
    IMAGE_FILE_MACHINE_IA64 = 512
    IMAGE_FILE_MACHINE_AMD64 = 34404

    with open(path, "rb") as f:
        s = f.read(2)
        if s != "MZ":
            print("check_binary_type - Not an EXE file!")

        else:
            f.seek(60)
            s = f.read(4)
            header_offset = struct.unpack("<L", s)[0]
            f.seek(header_offset + 4)
            s = f.read(2)
            machine = struct.unpack("<H", s)[0]

            if machine == IMAGE_FILE_MACHINE_I386:
                bin_type = "IA-32 (32-bit x86)"
            elif machine == IMAGE_FILE_MACHINE_IA64:
                bin_type = "IA-64 (Itanium)"
            elif machine == IMAGE_FILE_MACHINE_AMD64:
                bin_type = "AMD64 (64-bit x86)"
            else:
                bin_type = "Unknown"

    return bin_type


class ErrorMessages(object):
    """
    Error messages enums.
    """
    WARNING = 0
    ERROR = 1
    CRITICAL = 2
    INFO = 3


class PlaybackSources(object):
    """
    Playback sources enums.
    """
    FILES = 0
    PLAYLISTS = 1
    RADIO = 2


class RedirectDescriptor(object):

    def __init__(self):
        self.original_stderr_descriptor = None

    def redirect_C_stderr_null(self):
        """
        BREAKS WITH PYINSTALLER!!!

        Redirects all stderr ouput to new descriptor. So original stderr ouput will be thrown away.
        Only new sys.stderr output since this method call will be printed out.

        ##program init##
            1 -> something points to the stderr
            2 -> other library points to the stderr
            * redirect_C_stderr_null() called
            3 -> next thing points to the stderr
            4 -> error log points to the stderr
            * redirect_C_stderr_back() called

        ##later program goes like this ###
            called * redirect_C_stderr_null() *
            1 prints something ---> will be ignored (old stderr points nowhere)
            2 prints something ---> will be ignored (old stderr points nowhere)
            3 prints something ---> will be printed on stderr pipe
            4 prints something ---> will be printed on stderr pipe
            called * redirect_C_stderr_back() *
            1 prints something ---> will be printed on stderr pipe
            2 prints something ---> will be printed on stderr pipe
            3 prints something ---> will be ignored (old stderr points nowhere)
            4 prints something ---> will be ignored (old stderr points nowhere)
        """
        sys.stderr.flush()                                  # flush all data
        stderr_duplicate = os.dup(sys.stderr.fileno())      # creates copy of stderr
        self.original_stderr_descriptor = stderr_duplicate  # save descriptor number
        devnull = os.open(os.devnull, os.O_WRONLY)          # creates 'black hole'
        os.dup2(devnull, sys.stderr.fileno())               # redirects orig. low-level stderr descriptor to 'back hole'
        os.close(devnull)                                   # close the 'black hole', so no data will sent there anymore
        sys.stderr = os.fdopen(stderr_duplicate, 'w')       # python needs some stderr, so open new one

    def redirect_C_stderr_back(self):
        """
        Redirects backed up stderr to original pipe.
        @raise AssertionError: Descriptor is not redirected.
        """
        assert self.original_stderr_descriptor is not None
        sys.stderr.flush()                               #
        os.dup2(self.original_stderr_descriptor, 2)         # recover original orig. low-level stderr descriptor
        sys.stderr = os.fdopen(2, 'w')                      # reopen; backed up descriptor is closed automatically

