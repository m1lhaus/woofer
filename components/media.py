# -*- coding: utf-8 -*-

"""
Media components
- Media player
- Radio player
"""

__version__ = "$Id$"

import time
import logging
import os
import random


from PySide.QtGui import *
from PySide.QtCore import *

from components import vlc
from tools import misc
from tools.misc import unicode2bytes

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class MediaPlayer(QObject):
    """
    Media player class
    """

    TICK_INTERVAL = 1000        # in ms

    error = Signal(str)
    tick = Signal(int)

    mediaAdded = Signal(list, bool)
    playing = Signal()
    stopped = Signal()
    paused = Signal()
    timeChanged = Signal(int)
    positionChanged = Signal(float)
    mediaChanged = Signal(int)          # TODO: add metadata
    endReached = Signal(bool)

    def __init__(self, parent=None):
        super(MediaPlayer, self).__init__(parent)

        self.instance = vlc.Instance()
        """@type: vlc.Instance"""
        self._media_player = self.instance.media_player_new()
        """@type: vlc.MediaPlayer"""
        self._media_list = self.instance.media_list_new()
        """@type: vlc.MediaList"""
        logger.debug("Core instances of VLC player created")

        self.id_playlist = []
        self.playlist_pointer = 0        # points which media in idPlaylist is being played
        self.playlist_len = 0

        self.is_playing = False
        self.is_paused = False
        self.is_stopped = True
        self.append_mode = True
        self.shuffle_mode = False
        self.repeat_mode = False

        self.__setupEvents()

        # self.endReached.connect(self.stop)
        self.endReached.connect(self.next)

        logger.debug("Created woofer player instance")

    def __setupEvents(self):
        self.media_player_event_manager = self._media_player.event_manager()
        # self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerOpening, self.playerStateChanged)
        # self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerBuffering, self.playerStateChanged)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self.__playingCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self.__pausedCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self.__stoppedCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerForward, self.__forwardCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerBackward, self.__backwardCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.__endReachedCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self.__errorCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self.__timeChangedCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.__positionChangedCallback)
        self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerMediaChanged, self.__mediaChangedCallback)

    @Slot()
    def addMedia(self, mList):
        """
        Adds list of media objects to player media_list.
        Usually called as slot from parser thread.
        @param mList: list of (unicode_path, media_object)
        @type mList: list of (unicode, vlc.Media)
        """
        export = []
        # todo: check for ref count
        self._media_list.lock()
        for path, media in mList:
            self._media_list.add_media(media)
            media.release()

            self.id_playlist.append(self.playlist_len)        # new media is on the end of the list
            self.playlist_len += 1
            export.append((path, media.get_duration()))
        self._media_list.unlock()

        self.mediaAdded.emit(export, self.append_mode)

        # set set_mode, set media and switch to append mode for next iteration
        if not self.append_mode:
            path, media = mList[0]
            logger.debug("Setting current media %s", path)
            self._media_player.set_media(media)
            self.append_mode = True
            self.play()         # in set_mode, Play or Play All has been chosen => play()

    def removeItem(self, index):
        """
        Removes item from media list by index.
        If media is currently being played, next media is played.
        If there is no next media, playing is stopped.
        @param index: index of removed item in media_list
        @type index: int
        """
        logger.debug("Removing media item in index: %s", index)

        # get removed and current mrl for comparison
        playedMedia = self._media_player.get_media()
        self._media_list.lock()
        removedMedia = self._media_list.item_at_index(index)
        self._media_list.unlock()
        playedMrl = playedMedia.get_mrl()
        removedMrl = removedMedia.get_mrl()
        playedMedia.release()
        removedMedia.release()

        mustChangeSong = True if playedMrl == removedMrl else False

        self._media_list.lock()
        self._media_list.remove_index(index)
        count = self._media_list.count()
        self._media_list.unlock()

        # remove id from id_playlist
        for i in xrange(len(self.id_playlist)):
            if self.id_playlist[i] == index:
                del self.id_playlist[i]
                self.id_playlist[i:] = [x-1 for x in self.id_playlist[i:]]     # faster way than iterate over whole array
                break
        self.playlist_len -= 1

        # change song if removed == played, but stop if there is no next song
        if mustChangeSong:
            self.play(index) if index < count else self.stop()

    def clearMediaList(self):
        """
        Clears all existing items in media_list
        """
        logger.debug("Clearing media_list")
        self.stop()
        self._media_list.release()                              # delete old media list
        self._media_list = self.instance.media_list_new()       # create new and empty list
        self._media_player.set_media(None)

        self.id_playlist = []
        self.playlist_len = 0
        self.playlist_pointer = 0

    def getMrl(self):
        """
        Get the media resource locator (mrl) from a media descriptor object.
        @return: string with mrl of media descriptor object or None if no media
        @rtype: str or None
        """
        media = self.getMedia()
        mrl = media.get_mrl() if media else None
        media.release()

        return mrl

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
        self._media_list.lock()
        count = self._media_list.count()
        self._media_list.unlock()

        return count

    def playPause(self):
        if self._media_player.is_playing():
            self.pause()
        else:
            self.play()

    def play(self, item_playlist_id=None):
        """
        Plays the media in media_list (no effect if there is no media).
        @param item_playlist_id: id (index) of item in idPlaylist
        @type item_playlist_id: int
        """
        if item_playlist_id is not None:
            logger.debug("Play method called with index: %s" % item_playlist_id)
            self._media_player.stop()
            play_media = self._media_list.item_at_index(item_playlist_id)
            self._media_player.set_media(play_media)
            play_media.release()
            self._media_player.play()

            self.playlist_pointer = self.id_playlist.index(item_playlist_id)    # find item in playlist
        else:
            logger.debug("Play method called")
            self._media_player.play()

    def pause(self):
        """
        Pause media_player (no effect if there is no media).
        """
        logger.debug("Pause method called")
        self._media_player.pause()

    def stop(self):
        """
        Stop (no effect if there is no media)
        """
        logger.debug("Stop method called, stopping playback...")
        self._media_player.stop()

    def next(self, repeat=False):
        """
        Switches to next media in media_list if any.
        @param repeat: if set, current media is played again
        @type repeat: bool
        """
        if repeat:
            logger.debug("Next media method called, repeating current song")
            self._media_player.stop()
            self._media_player.play()

        else:
            logger.debug("Next media method called, switching to next song if any...")

            if self._media_player.is_playing():
                self._media_player.stop()

            if self.playlist_pointer + 1 < len(self.id_playlist):
                self.playlist_pointer += 1
                media = self._media_list.item_at_index(self.id_playlist[self.playlist_pointer])
                self._media_player.set_media(media)
                media.release()
                self._media_player.play()
            else:
                logger.debug("There is no next media (song) to play!")
                self._media_player.stop()

    def prev(self):
        """
        Switches to next media in media_list if any.
        Method returns False if there is no media to switch.
        @rtype : bool
        """
        logger.debug("Previous media method called")

        if self._media_player.is_playing():
            self._media_player.stop()

        if self.playlist_pointer - 1 >= 0:
            self.playlist_pointer -= 1
            media = self._media_list.item_at_index(self.id_playlist[self.playlist_pointer])
            self._media_player.set_media(media)
            media.release()
        else:
            logger.debug("There is no previous media (song) to play!")

        self._media_player.play()

    def setVolume(self, value):
        """
        Sets given volume value to player.
        Method returns False if unable to set the volume value.
        @param value: the volume in percents (0 = mute, 100 = 0dB).
        @type value: int
        @rtype: bool
        @raise ValueError: if value not in range [0, 100]
        """
        if not 0 <= value <= 100:
            raise ValueError("Volume must be in range <0, 100>")

        logger.debug("Setting volume to value %s", value)
        return self._media_player.audio_set_volume(int(value)) == -1

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
        Set movie position as percentage between 0 and 100. This has no effect if playback is not enabled.
        This might not work depending on the underlying input format and protocol.
        Method returns False if media is not seekable.
        @param new_pos: the position
        @type new_pos: float
        @rtype: bool
        @raise ValueError: if value not in range [0, 100]
        """
        if not 0 <= new_pos <= 100:
            raise ValueError("New position must be in range [0, 100]")

        new_pos = 99 if new_pos == 100 else new_pos

        logger.debug("Setting media to new position : %s", new_pos)
        return self._media_player.set_position(new_pos / 100.0)

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
        return length if length != -1 else None

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

    def setShuffle(self, state):
        current_id = self.id_playlist[self.playlist_pointer]

        if state:
            random.shuffle(self.id_playlist)
            self.id_playlist.remove(current_id)
            self.id_playlist.insert(0, current_id)
            self.shuffle_mode = True
            logger.debug("SHUFFLE playback mode turned ON")
        else:
            self.id_playlist = sorted(self.id_playlist)
            self.playlist_pointer = current_id                          # id_playlist is range-type (sorted) array
            self.shuffle_mode = False
            logger.debug("SHUFFLE playback mode turned OFF")

    def setRepeat(self, state):

        if state:
            self.repeat_mode = True
            logger.debug("REPEAT playback mode turned ON")
        else:
            self.repeat_mode = False
            logger.debug("REPEAT playback mode turned OFF")

    # ----
    # WARNING: CALLBACKS CALLED FROM ANOTHER THREAD !!!!  todo: fix
    # ----

    def __timeChangedCallback(self, event):
        self.timeChanged.emit(event.u.new_time)

    def __positionChangedCallback(self, event):
        newPos = event.u.new_position
        newPos = 0 if newPos > 1 else newPos
        self.positionChanged.emit(newPos)

    def __playingCallback(self, event):
        logger.debug("Media player is playing")
        self.is_playing = True
        self.is_paused = False
        self.is_stopped = False
        self.playing.emit()

    def __pausedCallback(self, event):
        logger.debug("Media player paused")
        self.is_playing = False
        self.is_paused = True
        self.is_stopped = False
        self.paused.emit()

    def __stoppedCallback(self, event):
        logger.debug("Media player is stopped")
        self.is_playing = False
        self.is_paused = False
        self.is_stopped = True
        self.stopped.emit()

    def __forwardCallback(self, event):
        logger.debug("Media player skipped forward")

    def __backwardCallback(self, event):
        logger.debug("Media player skipped backward")

    def __endReachedCallback(self, event):
        logger.debug("Media reached end")
        self.is_playing = False
        self.is_paused = False
        self.is_stopped = True

        self.endReached.emit(self.repeat_mode)          # if repeat_mode then do not switch to next song

    def __mediaChangedCallback(self, event):
        logger.debug("Media changed")
        currentMedia = self._media_player.get_media()
        index = self._media_list.index_of_item(currentMedia)
        currentMedia.release()
        self.mediaChanged.emit(index)

    def __errorCallback(self, event):
        logger.warning("Media encountered error")


class MediaParser(QObject):
    """
    Class for parsing media object.
    Runs in separated thread.
    Data are transfered via Signal/Slot mechanism.
    """

    finished = Signal()
    parsed = Signal(list)

    def __init__(self):
        super(MediaParser, self).__init__()
        self.vlcInstance = vlc.Instance()
        self._mutex = QMutex()
        self._cancel = False

        logger.debug("Media parser initialized.")

    def stop(self, value=None):
        """
        Return or set stopped flag, which cancel parsing.
        Thread safe method!
        @type value: bool or None
        @rtype: bool
        """
        self._mutex.lock()
        if value is not None:
            self._cancel = value
        self._mutex.unlock()

        return self._cancel

    @Slot(list)
    def parseMedia(self, sources):
        """
        Parses media files. Result is send to media player in separated thread.
        Thread worker!
        @type sources: list of unicode
        """
        # END FLAG RECEIVED
        if not sources:
            logger.debug("Parser finished, end flag received.")
            self.stop(False)            # reset stop flag

            self.finished.emit()

        # PARSE MEDIA FILES
        elif not self.stop():
            mediaList = []
            for unicode_path in sources:
                byte_path = unicode_path.encode("utf8")
                mMedia = self.vlcInstance.media_new(byte_path)
                mMedia.parse()
                mediaList.append((unicode_path, mMedia))

            self.parsed.emit(mediaList)


# ------------------------------------------------------------------------------------------------------------
# MediaPLayer

    # def setSource(self, source_path):
    #     """
    #     Sets the media source that will be played by the media_player.
    #     @param source_path: path to media file
    #     @type source_path: str or unicode
    #     """
    #     unicode_path, byte_path = unicode2bytes(source_path)            # vlc needs byte array (ascii str)
    #
    #     # if path exists
    #     if not os.path.isfile(unicode_path):
    #         self.error.emit("Given media file '%s' does not exist!" % source_path)
    #         return
    #
    #     # stops playback and clears media_list
    #     logger.debug("Deleting items from media list")
    #     self.clearMediaList()
    #
    #     # put the media to media list
    #     self._media_list.lock()
    #     self._media_list.add_media(self.instance.media_new(byte_path))
    #     # todo: check ref counter
    #     self._media_player.set_media(self._media_list.item_at_index(0))
    #     self._media_list.unlock()
    #
    #     self.id_playlist.append(0)        # new media has id #0 (it is first in the list)
    #     self.playlist_len = 1
    #     self.playlist_pointer = 0
    #
    #     logger.debug("New media source set to: %s", source_path)
    #
    # def addSource(self, source_path):
    #     """
    #     Adds one new media path to media list (queue).
    #     If player has no media set, method automatically sets added media as current.
    #     @type source_path: str or unicode
    #     """
    #     unicode_path, byte_path = unicode2bytes(source_path)            # vlc needs byte array (ascii str)
    #
    #     # if path exists
    #     if not os.path.isfile(unicode_path):
    #         self.error.emit("Given media file '%s' does not exist!" % source_path)
    #         return
    #
    #     logger.debug("Adding new media source: %s", source_path)
    #     # todo: check ref counter
    #     media = self.instance.media_new(byte_path)
    #     self._media_list.lock()
    #     self._media_list.add_media(media)
    #     self._media_list.unlock()
    #
    #     if not bool(self.getMedia()):
    #         logger.debug("Player has no media set, setting current media %s", source_path)
    #         self._media_player.set_media(media)
    #
    #     self.id_playlist.append(self.playlist_len)        # new media is on the end of the list
    #     self.playlist_len += 1
    #
    # def addSources(self, sources):
    #     """
    #     Appends list of new media paths to media list (queue).
    #     If player has no media set, method automatically sets first media path from list as current.
    #     @type sources: list of str or list of unicode
    #     """
    #     logger.debug("Adding new media sources.")
    #     try:
    #         self._media_list.lock()
    #         for single_path in sources:
    #             unicode_path, byte_path = unicode2bytes(single_path)            # vlc needs byte array (ascii str)
    #
    #             # if path exists
    #             if not os.path.isfile(unicode_path):
    #                 self.error.emit("Given media file '%s' does not exist!" % single_path)
    #                 return
    #
    #             media = self.instance.media_new(byte_path)
    #             self._media_list.add_media(media)
    #
    #             self.id_playlist.append(self.playlist_len)        # new media is on the end of the list
    #             self.playlist_len += 1
    #     finally:
    #         self._media_list.unlock()
    #
    #     # todo: check for ref counter !!!
    #     if not bool(self.getMedia()):
    #         logger.debug("Player has no media set, setting first media from list %s", sources[0])
    #         self._media_player.set_media(self._media_list.item_at_index(0))