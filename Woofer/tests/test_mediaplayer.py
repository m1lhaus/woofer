# -*- coding: utf-8 -*-

"""
Media player test unit
"""

__version__ = "$Id$"

import os
import time

from unittest import TestCase
from components import media

WAIT_TIME = 1   # in sec


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

    def test_setSource(self):
        """
        Tries to set valid source path to file and tests if given path was set as mrl
        """
        for source in self.source_set:
            self.mp.setSource(source)

            # mrl is in unusual string format, it's difficult to parse back original string
            # to compare mrls, convert source new path to mrl format as well
            new_media = self.mp.instance.media_new(source)
            new_mrl = new_media.get_mrl()
            ret_mrl = self.mp.getMrl()

            try:
                self.assertEquals(new_mrl, ret_mrl)                 # mrl comparison
                self.assertEqual(self.mp._media_list.count(), 1)     # is media list was emptied
                self.assertEqual(self.mp.source_list[0], source)
            finally:
                new_media.release()     # release manually created media class

    def test_setSource_error(self):
        """
        Tries to set invalid source path to file and tests if method raises exception
        """
        for source in self.invalid_source_set:
            self.assertRaises(ValueError, self.mp.setSource, source)

    def test_addSource(self):
        """
        Tests addMrl() to valid input
        """
        # add one string source
        source = self.source_set[0]
        list_count = self.mp._media_list.count()
        self.mp.addSource(source)
        new_list_count = self.mp._media_list.count()

        self.assertEqual(list_count + 1, new_list_count)
        self.assertIn(source, self.mp.source_list)
        self.assertEqual(new_list_count, len(self.mp.source_list))

        # add list of strings
        list_count = self.mp._media_list.count()
        self.mp.addSource(self.source_set)
        new_list_count = self.mp._media_list.count()

        self.assertEqual(list_count + len(self.source_set), new_list_count)
        for source in self.source_set:
            self.assertIn(source, self.mp.source_list)
        self.assertEqual(new_list_count, len(self.mp.source_list))

        # add empty list
        list_count = self.mp._media_list.count()
        self.mp.addSource([])
        new_list_count = self.mp._media_list.count()

        self.assertEqual(list_count, new_list_count)
        self.assertEqual(new_list_count, len(self.mp.source_list))

    def test_addSource_error(self):
        """
        Tests addMrl() method to invalid input
        """
        self.assertRaises(ValueError, self.mp.addSource, 0)
        self.assertRaises(ValueError, self.mp.addSource, 1)
        self.assertRaises(ValueError, self.mp.addSource, -1)
        self.assertRaises(ValueError, self.mp.addSource, True)
        self.assertRaises(ValueError, self.mp.addSource, "")
        self.assertRaises(ValueError, self.mp.addSource, [""])
        self.assertRaises(ValueError, self.mp.addSource, ("",))
        self.assertRaises(ValueError, self.mp.addSource, ("aaaa",))

    def test_clearList(self):
        """
        Fills media_list and then test clearList() method
        """
        for source in self.source_set:
            self.mp.addSource(source)

        if self.mp.listCount() != 0:
            self.mp.clearList()
        else:
            self.fail()

        self.assertEqual(self.mp.listCount(), 0)

    def test_playPauseStop(self):
        """
        Sets media, and tries to play, pause and stop
        """
        self.mp.setSource(self.source_set[1])

        self.mp.play()
        time.sleep(WAIT_TIME)
        self.assertTrue(self.mp.is_playing)

        self.mp.pause()
        time.sleep(WAIT_TIME)
        self.assertTrue(self.mp.is_paused)

        self.mp.stop()
        time.sleep(WAIT_TIME)
        self.assertTrue(self.mp.is_stopped)



