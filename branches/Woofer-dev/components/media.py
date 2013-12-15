# -*- coding: utf-8 -*-

"""
Media components
- Media player
- Radio player
"""

__version__ = "$Id$"

import logging
import os

from PySide.QtGui import *
from PySide.QtCore import *

from components import vlc

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class MediaPlayer(QObject):
    """
    Media player class
    """

    TICK_INTERVAL = 1000        # in ms

    error = Signal(str)
    tick = Signal(int)

    source_list = []

    def __init__(self, parent=None):
        super(MediaPlayer, self).__init__(parent)

        self.instance = vlc.Instance()
        """:type: vlc.Instance"""

        logger.debug("Created instance of VLC player")

        self.media_player = self.instance.media_player_new()
        """:type: vlc.MediaPlayer"""
        self.media_list_player = self.instance.media_list_player_new()
        """:type: vlc.MediaListPlayer"""
        self.media_list = self.instance.media_list_new()
        """:type: vlc.MediaList"""

        # connect player and media list with media_list_player
        self.media_list_player.set_media_player(self.media_player)
        self.media_list_player.set_media_list(self.media_list)

        logger.debug("Created media player reference")

        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self.timer_tick)

    def setMrl(self, source_path):
        """
        Set the media source that will be used by the media_player.
        @param source_path: path to media file (unicode not supported)
        @type source_path: str
        @raise ValueError: If given source path not exist
        """
        # because vlc works with bytes address (string -> bytes), source must be in str (ascii)
        # but os.path can't handle nonAscii characters => convert to unicode
        unicode_source_path = unicode(source_path, "utf-8")
        if not os.path.isfile(unicode_source_path):
            logger.error("Given source path is invalid: %s", source_path)
            raise ValueError("Given source path '%s' is invalid" % source_path)

        self.stop()

        # empty the media list
        logger.debug("Deleting items from media list")
        self.source_list = []
        while self.media_list.count() > 0:
            self.media_list.lock()
            status = self.media_list.remove_index(0)
            self.media_list.unlock()

            if status == -1:
                logger.error("Error when removing media from media list")

        # put the media to media list and set as current in media player
        self.media_list.lock()
        self.media_list.add_media(self.instance.media_new(source_path))
        self.media_list.unlock()
        self.media_player.set_media(self.media_list.item_at_index(0))
        self.source_list.append(source_path)

        logger.debug("New media source set to: %s", source_path)

    def addMrl(self, item):
        """
        Adds one or more new MRLs to media list (queue)
        @param item: one or more source path in ascii str
        @type item: str or tuple of str or list of str
        @raise ValueError: if given param is unsupported or mrl path is invalid
        """
        # for MULTIPLE items
        if isinstance(item, list) or isinstance(item, tuple):
            for single_item in item:
                unicode_source_path = unicode(single_item, "utf-8")
                if not os.path.isfile(unicode_source_path):
                    logger.error("Given mrl path is invalid: %s", unicode_source_path)
                    raise ValueError("Given mrl path is invalid. Could not locate the file on disk!")

                self.media_list.add_media(self.instance.media_new(single_item))
                self.source_list.append(single_item)

        # for SINGLE item
        elif isinstance(item, str):
            unicode_source_path = unicode(item, "utf-8")
            if not os.path.isfile(unicode_source_path):
                logger.error("Given mrl path is invalid: %s", unicode_source_path)
                raise ValueError("Given mrl path is invalid. Could not locate the file on disk!")

            self.media_list.add_media(self.instance.media_new(item))
            self.source_list.append(item)

        else:
            logger.error("Unsupported mrl parameter type, type: %s", type(item))
            raise ValueError("Unsupported parameter type. Only list and tuple are supported for multiple items "
                             "or str for single item. Given type: %s" % type(item))

    def getMrl(self):
        """
        Get the media resource locator (mrl) from a media descriptor object.
        @return: string with mrl of media descriptor object or None if no media
        @rtype: str or None
        """
        media = self.media_player.get_media()

        if media:
            return media.get_mrl()
        else:
            return None

    def getMedia(self):
        """
        Get the media used by the media_player.
        @return: the media associated with p_mi, or None if no media is associated.
        @rtype: vlc.Media or None
        """
        return self.media_player.get_media()

    def play(self):
        """
        Play (emits error signal when something went wrong)
        """
        logger.debug("Play method called")

        if self.media_player.play() == -1:
            logger.warning("Error. Unable to play the media")
            self.error.emit("Error. Unable to play the media")
            return

        self.tick_timer.start(self.TICK_INTERVAL)

    def pause(self):
        """
        Toggle pause (no effect if there is no media)
        """
        logger.debug("Pause method called")

        self.media_player.pause()
        self.tick_timer.stop()

    def stop(self):
        """
        Stop (no effect if there is no media)
        """
        self.media_player.stop()
        self.tick_timer.stop()

    def isPlaying(self):
        """
        @return: if player is currently playing
        @rtype : bool
        """
        return self.media_player.is_playing() == 1

    def next(self):
        pass

    def prev(self):
        pass

    def queue(self):
        pass

    def enqueue(self):
        pass

    def setVolume(self, value):
        """
        Set current software audio volume.
        @param value: the volume in percents (0 = mute, 100 = 0dB).
        @type value: int
        @raise ValueError: if value not in range [0, 100]
        """
        if 0 <= value <= 100:
            if self.media_player.audio_set_volume(int(value)) == -1:
                logger.error("Error. Unable to set new volume value: %s", value)
            else:
                logger.debug("Volume set to '%s'", value)

        else:
            raise ValueError("Volume must be in range <0, 100>")

    def volume(self):
        """
        Get current software audio volume.
        @return: the software volume in percents (0 = mute, 100 = nominal / 0dB).
        @rtype: int
        """
        return self.media_player.audio_get_volume()

    def setTime(self, new_time):
        """
        Set the movie time (in ms). This has no effect if no media is being played.
        Not all formats and protocols support this. Rather use setPosition() method!
        @param new_time: the movie time (in ms).
        @type new_time: int
        @raise ValueError: if value not in range [0, totalTime]
        """
        if not self.media_player.is_seekable():
            logger.error("Media is not seekable")
            return

        total_time = self.totalTime()
        if 0 <= new_time <= total_time:
            self.media_player.set_time(int(new_time))
            logger.debug("Media play set to new time: %s ms", new_time)

        else:
            raise ValueError("New time must be in range [0, %d]" % total_time)

    def setPosition(self, new_pos):
        """
        Set movie position as percentage between 0.0 and 1.0. This has no effect if playback is not enabled.
        This might not work depending on the underlying input format and protocol.
        @param new_pos: the position
        @type new_pos: int
        @raise ValueError: if value not in range [0, 1.0]
        """
        if not self.media_player.is_seekable():
            logger.error("Media is not seekable")
            return

        if 0 <= new_pos <= 1.0:
            self.media_player.set_position(new_pos)
            logger.debug("Media play set to new position: %s", new_pos)

        else:
            raise ValueError("New position must be in range [0, 1.0]")

    def currentTime(self):
        """
        Get the current time (in ms).
        @return: the media time (in ms), or -1 if there is no media.
        @rtype : int
        """
        time = self.media_player.get_time()

        if time == -1:
            logger.warning("There is no media set to get current time")

        return time

    def totalTime(self):
        """
        Get the current media length (in ms).
        @return: the media length (in ms), or -1 if there is no media.
        @rtype : int
        """
        length = self.media_player.get_length()

        if length == -1:
            logger.warning("There is no media set to get its length")

        return length

    def remainingTime(self):
        """
        Get the current media remaining time (in ms)
        @return: the media remaining time (in ms), or -1 if there is no media.
        @rtype : int
        """
        current_time = self.currentTime()
        total_time = self.totalTime()

        if current_time == -1 or total_time == -1:
            logger.warning("There is no media set to get remaining time")
            return -1

        else:
            return total_time - current_time

    def timer_tick(self):
        self.tick.emit(self.currentTime())


class RadioPlayer(QObject):
    """
    Internet radio streaming class
    """