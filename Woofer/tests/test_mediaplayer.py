# -*- coding: utf-8 -*-

"""
Media player test unit
"""

__version__ = "$Id$"

import os
import time

from unittest import TestCase
from components import media
from components import vlc
from tools.misc import unicode2bytes

WAIT_TIME = 1   # in sec


class TestMediaPlayer(TestCase):
    """
    Class testing media player functionality
    """

    mp = media.MediaPlayer()
    tests_data_folder = os.path.join(os.path.dirname(__file__), 'data')
    vlc_instance = vlc.Instance()

    # sources in str form (vlc needs bytes chars => unicode is not supported)
    source_set = (os.path.join(tests_data_folder, u"_12112_+ščř-+.mp3"),
                  os.path.join(tests_data_folder, u"+ěščřžýáíé.mp3"),
                  os.path.join(tests_data_folder, u"klnfenf.+ěščřžýáí-+'.mp3"),
                  os.path.join(tests_data_folder, u"mp.mp3"))

    invalid_source_set = (os.path.join(tests_data_folder, u"sasas_12112_+ščř-+.mp3"),
                          os.path.join(tests_data_folder, u"asassa+ěščřžýáíé.mp3"),
                          os.path.join(tests_data_folder, u""),
                          u"")

    def test_setSource(self):
        """
        Tries to set valid source path to file and tests if given path was set as mrl
        """
        for source in self.source_set:
            unicode_str, byte_str = unicode2bytes(source)
            self.mp.setSource(unicode_str)

            # mrl is in unusual string format, it's difficult to parse back original string
            # to compare mrls, convert source new path to mrl format as well
            new_media = self.vlc_instance.media_new(byte_str)
            new_mrl = new_media.get_mrl()
            ret_mrl = self.mp.getMrl()
            new_media.release()

            self.assertEquals(new_mrl, ret_mrl)                     # mrl comparison
            self.assertEqual(self.mp.listCount(), 1)        # is media only one in the list
            # self.assertEqual(self.mp.source_list[0], unicode_str)        # is media stored in the helper list

    def test_addSource(self):
        """
        Tests addMrl() to valid input
        """
        source = self.source_set[0]
        unicode_str, byte_str = unicode2bytes(source)

        list_count = self.mp.listCount()
        self.mp.addSource(unicode_str)
        new_list_count = self.mp.listCount()

        self.assertEqual(list_count + 1, new_list_count)
        # self.assertIn(unicode_str, self.mp.source_list)
        # self.assertEqual(new_list_count, len(self.mp.source_list))

    def test_addSources(self):
        list_count = self.mp.listCount()
        self.mp.addSources(self.source_set)
        new_list_count = self.mp.listCount()

        self.assertEqual(list_count + len(self.source_set), new_list_count)
        for source in self.source_set:
            unicode_str, byte_str = unicode2bytes(source)
            # self.assertIn(unicode_str, self.mp.source_list)
        # self.assertEqual(new_list_count, len(self.mp.source_list))

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



