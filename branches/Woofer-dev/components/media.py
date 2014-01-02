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
    is_playing = False
    is_paused = False
    is_stopped = True

    def __init__(self, parent=None):
        super(MediaPlayer, self).__init__(parent)

        self.instance = vlc.Instance()
        """@type: vlc.Instance"""

        logger.debug("Created instance of VLC player")

        self._media_player = self.instance.media_player_new()
        """@type: vlc.MediaPlayer"""
        self._media_list_player = self.instance.media_list_player_new()
        """@type: vlc.MediaListPlayer"""
        self._media_list = self.instance.media_list_new()
        """@type: vlc.MediaList"""

        # connect player and media list with media_list_player
        self._media_list_player.set_media_player(self._media_player)
        self._media_list_player.set_media_list(self._media_list)

        self.__setupEvents()

        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self.timer_tick)
        logger.debug("Created woofer player instance")

    def __setupEvents(self):
        self.media_player_event_manager = self._media_player.event_manager()
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerOpening, self.playerStateChanged)
        # self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerBuffering, self.playerStateChanged)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self.playerStateChanged)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self.playerStateChanged)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self.playerStateChanged)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerForward, self.playerStateChanged)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerBackward, self.playerStateChanged)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.playerStateChanged)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self.playerStateChanged)
        # self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self.playerStateChanged)

    def setSource(self, source_path):
        """
        Set the media source that will be used by the media_player.
        @param source_path: path to media file (unicode not supported)
        @type source_path: str
        @raise ValueError: If given source path not exist
        """
        # because vlc works with bytes address (string -> bytes), source must be in str (ascii)
        # but os.path can't handle nonAscii characters => converts to unicode
        unicode_source_path = unicode(source_path, "utf-8")
        if not os.path.isfile(unicode_source_path):
            logger.error("Given source path is invalid: %s", source_path)
            raise ValueError("Given source path '%s' is invalid" % source_path)

        self.stop()

        # empty the media list
        logger.debug("Deleting items from media list")
        self.source_list = []
        self.clearList()

        # put the media to media list
        self._media_list.lock()
        self._media_list.add_media(self.instance.media_new(source_path))
        self._media_list.unlock()

        self._media_player.set_media(self._media_list.item_at_index(0))
        self.source_list.append(source_path)

        logger.debug("New media source set to: %s", source_path)

    def addSource(self, item):
        """
        Adds one or more new MRLs to media list (queue).
        If player has no media set, method automatically sets added media as current.
        @param item: one or more source path in ascii str
        @type item: str or tuple of str or list of str
        @raise ValueError: if given param is unsupported or mrl path is invalid
        """
        has_media = bool(self.getMedia())

        # for MULTIPLE items
        if isinstance(item, list) or isinstance(item, tuple):
            for single_item in item:
                # because vlc works with bytes address (string -> bytes), source must be in str (ascii)
                # but os.path can't handle nonAscii characters => converts to unicode
                unicode_source_path = unicode(single_item, "utf-8")
                if not os.path.isfile(unicode_source_path):
                    logger.error("Given mrl path is invalid: %s", unicode_source_path)
                    raise ValueError("Given mrl path is invalid. Could not locate the file on disk!")

                logger.debug("Adding new mrl: %s", single_item)
                media = self.instance.media_new(single_item)
                self._media_list.add_media(media)
                self.source_list.append(single_item)

                if not has_media:
                    logger.debug("Player has no media set, setting current media %s", item)
                    self._media_player.set_media(media)
                    has_media = True

        # for SINGLE item
        elif isinstance(item, str):
            unicode_source_path = unicode(item, "utf-8")
            if not os.path.isfile(unicode_source_path):
                logger.error("Given mrl path is invalid: %s", unicode_source_path)
                raise ValueError("Given mrl path is invalid. Could not locate the file on disk!")

            logger.debug("Adding new mrl: %s", item)
            media = self.instance.media_new(item)
            self._media_list.add_media(media)
            self.source_list.append(item)

            if not has_media:
                logger.debug("Player has no media set, setting current media %s", item)
                self._media_player.set_media(media)
                has_media = True

        else:
            logger.error("Unsupported mrl parameter type, type: %s", type(item))
            raise ValueError("Unsupported parameter type. Only list and tuple are supported for multiple items "
                             "or str for single item. Given type: %s" % type(item))

    def clearList(self):
        """
        Clears all existing items in media_list
        """
        logger.debug("Clearing media_list")
        self._media_list.lock()
        # FIXME potentially slow, checks for memory leaks
        while self._media_list.count() > 0:
            if self._media_list.remove_index(0) == -1:
                logger.error("Error when removing media from media list")
        self._media_list.unlock()

    def getMrl(self):
        """
        Get the media resource locator (mrl) from a media descriptor object.
        @return: string with mrl of media descriptor object or None if no media
        @rtype: str or None
        """
        media = self.getMedia()

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
        return self._media_player.get_media()

    def listCount(self):
        """
        @return: Number of items in media_list (queue)
        @rtype : int
        """
        return self._media_list.count()

    def play(self):
        """
        Plays the media in media_list. Emits error signal when something went wrong.
        Method returns False if there is no media or unable to play the source.
        @rtype : bool
        """
        logger.debug("Play method called")
        return self._media_list_player.play() == -1

    def pause(self):
        """
        Toggle pause (no effect if there is no media)
        """
        logger.debug("Pause method called")
        self._media_list_player.pause()

    def stop(self):
        """
        Stop (no effect if there is no media)
        """
        self._media_list_player.stop()

    def next(self):
        """
        Switches to next media in media_list if any.
        Method returns False if there is no media to switch.
        @rtype : bool
        """
        logger.debug("Next media method called")
        return self._media_list_player.next() == -1

    def prev(self):
        """
        Switches to next media in media_list if any.
        Method returns False if there is no media to switch.
        @rtype : bool
        """
        logger.debug("Previous media method called")
        return self._media_list_player.previous() == -1

    def setVolume(self, value):
        """
        Sets given volume value to player.
        Method returns False if unable to set the volume value.
        @param value: the volume in percents (0 = mute, 100 = 0dB).
        @type value: int
        @rtype: bool
        @raise ValueError: if value not in range [0, 100]
        """
        if 0 <= value <= 100:
            logger.debug("Setting volume to value %s", value)
            return self._media_player.audio_set_volume(int(value)) == -1
        else:
            raise ValueError("Volume must be in range <0, 100>")

    def volume(self):
        """
        Get current software audio volume in range [0, 100].
        @return: the software volume in percents (0 = mute, 100 = nominal / 0dB).
        @rtype: int
        """
        return self._media_player.audio_get_volume()

    def setTime(self, new_time):
        """
        Set the movie time (in ms). This has no effect if no media is being played.
        Not all formats and protocols support this. Rather use setPosition() method!
        Method returns False if media is not seekable.
        @param new_time: the movie time (in ms).
        @type new_time: int
        @rtype: bool
        @raise ValueError: if value not in range [0, totalTime]
        """
        if not self._media_player.is_seekable():
            logger.error("Media is not seekable")
            return False

        total_time = self.totalTime()
        if 0 <= new_time <= total_time:
            self._media_player.set_time(int(new_time))
            logger.debug("Media play set to new time: %s ms", new_time)
        else:
            raise ValueError("New time must be in range [0, %d]" % total_time)

        return True

    def setPosition(self, new_pos):
        """
        Set movie position as percentage between 0.0 and 1.0. This has no effect if playback is not enabled.
        This might not work depending on the underlying input format and protocol.
        Method returns False if media is not seekable.
        @param new_pos: the position
        @type new_pos: int
        @rtype: bool
        @raise ValueError: if value not in range [0, 1.0]
        """
        if not self._media_player.is_seekable():
            logger.error("Media is not seekable")
            return False

        if 0 <= new_pos <= 1.0:
            self._media_player.set_position(new_pos)
            logger.debug("Media play set to new position: %s", new_pos)
        else:
            raise ValueError("New position must be in range [0, 1.0]")

        return True

    def currentTime(self):
        """
        Get the current time (in ms).
        Method returns None if no media set.
        @rtype : int or None
        """
        time = self._media_player.get_time()

        if time == -1:
            logger.warning("There is no media set to get current time")
            time = None

        return time

    def totalTime(self):
        """
        Get the current media length (in ms).
        Method returns None if no media set.
        @rtype : int or None
        """
        length = self._media_player.get_length()

        if length == -1:
            logger.warning("There is no media set to get its length")
            length = None

        return length

    def remainingTime(self):
        """
        Get the current media remaining time (in ms)
        Method returns None if no media set.
        @rtype : int or None
        """
        current_time = self.currentTime()
        total_time = self.totalTime()

        if current_time == -1 or total_time == -1:
            logger.warning("There is no media set to get remaining time")
            remaining_time = None
        else:
            remaining_time = total_time - current_time

        return remaining_time

    def playerStateChanged(self, event):
        """
        Called when media_player state has changed.
        @type event: vlc.Event
        """

        if event.type == vlc.EventType.MediaPlayerOpening:
            logger.debug("Opening the media")
        elif event.type == vlc.EventType.MediaPlayerPlaying:
            logger.debug("Media player is playing")
            self.is_playing = True
            self.is_paused = False
            self.is_stopped = False
            self.tick_timer.start(self.TICK_INTERVAL)
        elif event.type == vlc.EventType.MediaPlayerPaused:
            logger.debug("Media player paused")
            self.is_playing = False
            self.is_paused = True
            self.is_stopped = False
            self.tick_timer.stop()
        elif event.type == vlc.EventType.MediaPlayerStopped:
            logger.debug("Media player is stopped")
            self.is_playing = False
            self.is_paused = False
            self.is_stopped = True
            self.tick_timer.stop()
        elif event.type == vlc.EventType.MediaPlayerForward:
            logger.debug("Media player skipped forward")
        elif event.type == vlc.EventType.MediaPlayerBackward:
            logger.debug("Media player skipped backward")
        elif event.type == vlc.EventType.MediaPlayerEndReached:
            logger.debug("Media end reached")
        elif event.type == vlc.EventType.MediaPlayerEncounteredError:
            logger.debug("Media encountered error")
        elif event.type == vlc.EventType.MediaPlayerTimeChanged:
            # logger.debug("Media Player Time Changed encountered error")
            print event.u.new_time

    @Slot()
    def timer_tick(self):
        self.tick.emit(self.currentTime())


class RadioPlayer(QObject):
    """
    Internet radio streaming class
    """