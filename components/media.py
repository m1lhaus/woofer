# -*- coding: utf-8 -*-

"""
Media components
- Media player
- Radio player
"""

import os
import logging
import random

from PyQt4.QtCore import *

from components import libvlc
import tools


logger = logging.getLogger(__name__)


class MediaPlayer(QObject):
    """
    Media player class.
    Uses LibVLC highlevel wrapper.
    """

    errorSignal = pyqtSignal(int, unicode, unicode)        # (Message.CRITICAL, main_text, description)
    tickTocSignal = pyqtSignal(int)

    mediaAddedSignal = pyqtSignal(list, bool)
    playingSignal = pyqtSignal()
    stoppedSignal = pyqtSignal()
    pausedSignal = pyqtSignal()
    timeChangedSignal = pyqtSignal(int)
    positionChangedSignal = pyqtSignal(float)
    mediaChangedSignal = pyqtSignal(int)          # TODO: add metadata
    endReachedSignal = pyqtSignal(bool)

    # this signals are used as helper, because callback are called from vlc directly (from another thread),
    # so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
    mediaChangedCallbackSignal = pyqtSignal()
    endReachedCallbackSignal = pyqtSignal()
    errorCallbackSignal = pyqtSignal()

    def __init__(self):
        super(MediaPlayer, self).__init__()
        self.instance = libvlc.Instance()
        """@type: libvlc.Instance"""
        self._media_player = self.instance.media_player_new()
        """@type: libvlc.MediaPlayer"""
        self._media_list = self.instance.media_list_new()
        """@type: libvlc.MediaList"""
        logger.debug(u"Core instances of VLC player created")

        self.tick_rate = 1000                           # in ms
        self.media_list = []                            # path to media file is stored in _media_list but is
                                                        # vlc translates the path to its form
        self.shuffled_playlist = []                     # items are represented by its index in _media_list
        self.shuffled_playlist_current_index = 0        # points which media in shuffled_playlist is being played

        self.is_playing = False
        self.is_paused = False
        self.is_stopped = True
        self.append_media = True        # append to playlist or clear playlist
        self.appending_mode = True      # flag that says if newly added media has been appended
        self.shuffle_mode = False
        self.repeat_mode = False
        self.player_is_empty = True

        self.endReachedSignal.connect(self.next)
        self.playingSignal.connect(self._playingSlot)
        self.pausedSignal.connect(self._pausedSlot)
        self.stoppedSignal.connect(self._stoppedSlot)
        self.endReachedSignal.connect(self._stoppedSlot)
        self.mediaChangedCallbackSignal.connect(self._mediaChangedSlot)
        self.endReachedCallbackSignal.connect(self._endReachedSlot)
        self.errorCallbackSignal.connect(self._errorSlot)

        self._setupEvents()

        logger.debug(u"Created Woofer player instance")

    def _setupEvents(self):
        self._event_manager = self._media_player.event_manager()
        # self._event_manager.event_attach(libvlc.EventType.MediaPlayerOpening, self.playerStateChanged)
        # self._event_manager.event_attach(libvlc.EventType.MediaPlayerBuffering, self.playerStateChanged)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerPlaying, self.__playingCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerPaused, self.__pausedCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerStopped, self.__stoppedCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerForward, self.__forwardCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerBackward, self.__backwardCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerEndReached, self.__endReachedCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerEncounteredError, self.__errorCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerTimeChanged, self.__timeChangedCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerPositionChanged, self.__positionChangedCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerMediaChanged, self.__mediaChangedCallback)

    @pyqtSlot(list)
    def addMedia(self, mlist, restoring_session=False):
        """
        Adds list of media objects to player media_list.
        Usually called as slot from parser thread, but could be called manually
        when last session is restored on application start.
        @param restoring_session: flag when method is called manually to restore playlist from saved session
        @param mlist: list of (unicode_path, media_object) or list of (unicode_path)
        @type mlist: list of (unicode, libvlc.Media) or list of (unicode)
        """
        # when restoring session, no parsed media files are available, but vlc takes both vlc.Media and mrl
        if restoring_session:
            logger.debug(u"Restoring session, adding media paths to _media_list...")

            self._media_list.lock()
            for path in mlist:
                unicode_path, byte_path = tools.unicode2bytes(path)       # fix Windows encoding issues
                # vlc will parse media automatically if needed (before playing)
                self._media_list.add_media(byte_path)
                self.media_list.append(os.path.normpath(path))
                # normpath to preserve win/unix compatibility when restoring session

            # set previous current media now as current
            media = self._media_list.item_at_index(self.shuffled_playlist[self.shuffled_playlist_current_index])
            self._media_list.unlock()

            self._media_player.set_media(media)
            self.player_is_empty = False
            media.release()
            logger.debug(u"All media paths restored.")

        else:
            export = []

            self._media_list.lock()
            for path, media in mlist:
                self._media_list.add_media(media)
                media.release()
                self.media_list.append(path)
                self.shuffled_playlist.append(len(self.shuffled_playlist))        # new media is on the end of the list
                export.append((path, media.get_duration()))
            self._media_list.unlock()

            self.mediaAddedSignal.emit(export, self.append_media)

            # set set_mode, set media and switch to append mode for next iteration
            if not self.append_media or self.player_is_empty:
                path, media = mlist[0]
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
        logger.debug(u"Removing media item on index: %s", remove_index)

        must_change_song = False
        restore_playing = self.is_playing
        current_index = self.shuffled_playlist[self.shuffled_playlist_current_index]

        # remove media from player if media is currently being played
        if remove_index == current_index:
            must_change_song = True
            self._media_player.stop()
            self._media_player.set_media(None)
            self.player_is_empty = True

        # remove media from _media_list
        self._media_list.lock()
        remove_error = self._media_list.remove_index(remove_index) == -1
        self._media_list.unlock()
        del self.media_list[remove_index]

        if remove_error:
            logger.error(u"Unable to remove item from _media_list. "
                         u"Item is not in the list or _media_list is read only! "
                         u"Playlist len: %s, index: %s" % (len(self.shuffled_playlist), remove_index))
            self.errorSignal.emit(tools.ErrorMessages.CRITICAL,
                                  u"Unable remove item from Woofer media list. "
                                  u"Item is not in the list or the list is read only!",
                                  u"playlist len: %s, removed index: %s" % (len(self.shuffled_playlist), remove_index))

        self._media_list.lock()
        new_playlist_len = self._media_list.count()
        self._media_list.unlock()

        # decrease all references with higher index
        for i in xrange(len(self.shuffled_playlist)):
            index = self.shuffled_playlist[i]
            if index > remove_index:
                self.shuffled_playlist[i] -= 1
            elif index == remove_index:
                rem_idx_in_shuffled_playlist = i
        # remove media reference from shuffled_playlist
        del self.shuffled_playlist[rem_idx_in_shuffled_playlist]

        # change song if removed == played, but stop if there is no next song
        if must_change_song:
            logger.debug(u"Currently playing media has been removed from playlist, selecting next one.")
            self.play(item_playlist_id=self.shuffled_playlist[self.shuffled_playlist_current_index])
            if not restore_playing:
                self.stop()

        elif rem_idx_in_shuffled_playlist < self.shuffled_playlist_current_index:
            self.shuffled_playlist_current_index -= 1

    def clearMediaList(self):
        """
        Clears all existing items in media_list
        """
        logger.debug(u"Clearing _media_list")
        self.stop()
        self._media_list.release()                              # delete old media list
        self._media_list = self.instance.media_list_new()       # create new and empty list
        self._media_player.set_media(None)
        self.media_list = []
        self.player_is_empty = True

        self.shuffled_playlist = []
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
        WARNING: Media reference counter will +1 => media should be released after usage!
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
        # play given media (index) - find item in playlist
        if item_playlist_id is not None:
            logger.debug(u"Play method called with index: %s" % item_playlist_id)
            self._media_player.stop()
            play_media = self._media_list.item_at_index(item_playlist_id)
            self._media_player.set_media(play_media)
            self.player_is_empty = False
            play_media.release()
            self.shuffled_playlist_current_index = self.shuffled_playlist.index(item_playlist_id)
        else:
            logger.debug(u"Play method called")

        if self._media_player.play() == -1:
            current_media_path = self.media_list[self.shuffled_playlist[self.shuffled_playlist_current_index]]
            self.errorSignal.emit(tools.ErrorMessages.ERROR, u"Error occurred when trying to play media file",
                                  u"Media: %s" % current_media_path)

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

        logger.debug(u"Volume set: %s", value)
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
        """
        Get current mute status.
        @return: the mute status (boolean) if defined, -1 if undefined/unapplicable.
        """
        return self._media_player.audio_get_mute()

    def setTime(self, new_time):
        """
        Set the playback time (in ms). This has no effect if no media is being played.
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
            logger.debug(u"Playback time set: %s", new_time)
        else:
            raise ValueError(u"New time must be in range [0, %d]" % total_time)

        return True

    def setPosition(self, new_pos):
        """
        Set playback position as percentage between 0 and 100. This has no effect if playback is not enabled.
        This might not work depending on the underlying input format and protocol.
        Method returns False if media is not seekable.
        @param new_pos: the position
        @type new_pos: float
        @rtype: bool
        @raise ValueError: if value not in range [0, 100]
        """
        logger.debug(u"Playback position set: %s", new_pos)
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
        if not self.shuffled_playlist:      # playlist is empty
            return

        current_id = self.shuffled_playlist[self.shuffled_playlist_current_index]
        if state:
            random.shuffle(self.shuffled_playlist)
            self.shuffled_playlist.remove(current_id)
            self.shuffled_playlist.insert(0, current_id)
        else:
            self.shuffled_playlist = sorted(self.shuffled_playlist)
            self.shuffled_playlist_current_index = current_id         # id_playlist is range-type (sorted) array

        logger.debug(u"SHUFFLE mode: %s", state)

    def setRepeat(self, state):
        """
        Enable/disable repeat mode
        @type state: bool
        """
        self.repeat_mode = state
        logger.debug(u"REPEAT mode: %s", state)

    def initMediaAdding(self, append=True):
        """
        Called before media adding is started from scanner/parser thread.
        @param append: append mode flag
        @type append: bool
        """
        logger.debug(u"Initializing media adding...")
        self.appending_mode = append
        self.append_media = append

    @pyqtSlot()
    def mediaAddingFinished(self):
        """
        Called when media adding ends.
        If shuffle_mode set, newly added media are shuffled with unplayed media.
        """
        logger.debug(u"Media adding finished.")
        if self.shuffle_mode:
            logger.debug(u"Shuffling newly added media...")
            # shuffle newly added media with the rest, which have not been played yet
            if self.appending_mode:
                index = self.shuffled_playlist_current_index+1      # shuffle all from currently played
                tmp_list = self.shuffled_playlist[index:]
                random.shuffle(tmp_list)
                self.shuffled_playlist[index:] = tmp_list
            else:
                self.setShuffle(True)       # implicit shuffle

    # ------------------------- CALLBACKS ------------------------------------------

    @pyqtSlot()
    def _playingSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        self.is_playing = True
        self.is_paused = False
        self.is_stopped = False

    @pyqtSlot()
    def _pausedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        self.is_playing = False
        self.is_paused = True
        self.is_stopped = False

    @pyqtSlot()
    def _stoppedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        Called when stopped and end-reached
        """
        self.is_playing = False
        self.is_paused = False
        self.is_stopped = True

    @pyqtSlot()
    def _mediaChangedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        currentMedia = self._media_player.get_media()
        self._media_list.lock()
        index = self._media_list.index_of_item(currentMedia)
        self._media_list.unlock()
        currentMedia.release()

        self.mediaChangedSignal.emit(index)

    @pyqtSlot()
    def _endReachedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        self.endReachedSignal.emit(self.repeat_mode)          # if repeat_mode then do not switch to next song

    @pyqtSlot()
    def _errorSlot(self):
        logger.warning(u"Media encountered error")
        current_media_path = self.media_list[self.shuffled_playlist[self.shuffled_playlist_current_index]]
        self.errorSignal.emit(tools.ErrorMessages.ERROR, u"Error occurred when trying to play media file",
                              u"Playing %s failed!" % current_media_path)

    # WARNING: CALLBACKS CALLED DIRECTLY FROM ANOTHER THREAD (VLC THREAD) !!!!

    def __timeChangedCallback(self, event):
        try:
            new_time = event.u.new_time
        except RuntimeError:
            logger.warning(u"Media player callback called, but C++ object does not exist. "
                           u"If program is being closed, this is a possible behaviour.")
        else:
            self.timeChangedSignal.emit(new_time)

    def __positionChangedCallback(self, event):
        try:
            newPos = event.u.new_position
        except RuntimeError:
            logger.warning(u"Media player callback called, but C++ object does not exist. "
                           u"If program is being closed, this is a possible behaviour.")
        else:
            newPos = 0 if newPos > 1 else newPos
            self.positionChangedSignal.emit(newPos)

    def __playingCallback(self, event):
        logger.debug(u"Player playing callback")
        self.playingSignal.emit()

    def __pausedCallback(self, event):
        logger.debug(u"Player paused callback")
        self.pausedSignal.emit()

    def __stoppedCallback(self, event):
        logger.debug(u"Player stopped callback")
        self.stoppedSignal.emit()

    def __forwardCallback(self, event):
        logger.debug(u"Player next track callback")

    def __backwardCallback(self, event):
        logger.debug(u"Player prev track callback")

    def __endReachedCallback(self, event):
        logger.debug(u"Player media end reached callback")
        self.endReachedCallbackSignal.emit()

    def __mediaChangedCallback(self, event):
        logger.debug(u"Player media changed callback")
        self.mediaChangedCallbackSignal.emit()

    def __errorCallback(self, event):
        self.errorCallbackSignal.emit()


class MediaParser(QObject):
    """
    Class for parsing media object.
    Runs in separated thread.
    Data are transferred via Signal/Slot mechanism.
    Worker method: MediaParser.parseMedia()
    """

    finishedSignal = pyqtSignal()
    dataParsedSignal = pyqtSignal(list)

    def __init__(self):
        super(MediaParser, self).__init__()
        self.vlc_instance = libvlc.Instance()        # for parsing
        self.stop = False

        logger.debug(u"Media Parser initialized.")

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
            self.stop = False           # reset stop flag
            self.finishedSignal.emit()

        # PARSE MEDIA FILES
        elif not self.stop:
            media_list = []
            for unicode_path in sources:
                byte_path = unicode_path.encode("utf8")
                media_object = self.vlc_instance.media_new(byte_path)
                media_object.parse()
                media_list.append((unicode_path, media_object))

            self.dataParsedSignal.emit(media_list)