# -*- coding: utf-8 -*-

"""
Media components
- Media player
- Radio player
"""

__version__ = "$Id: media.py 131 2014-10-22 17:07:22Z m1lhaus $"

import logging
import random

from PyQt4.QtCore import *

from components import libvlc
import tools


logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)


class MediaPlayer(QObject):
    """
    Media player class
    """

    TICK_INTERVAL = 1000        # in ms

    # error = pyqtSignal(str)
    errorEncountered = pyqtSignal(int, unicode, unicode)        # (Message.CRITICAL, main_text, description)
    tick = pyqtSignal(int)

    mediaAdded = pyqtSignal(list, bool)
    playing = pyqtSignal()
    stopped = pyqtSignal()
    paused = pyqtSignal()
    timeChanged = pyqtSignal(int)
    positionChanged = pyqtSignal(float)
    mediaChanged = pyqtSignal(int)          # TODO: add metadata
    endReached = pyqtSignal(bool)

    # this signals are used as helper, because callback are called from vlc directly (from another thread),
    # so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
    mediaChangedCallbackSignal = pyqtSignal()
    endReachedCallbackSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(MediaPlayer, self).__init__(parent)

        self.instance = libvlc.Instance()
        """@type: vlc.Instance"""
        self._media_player = self.instance.media_player_new()
        """@type: vlc.MediaPlayer"""
        self._media_list = self.instance.media_list_new()
        """@type: vlc.MediaList"""
        logger.debug(u"Core instances of VLC player created")

        self.shuffled_playlist = []
        self.shuffled_playlist_current_index = 0        # points which media in idPlaylist is being played
        # self.playlist_len = 0

        self.is_playing = False
        self.is_paused = False
        self.is_stopped = True
        self.append_media = True        # append to playlist or clear playlist
        self.appending_mode = True      # flag that says if newly added media has been appended
        self.shuffle_mode = False
        self.repeat_mode = False
        self.player_is_empty = True

        self.endReached.connect(self.next)
        self.playing.connect(self.__playingSlot)
        self.paused.connect(self.__pausedSlot)
        self.stopped.connect(self.__stoppedSlot)
        self.endReached.connect(self.__stoppedSlot)
        self.mediaChangedCallbackSignal.connect(self.__mediaChangedSlot)
        self.endReachedCallbackSignal.connect(self.__endReachedSlot)

        self.__setupEvents()

        logger.debug(u"Created Woofer player instance")

    def __setupEvents(self):
        self.media_player_event_manager = self._media_player.event_manager()
        # self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerOpening,
        #                                              self.playerStateChanged)
        # self.media_player_event_manager.event_attach(vlc.EventType.MediaPlayerBuffering,
        #                                              self.playerStateChanged)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerPlaying,
                                                     self.__playingCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerPaused,
                                                     self.__pausedCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerStopped,
                                                     self.__stoppedCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerForward,
                                                     self.__forwardCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerBackward,
                                                     self.__backwardCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerEndReached,
                                                     self.__endReachedCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerEncounteredError,
                                                     self.__errorCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerTimeChanged,
                                                     self.__timeChangedCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerPositionChanged,
                                                     self.__positionChangedCallback)
        self.media_player_event_manager.event_attach(libvlc.EventType.MediaPlayerMediaChanged,
                                                     self.__mediaChangedCallback)

    @pyqtSlot(list)
    def addMedia(self, mList, restoring_session=False):
        """
        Adds list of media objects to player media_list.
        Usually called as slot from parser thread, but could be called manually
        when last session is restored on application start.
        @param restoring_session: flag when method is called manually to restore playlist from saved session
        @param mList: list of (unicode_path, media_object) or list of (unicode_path)
        @type mList: list of (unicode, libvlc.Media) or list of (unicode)
        """

        # when restoring session, no parsed media files are available, but vlc takes both vlc.Media and mrl
        if restoring_session:
            logger.debug(u"Adding media paths to media_list...")

            self._media_list.lock()
            for path in mList:
                unicode_path, byte_path = tools.unicode2bytes(path)       # fix Windows encoding issues
                # vlc will parse media automatically if needed (before playing)
                self._media_list.add_media(byte_path)

            # set previous current media now as current
            media = self._media_list.item_at_index(self.shuffled_playlist[self.shuffled_playlist_current_index])
            self._media_list.unlock()

            self._media_player.set_media(media)
            self.player_is_empty = False
            media.release()
            logger.debug(u"Media added successfully")

        else:
            export = []

            self._media_list.lock()
            for path, media in mList:
                self._media_list.add_media(media)
                media.release()

                self.shuffled_playlist.append(len(self.shuffled_playlist))        # new media is on the end of the list
                # self.playlist_len += 1
                export.append((path, media.get_duration()))
            self._media_list.unlock()

            self.mediaAdded.emit(export, self.append_media)

            # set set_mode, set media and switch to append mode for next iteration
            if not self.append_media or self.player_is_empty:
                path, media = mList[0]
                logger.debug(u"Setting current media %s", path)
                self._media_player.set_media(media)
                self.player_is_empty = False
                self.append_media = True
                self.play()         # in set_mode, Play or Play All has been chosen => play()

    def removeItem(self, remove_index):
        """
        Removes item from media list by index.
        If media is currently being played, next media is played.
        If there is no next media, playing is stopped.
        @param remove_index: index of removed item in media_list
        @type remove_index: int
        """
        logger.debug(u"Removing media item in index: %s", remove_index)

        mustChangeSong = False
        restore_playing = self.is_playing
        current_index = self.shuffled_playlist[self.shuffled_playlist_current_index]

        # remove media from player if media is currently being played
        if remove_index == current_index:
            mustChangeSong = True
            self._media_player.stop()
            self._media_player.set_media(None)
            self.player_is_empty = True

        # remove media from _media_list
        self._media_list.lock()
        remove_error = self._media_list.remove_index(remove_index) == -1
        self._media_list.unlock()

        if remove_error:
            logger.error(u"Unable to remove item from _media_list. "
                         u"Item is not in the list or _media_list is read only! "
                         u"Playlist len: %s, index: %s" % (len(self.shuffled_playlist), remove_index))
            self.errorEncountered.emit(tools.ErrorMessages.CRITICAL,
                                       u"Unable remove item from _media_list. "
                                       u"Item is not in the list or _media_list is read only!",
                                       u"playlist len: %s, removed index: %s" % (len(self.shuffled_playlist), remove_index))

        self._media_list.lock()
        new_playlist_len = self._media_list.count()
        self._media_list.unlock()

        # remove media reference from shuffled_playlist[]
        for i in xrange(len(self.shuffled_playlist)):
            if self.shuffled_playlist[i] == remove_index:
                del self.shuffled_playlist[i]
                # faster way than iterate over whole array
                self.shuffled_playlist[i:] = [x-1 for x in self.shuffled_playlist[i:]]
                break
        # self.playlist_len -= 1

        # change song if removed == played, but stop if there is no next song
        if mustChangeSong:
            if remove_index < new_playlist_len:
                logger.debug(u"Currently playlist media has been removed from playlist, selecting next one.")
                if restore_playing:
                    self.play(item_playlist_id=remove_index)
                else:
                    self.next(playlist_index=remove_index)
            else:
                self.shuffled_playlist_current_index = 0
                logger.debug(u"Last item from playlist has been removed. Playing remains stopped.")

    def clearMediaList(self):
        """
        Clears all existing items in media_list
        """
        logger.debug(u"Clearing _media_list")
        self.stop()
        self._media_list.release()                              # delete old media list
        self._media_list = self.instance.media_list_new()       # create new and empty list
        self._media_player.set_media(None)
        self.player_is_empty = True

        self.shuffled_playlist = []
        # self.playlist_len = 0
        self.shuffled_playlist_current_index = 0

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
        Media reference counter will +1 => media should be released after usage!
        @return: the media associated with p_mi, or None if no media is associated.
        @rtype: libvlc.Media or None
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

    @pyqtSlot()
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
            logger.debug(u"Play method called with index: %s" % item_playlist_id)
            self._media_player.stop()
            play_media = self._media_list.item_at_index(item_playlist_id)
            self._media_player.set_media(play_media)
            self.player_is_empty = False
            play_media.release()
            self.shuffled_playlist_current_index = self.shuffled_playlist.index(item_playlist_id)    # find item in playlist
        else:
            logger.debug(u"Play method called")

        self._media_player.play()

    @pyqtSlot()
    def pause(self):
        """
        Pause media_player (no effect if there is no media).
        """
        logger.debug(u"Pause method called")
        self._media_player.pause()

    @pyqtSlot()
    def stop(self):
        """
        Stop (no effect if there is no media)
        """
        logger.debug(u"Stop method called, stopping playback...")
        self._media_player.stop()

    @pyqtSlot(bool)
    def next(self, repeat=False, playlist_index=None):
        """
        Switches to next media in media_list if any.
        @param repeat: if set, current media is played again
        @type repeat: bool
        """
        if playlist_index is not None:
            logger.debug(u"Setting next media to play by playlist_id: %s" % playlist_index)
            self._media_player.stop()
            play_media = self._media_list.item_at_index(playlist_index)
            self._media_player.set_media(play_media)
            self.player_is_empty = False
            play_media.release()
            self.shuffled_playlist_current_index = self.shuffled_playlist.index(playlist_index)  # find item in playlist

        elif repeat:
            logger.debug(u"Next media method called, repeating current song")
            self._media_player.stop()
            self._media_player.play()

        else:
            logger.debug(u"Next media method called, switching to next song if any...")

            if self._media_player.is_playing():
                self._media_player.stop()

            if self.shuffled_playlist_current_index + 1 < len(self.shuffled_playlist):
                self.shuffled_playlist_current_index += 1
                media = self._media_list.item_at_index(self.shuffled_playlist[self.shuffled_playlist_current_index])
                self._media_player.set_media(media)
                self.player_is_empty = False
                media.release()
                self._media_player.play()
            else:
                logger.debug(u"There is no next media (song) to play!")
                self._media_player.stop()

    @pyqtSlot()
    def prev(self):
        """
        Switches to next media in media_list if any.
        Method returns False if there is no media to switch.
        @rtype : bool
        """
        logger.debug(u"Previous media method called")

        if self._media_player.is_playing():
            self._media_player.stop()

        if self.shuffled_playlist_current_index - 1 >= 0:
            self.shuffled_playlist_current_index -= 1
            media = self._media_list.item_at_index(self.shuffled_playlist[self.shuffled_playlist_current_index])
            self._media_player.set_media(media)
            self.player_is_empty = False
            media.release()
        else:
            logger.debug(u"There is no previous media (song) to play!")

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
            raise ValueError(u"Volume must be in range <0, 100>")

        logger.debug(u"Setting volume to value %s", value)
        self._media_player.audio_set_volume(int(value))

    def getVolume(self):
        """
        Get current software audio volume in range [0, 100].
        @return: the software volume in percents (0 = mute, 100 = nominal / 0dB).
        @rtype: int
        """
        return self._media_player.audio_get_volume()

    def setMute(self, status):
        logger.debug(u"Setting audio MUTE to %s", status)
        self._media_player.audio_set_mute(status)

    def isMuted(self):
        return self._media_player.audio_get_mute()

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
            logger.error(u"Media is not seekable")
            return False

        total_time = self.totalTime()
        if 0 <= new_time <= total_time:
            self._media_player.set_time(int(new_time))
            logger.debug(u"Media play set to new time: %s ms", new_time)
        else:
            raise ValueError(u"New time must be in range [0, %d]" % total_time)

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
            raise ValueError(u"New position must be in range [0, 100]")

        new_pos = 99 if new_pos == 100 else new_pos

        logger.debug(u"Setting media to new position : %s", new_pos)
        return self._media_player.set_position(new_pos / 100.0)

    def currentTime(self):
        """
        Get the current time (in ms).
        Method returns None if no media set.
        @rtype : int or None
        """
        ctime = self._media_player.get_time()

        if ctime == -1:
            logger.warning(u"There is no media set to get current time")
            ctime = None

        return ctime

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
            logger.warning(u"There is no media set to get remaining time")
            remaining_time = None
        else:
            remaining_time = total_time - current_time

        return remaining_time

    def setShuffle(self, state):
        """
        Enable/disable shuffle mode
        @param state: enable/disable
        @type state: bool
        """
        self.shuffle_mode = state

        # playlist is not empty
        if self.shuffled_playlist:
            current_id = self.shuffled_playlist[self.shuffled_playlist_current_index]

            if state:
                random.shuffle(self.shuffled_playlist)
                self.shuffled_playlist.remove(current_id)
                self.shuffled_playlist.insert(0, current_id)
                logger.debug(u"SHUFFLE playback mode turned ON")
            else:
                self.shuffled_playlist = sorted(self.shuffled_playlist)
                self.shuffled_playlist_current_index = current_id                          # id_playlist is range-type (sorted) array
                logger.debug(u"SHUFFLE playback mode turned OFF")

    def setRepeat(self, state):
        """
        Enable/disable repeat mode
        @type state: bool
        """
        self.repeat_mode = state

        if state:
            logger.debug(u"REPEAT playback mode turned ON")
        else:
            logger.debug(u"REPEAT playback mode turned OFF")

    def initMediaAdding(self, append=True):
        """
        Called before media adding is started from scanner/parser thread.
        @param append: append mode flag
        @type append: bool
        """
        self.appending_mode = append
        self.append_media = append

    @pyqtSlot()
    def mediaAddingFinished(self):
        """
        Called when media adding ends.
        If shuffle_mode set, newly added media are shuffled with unplayed media.
        """

        # shuffle newly added media with the rest, which have not been played yet
        if self.appending_mode and self.shuffle_mode:
            logger.debug(u"Shuffling newly added media")
            index = self.shuffled_playlist_current_index+1
            tmp_list = self.shuffled_playlist[index:]
            random.shuffle(tmp_list)
            self.shuffled_playlist[index:] = tmp_list

        elif not self.appending_mode and self.shuffle_mode:
            logger.debug(u"Newly added media which has not been appended are not shuffled. Shuffling...")
            self.setShuffle(True)

    @pyqtSlot()
    def __playingSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        self.is_playing = True
        self.is_paused = False
        self.is_stopped = False

    @pyqtSlot()
    def __pausedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        self.is_playing = False
        self.is_paused = True
        self.is_stopped = False

    @pyqtSlot()
    def __stoppedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        Called when stopped and end-reached
        """
        self.is_playing = False
        self.is_paused = False
        self.is_stopped = True

    @pyqtSlot()
    def __mediaChangedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        currentMedia = self._media_player.get_media()
        self._media_list.lock()
        index = self._media_list.index_of_item(currentMedia)
        self._media_list.unlock()
        currentMedia.release()

        self.mediaChanged.emit(index)

    @pyqtSlot()
    def __endReachedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        self.endReached.emit(self.repeat_mode)          # if repeat_mode then do not switch to next song

    # ------------------------------------------------------------------------
    # WARNING: CALLBACKS CALLED DIRECTLY FROM ANOTHER THREAD (VLC THREAD) !!!!
    # ------------------------------------------------------------------------

    def __timeChangedCallback(self, event):
        try:
            new_time = event.u.new_time
        except RuntimeError:
            logger.warning("Media player callback called, but C++ object does not exist. "
                           "If program is being closed, this is a possible behaviour.")
        else:
            self.timeChanged.emit(new_time)

    def __positionChangedCallback(self, event):
        try:
            newPos = event.u.new_position
        except RuntimeError:
            logger.warning("Media player callback called, but C++ object does not exist. "
                           "If program is being closed, this is a possible behaviour.")
        else:
            newPos = 0 if newPos > 1 else newPos
            self.positionChanged.emit(newPos)

    def __playingCallback(self, event):
        logger.debug(u"Media player is playing")
        self.playing.emit()

    def __pausedCallback(self, event):
        logger.debug(u"Media player paused")
        self.paused.emit()

    def __stoppedCallback(self, event):
        logger.debug(u"Media player is stopped")
        self.stopped.emit()

    def __forwardCallback(self, event):
        logger.debug(u"Media player skipped forward")

    def __backwardCallback(self, event):
        logger.debug(u"Media player skipped backward")

    def __endReachedCallback(self, event):
        logger.debug(u"Media reached end")
        self.endReachedCallbackSignal.emit()

    def __mediaChangedCallback(self, event):
        logger.debug(u"Media changed")
        self.mediaChangedCallbackSignal.emit()

    def __errorCallback(self, event):
        logger.warning(u"Media encountered error")


class MediaParser(QObject):
    """
    Class for parsing media object.
    Runs in separated thread.
    Data are transfered via Signal/Slot mechanism.
    """

    finished = pyqtSignal()
    parsed = pyqtSignal(list)

    def __init__(self):
        super(MediaParser, self).__init__()
        self.vlcInstance = libvlc.Instance()
        self._mutex = QMutex()
        self._cancel = False

        logger.debug(u"Media Parser initialized.")

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

    @pyqtSlot(list)
    def parseMedia(self, sources):
        """
        Parses media files. Result is send to media player in separated thread.
        Thread worker!
        @type sources: list of unicode
        """
        # END FLAG RECEIVED
        if not sources:
            logger.debug(u"Parser finished, end flag received.")
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