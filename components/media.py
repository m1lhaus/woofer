# -*- coding: utf-8 -*-
#
# Woofer - free open-source cross-platform music player
# Copyright (C) 2015 Milan Herbig <milanherbig[at]gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

"""
Media components
- Media player
- Radio player
"""

import os
import logging
import random

from PyQt5.QtCore import *

from components import libvlc
import tools


logger = logging.getLogger(__name__)


class MediaPlayer(QObject):
    """
    Media player class.
    Uses LibVLC highlevel wrapper.
    """

    errorSignal = pyqtSignal(int, str, str)        # (Message.CRITICAL, main_text, description)
    tickTocSignal = pyqtSignal(int)

    mediaAddedSignal = pyqtSignal(list, bool)
    playingSignal = pyqtSignal()
    stoppedSignal = pyqtSignal()
    pausedSignal = pyqtSignal()
    timeChangedSignal = pyqtSignal(int)
    positionChangedSignal = pyqtSignal(float)
    mediaChangedSignal = pyqtSignal(int, int)
    endReachedSignal = pyqtSignal(bool)

    # this signals are used as helper, because callback are called from vlc directly (from another thread),
    # so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
    mediaChangedCallbackSignal = pyqtSignal()
    endReachedCallbackSignal = pyqtSignal()
    errorCallbackSignal = pyqtSignal()

    def __init__(self):
        super(MediaPlayer, self).__init__()
        self._instance = libvlc.Instance()
        """@type: libvlc.Instance"""
        self._media_player = self._instance.media_player_new()
        """@type: libvlc.MediaPlayer"""
        self._media_list = self._instance.media_list_new()
        """@type: libvlc.MediaList"""
        self._event_manager = self._media_player.event_manager()
        """@type: libvlc.EventManager"""
        logger.debug("Core instances of VLC player created")

        self.tick_rate = 1000                           # in ms
        self.media_list = []                            # path to media file is stored in _media_list but is
                                                        # vlc translates the path to its form
        self.shuffled_playlist = []                     # items are represented by its index in _media_list
        self.shuffled_playlist_current_index = 0        # points which media in shuffled_playlist is being played
        self.shuffled_playlist_old_index = 0            # points which media in shuffled_playlist was previously played

        self.is_playing = False
        self.is_paused = False
        self.is_stopped = True
        self.append_media = True        # append to playlist or clear playlist
        self.appending_mode = True      # flag that says if newly added media has been appended
        self.shuffle_mode = False
        self.repeat_mode = False
        self.player_is_empty = True

        self.endReachedSignal.connect(self.next_track)
        self.playingSignal.connect(self._playingSlot)
        self.pausedSignal.connect(self._pausedSlot)
        self.stoppedSignal.connect(self._stoppedSlot)
        self.endReachedSignal.connect(self._stoppedSlot)
        self.mediaChangedCallbackSignal.connect(self._mediaChangedSlot)
        self.endReachedCallbackSignal.connect(self._endReachedSlot)
        self.errorCallbackSignal.connect(self._errorSlot)

        self._attachEvents()

        logger.debug("Created Woofer player instance")

    def _attachEvents(self):
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerOpening, self.__openingCallback)
        self._event_manager.event_attach(libvlc.EventType.MediaPlayerBuffering, self.__bufferingCallback)
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

    def _detachEvents(self):
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerOpening)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerBuffering)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerPlaying)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerPaused)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerStopped)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerForward)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerBackward)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerEndReached)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerEncounteredError)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerTimeChanged)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerPositionChanged)
        self._event_manager.event_detach(libvlc.EventType.MediaPlayerMediaChanged)

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
            logger.debug("Restoring session, adding media paths to _media_list...")

            self._media_list.lock()
            for path in mlist:
                # unicode_path, byte_path = tools.unicode2bytes(path)       # fix Windows encoding issues
                # vlc will parse media automatically if needed (before playing)
                self._media_list.add_media(path)
                self.media_list.append(os.path.normpath(path))
                # normpath to preserve win/unix compatibility when restoring session

            # set previous current media now as current
            media = self._media_list.item_at_index(self.shuffled_playlist[self.shuffled_playlist_current_index])
            self._media_list.unlock()

            self._media_player.set_media(media)
            self.player_is_empty = False
            media.release()
            logger.debug("All media paths restored.")

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
                logger.debug("Setting current media %s", path)
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
        logger.debug("Removing media item on index: %s", remove_index)

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
        remove_error = (self._media_list.remove_index(remove_index) == -1)
        self._media_list.unlock()
        del self.media_list[remove_index]

        if remove_error:
            logger.error("Unable to remove item from _media_list. "
                         "Item is not in the list or _media_list is read only! "
                         "Playlist len: %s, index: %s" % (len(self.shuffled_playlist), remove_index))
            self.errorSignal.emit(tools.ErrorMessages.CRITICAL,
                                  "Unable remove item from Woofer media list. "
                                  "Item is not in the list or the list is read only!",
                                  "playlist len: %s, removed index: %s" % (len(self.shuffled_playlist), remove_index))

        # decrease all references with higher index
        for i in range(len(self.shuffled_playlist)):
            index = self.shuffled_playlist[i]
            if index > remove_index:
                self.shuffled_playlist[i] -= 1
            elif index == remove_index:
                rem_idx_in_shuffled_playlist = i
        # remove media reference from shuffled_playlist
        del self.shuffled_playlist[rem_idx_in_shuffled_playlist]

        # change song if removed == played, but stop if there is no next song
        if must_change_song:
            logger.debug("Currently playing media has been removed from playlist, selecting next one.")
            if not self.shuffled_playlist:
                logger.debug("There is no other media left!")
                return

            self.play(item_playlist_id=self.shuffled_playlist[self.shuffled_playlist_current_index])
            if not restore_playing:
                self.stop()

        elif rem_idx_in_shuffled_playlist < self.shuffled_playlist_current_index:
            self.shuffled_playlist_current_index -= 1

    def clearMediaList(self):
        """
        Clears all existing items in media_list
        """
        logger.debug("Clearing _media_list")
        self.stop()
        self._media_list.release()                              # delete old media list
        self._media_list = self._instance.media_list_new()       # create new and empty list
        self._media_player.set_media(None)
        self.media_list = []
        self.player_is_empty = True

        self.shuffled_playlist = []
        self.shuffled_playlist_current_index = 0
        self.shuffled_playlist_old_index = 0

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
        if not self.shuffled_playlist:
            logger.debug("Play called, but there is no items to play!")
            return

        self.shuffled_playlist_old_index = self.shuffled_playlist_current_index

        # play given media (index) - find item in playlist
        if item_playlist_id is not None:
            logger.debug("Play method called with index: %s" % item_playlist_id)
            self._media_player.stop()
            self.shuffled_playlist_current_index = self.shuffled_playlist.index(item_playlist_id)

            play_media = self._media_list.item_at_index(item_playlist_id)
            self._media_player.set_media(play_media)
            self.player_is_empty = False
            play_media.release()
        else:
            logger.debug("Play method called")

        if self._media_player.play() == -1:
            current_media_path = self.media_list[self.shuffled_playlist[self.shuffled_playlist_current_index]]
            self.errorSignal.emit(tools.ErrorMessages.ERROR, "Error occurred when trying to play media file",
                                  "Media: %s" % current_media_path)

    @pyqtSlot()
    def pause(self):
        """
        Pause media_player (no effect if there is no media).
        """
        logger.debug("Pause method called")
        self._media_player.pause()

    @pyqtSlot()
    def stop(self):
        """
        Stop (no effect if there is no media)
        """
        logger.debug("Stop method called, stopping playback...")
        self._media_player.stop()

    @pyqtSlot(bool)
    def next_track(self, repeat=False, playlist_index=None):
        """
        Switches to next media in media_list if any.
        @param repeat: if set, current media is played again
        @type repeat: bool
        """
        self.shuffled_playlist_old_index = self.shuffled_playlist_current_index

        if playlist_index is not None:
            logger.debug("Setting next media to play by playlist_id: %s" % playlist_index)
            self._media_player.stop()
            play_media = self._media_list.item_at_index(playlist_index)
            self._media_player.set_media(play_media)
            self.player_is_empty = False
            play_media.release()
            self.shuffled_playlist_current_index = self.shuffled_playlist.index(playlist_index)  # find item in playlist

        elif repeat:
            logger.debug("Next media method called, repeating current song")
            self._media_player.stop()
            self._media_player.play()

        else:
            logger.debug("Next media method called, switching to next song if any...")

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
                logger.debug("There is no next media (song) to play!")
                self._media_player.stop()

    @pyqtSlot()
    def prev_track(self):
        """
        Switches to next media in media_list if any.
        Method returns False if there is no media to switch.
        @rtype : bool
        """
        logger.debug("Previous media method called")

        self.shuffled_playlist_old_index = self.shuffled_playlist_current_index

        if self._media_player.is_playing():
            self._media_player.stop()

        if self.shuffled_playlist_current_index - 1 >= 0:
            self.shuffled_playlist_current_index -= 1
            media = self._media_list.item_at_index(self.shuffled_playlist[self.shuffled_playlist_current_index])
            self._media_player.set_media(media)
            self.player_is_empty = False
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
        if not 0 <= value <= 200:
            raise ValueError("Volume must be in range <0, 200>")

        logger.debug("Volume set: %s", value)
        self._media_player.audio_set_volume(int(value))

    def getVolume(self):
        """
        Get current software audio volume in range [0, 100].
        @return: the software volume in percents (0 = mute, 100 = nominal / 0dB).
        @rtype: int
        """
        return self._media_player.audio_get_volume()

    def setMute(self, status):
        logger.debug("Setting audio MUTE to %s", status)
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
            logger.error("Media is not seekable")
            return False

        total_time = self.totalTime()
        if 0 <= new_time <= total_time:
            self._media_player.set_time(int(new_time))
            logger.debug("Playback time set: %s", new_time)
        else:
            raise ValueError("New time must be in range [0, %d]" % total_time)

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
        logger.debug("Playback position set: %s", new_pos)
        return self._media_player.set_position(new_pos / 100.0)

    def currentTime(self):
        """
        Get the current time (in ms).
        Method returns None if no media set.
        @rtype : int or None
        """
        ctime = self._media_player.get_time()

        if ctime == -1:
            logger.warning("There is no media set to get current time")
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
            logger.warning("There is no media set to get remaining time")
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
            self.shuffled_playlist_current_index = 0
        else:
            self.shuffled_playlist = sorted(self.shuffled_playlist)
            self.shuffled_playlist_current_index = current_id         # id_playlist is range-type (sorted) array

        logger.debug("SHUFFLE mode: %s", state)

    def setRepeat(self, state):
        """
        Enable/disable repeat mode
        @type state: bool
        """
        self.repeat_mode = state
        logger.debug("REPEAT mode: %s", state)

    def initMediaAdding(self, append=True):
        """
        Called before media adding is started from scanner/parser thread.
        @param append: append mode flag
        @type append: bool
        """
        logger.debug("Initializing media adding...")
        self.appending_mode = append
        self.append_media = append

    @pyqtSlot()
    def mediaAddingFinished(self):
        """
        Called when media adding ends.
        If shuffle_mode set, newly added media are shuffled with unplayed media.
        """
        logger.debug("Media adding finished.")
        if self.shuffle_mode:
            logger.debug("Shuffling newly added media...")
            # shuffle newly added media with the rest, which have not been played yet
            if self.appending_mode:
                index = self.shuffled_playlist_current_index+1      # shuffle all from currently played
                tmp_list = self.shuffled_playlist[index:]
                random.shuffle(tmp_list)
                self.shuffled_playlist[index:] = tmp_list
            else:
                self.setShuffle(True)       # implicit shuffle

    def quit(self):
        self.stop()
        self._detachEvents()

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
        current_index = self.shuffled_playlist[self.shuffled_playlist_current_index]
        last_index = self.shuffled_playlist[self.shuffled_playlist_old_index]
        self.mediaChangedSignal.emit(current_index, last_index)

    @pyqtSlot()
    def _endReachedSlot(self):
        """
        Slot is used as helper, because callback are called from vlc directly (from another thread),
        so to prevent cross-thread collision, variables (flags) are manipulated only from MediaPlayer thread
        """
        self.endReachedSignal.emit(self.repeat_mode)          # if repeat_mode then do not switch to next song

    @pyqtSlot()
    def _errorSlot(self):
        logger.warning("Media encountered error")
        current_media_path = self.media_list[self.shuffled_playlist[self.shuffled_playlist_current_index]]
        self.errorSignal.emit(tools.ErrorMessages.ERROR, "Error occurred when trying to play media file",
                              "Playing %s failed!" % current_media_path)

    # WARNING: CALLBACKS CALLED DIRECTLY FROM ANOTHER THREAD (VLC THREAD) !!!!

    def __timeChangedCallback(self, event):
        try:
            new_time = event.u.new_time
        except RuntimeError:
            logger.warning("Media player callback called, but C++ object does not exist. "
                           "If program is being closed, this is a possible behaviour.")
        else:
            self.timeChangedSignal.emit(new_time)

    def __positionChangedCallback(self, event):
        try:
            newPos = event.u.new_position
        except RuntimeError:
            logger.warning("Media player callback called, but C++ object does not exist. "
                           "If program is being closed, this is a possible behaviour.")
        else:
            newPos = 0 if newPos > 1 else newPos
            self.positionChangedSignal.emit(newPos)

    def __playingCallback(self, event):
        logger.debug("Player playing callback")
        self.playingSignal.emit()

    def __pausedCallback(self, event):
        logger.debug("Player paused callback")
        self.pausedSignal.emit()

    def __stoppedCallback(self, event):
        logger.debug("Player stopped callback")
        self.stoppedSignal.emit()

    def __forwardCallback(self, event):
        logger.debug("Player next track callback")

    def __backwardCallback(self, event):
        logger.debug("Player prev track callback")

    def __endReachedCallback(self, event):
        logger.debug("Player media end reached callback")
        self.endReachedCallbackSignal.emit()

    def __mediaChangedCallback(self, event):
        logger.debug("Player media changed callback")
        self.mediaChangedCallbackSignal.emit()

    def __errorCallback(self, event):
        self.errorCallbackSignal.emit()

    def __bufferingCallback(self, event):
        pass

    def __openingCallback(self, event):
        pass


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
        self._stop = False

        logger.debug("Media Parser initialized.")

    @pyqtSlot(list)
    def parseMedia(self, sources):
        """
        Parses media files. Result is send to media player in separated thread.
        Thread worker!
        @type sources: list of unicode
        """
        # END FLAG RECEIVED
        if not sources:
            logger.debug("Parser finished, end flag received.")
            self._stop = False           # reset stop flag
            self.finishedSignal.emit()

        # PARSE MEDIA FILES
        elif not self._stop:
            media_list = []
            for unicode_path in sources:
                media_object = self.vlc_instance.media_new(unicode_path)
                media_object.parse()
                media_list.append((unicode_path, media_object))

            self.dataParsedSignal.emit(media_list)

    def stop(self):
        """
        Called outside the thread to stop parsing.
        When _stop set, all incoming paths for parsing will be thrown away.
        """
        self._stop = True
