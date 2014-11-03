# -*- coding: utf-8 -*-

"""
Unittest for woofer.py
"""

__version__ = "$Id: test_woofer.py 143 2014-10-26 13:52:36Z m1lhaus $"

import sys
import os

from unittest import TestCase

import sip
sip.setapi('QDate', 2)
sip.setapi('QDateTime', 2)
sip.setapi('QString', 2)
sip.setapi('QTextStream', 2)
sip.setapi('QTime', 2)
sip.setapi('QUrl', 2)
sip.setapi('QVariant', 2)

from PyQt5.QtCore import QSharedMemory


class TestWoofer(TestCase):

    def test_obtainSharedMemoryLock(self):
        from woofer import obtainSharedMemoryLock

        sharedMemoryLock, error_str = obtainSharedMemoryLock()
        self.assertTrue(isinstance(sharedMemoryLock, QSharedMemory))
        sharedMemoryLock2, error_str2 = obtainSharedMemoryLock()            # like another app has been launched
        self.assertFalse(isinstance(sharedMemoryLock2, QSharedMemory))

    def test_foundLibVLC(self):
        from woofer import foundLibVLC
        from tools.misc import check_binary_type

        if os.name == "nt":
            # check if libvlc.dll exists and is usable
            libvlc_lib_path = os.path.join(os.getcwd(), 'libvlc', 'win', 'libvlc.dll')
            self.assertTrue(os.path.isfile(libvlc_lib_path))
            self.assertEqual(check_binary_type(libvlc_lib_path), check_binary_type(sys.executable))

            # check if has been used by libvlc wrapper
            self.assertTrue(foundLibVLC())
        else:
            self.fail("This test is not implemented for Linux, yet!")






