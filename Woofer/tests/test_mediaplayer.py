# -*- coding: utf-8 -*-

"""
Media player test unit
"""

__version__ = "$Id$"

import os

from unittest import TestCase
from components import media


class TestMediaPlayer(TestCase):
    """
    Class testing media player functionality
    """

    mp = media.MediaPlayer()
    tests_data_folder = os.path.join(os.path.dirname(__file__), 'data')

    # sources in str form (vlc needs bytes chars => unicode is not supported)
    source_set = (os.path.join(tests_data_folder, "_12112_+ščř-+.mp3"),
                  os.path.join(tests_data_folder, "+ěščřžýáíé.mp3"),
                  os.path.join(tests_data_folder, "klnfenf.+ěščřžýáí-+'.mp3"),
                  os.path.join(tests_data_folder, "mp.mp3"))

    invalid_source_set = (os.path.join(tests_data_folder, "sasas_12112_+ščř-+.mp3"),
                          os.path.join(tests_data_folder, "asassa+ěščřžýáíé.mp3"),
                          os.path.join(tests_data_folder, ""),
                          "")

    def test_setMrl(self):
        """
        Tries to set valid source path to file and tests if given path was set as mrl
        """
        for source in self.source_set:
            self.mp.setMrl(source)

            # mrl is in unusual string format, it's difficult to parse back original string
            # to compare mrls, convert source new path to mrl format as well
            new_media = self.mp.instance.media_new(source)
            new_mrl = new_media.get_mrl()
            ret_mrl = self.mp.getMrl()

            try:
                self.assertEquals(new_mrl, ret_mrl)                 # mrl comparison
                self.assertEqual(self.mp.media_list.count(), 1)     # is media list was emptied
                self.assertEqual(self.mp.source_list[0], source)
            finally:
                new_media.release()     # release manually created media class

    def test_setMrl_error(self):
        """
        Tries to set invalid source path to file and tests if method raises exception
        """
        for source in self.invalid_source_set:
            self.assertRaises(ValueError, self.mp.setMrl, source)

    def test_addMrl(self):
        """
        Tests addMrl() to valid input
        """
        # add one string source
        source = self.source_set[0]
        list_count = self.mp.media_list.count()
        self.mp.addMrl(source)
        new_list_count = self.mp.media_list.count()

        self.assertEqual(list_count + 1, new_list_count)
        self.assertIn(source, self.mp.source_list)
        self.assertEqual(new_list_count, len(self.mp.source_list))

        # add list of strings
        list_count = self.mp.media_list.count()
        self.mp.addMrl(self.source_set)
        new_list_count = self.mp.media_list.count()

        self.assertEqual(list_count + len(self.source_set), new_list_count)
        for source in self.source_set:
            self.assertIn(source, self.mp.source_list)
        self.assertEqual(new_list_count, len(self.mp.source_list))

        # add empty list
        list_count = self.mp.media_list.count()
        self.mp.addMrl([])
        new_list_count = self.mp.media_list.count()

        self.assertEqual(list_count, new_list_count)
        self.assertEqual(new_list_count, len(self.mp.source_list))

    def test_addMrl_error(self):
        """
        Tests addMrl() method to invalid input
        """
        self.assertRaises(ValueError, self.mp.addMrl, 0)
        self.assertRaises(ValueError, self.mp.addMrl, 1)
        self.assertRaises(ValueError, self.mp.addMrl, -1)
        self.assertRaises(ValueError, self.mp.addMrl, True)
        self.assertRaises(ValueError, self.mp.addMrl, "")
        self.assertRaises(ValueError, self.mp.addMrl, [""])
        self.assertRaises(ValueError, self.mp.addMrl, ("",))
        self.assertRaises(ValueError, self.mp.addMrl, ("aaaa",))

