# -*- coding: utf-8 -*-

"""
Windows classes for catching global (system-wide) shortcuts.
"""

import logging
import ctypes

from PyQt4.QtCore import *

import tools

logger = logging.getLogger(__name__)


class GlobalHKListener(QObject):
    """
    Registers global hotkeys through win32 api.
    If registering fails, WindowsKeyHook class should be used instead!
    """
    errorSignal = pyqtSignal(int, unicode, unicode)
    retrySignal = pyqtSignal()

    mediaPlayKeyPressed = pyqtSignal()
    mediaStopKeyPressed = pyqtSignal()
    mediaNextTrackKeyPressed = pyqtSignal()
    mediaPrevTrackKeyPressed = pyqtSignal()

    def __init__(self):
        super(GlobalHKListener, self).__init__()
        self.stop = False
        self.registered = False

        self.retryTimer = QTimer(self)
        self.retryDelay = 5000

        self.WM_HOTKEY = 0x0312
        self.WM_TIMER = 0x0113

        self.HOTKEYS = {
            1: (0xB3, 'VK_MEDIA_PLAY_PAUSE'),
            2: (0xB2, 'VK_MEDIA_STOP'),
            3: (0xB0, 'VK_MEDIA_NEXT_TRACK'),
            4: (0xB1, 'VK_MEDIA_PREV_TRACK'),
        }

        self.HOTKEY_ACTIONS = {
            1: self.mediaPlayKeyPressed,
            2: self.mediaStopKeyPressed,
            3: self.mediaNextTrackKeyPressed,
            4: self.mediaPrevTrackKeyPressed
        }

        self.retryTimer.timeout.connect(self._retry_registration)
        self.retrySignal.connect(self.start_listening, Qt.QueuedConnection)

        logger.debug(u"Windows global hotkey listener initialized.")

    @pyqtSlot()
    def start_listening(self):
        """
        Thread worker. Called when thread is executed.
        Listens for all system-wide messages. Method makes thread busy, unresponsive!
        When thread.quit() method is invoked, system-wide quit(0) message is sent to worker which also
        terminates message listener.
        """
        if not self.registered and not self._registerHotkeys():
            logger.warning(u"Unable to register all multimedia hotkeys, unregistering and retrying every %d sec",
                           self.retryDelay/1000)
            self._unregisterHotkeys()
            self.retryTimer.start(self.retryDelay)
            self.errorSignal.emit(tools.ErrorMessages.WARNING,
                                  u"Another media application already using multimedia hotkeys for playback control.",
                                  u"")
        else:
            # start listening
            logger.debug(u"Starting windows key-down hook (listener) loop.")
            try:
                msg = ctypes.wintypes.MSG()

                # GetMessageA() is blocking function - it waits until some message is received
                # so timer posts its WM_TIMER every 100ms and wakes GetMessageA() function
                timerId = ctypes.windll.user32.SetTimer(None, None, 100, None)

                # handles the WM_HOTKEY messages and pass everything else along.
                while not self.stop and ctypes.windll.user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == self.WM_HOTKEY:
                        # process -> call handler
                        keySignal = self.HOTKEY_ACTIONS.get(msg.wParam)
                        if keySignal:
                            keySignal.emit()

                ctypes.windll.user32.KillTimer(None, timerId)
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageA(ctypes.byref(msg))

            finally:
                self._unregisterHotkeys()

            logger.debug(u"Main hotkey listener loop ended.")

    def _registerHotkeys(self):
        """
        Call Win32 API to register global shortcut (hotkey) for current thread id.
        Only this (worker) thread is then notified when shortcut is executed.
        @return: success
        @rtype: bool
        """
        for hk_id, (vk, vk_name) in self.HOTKEYS.items():
            if not ctypes.windll.user32.RegisterHotKey(None, hk_id, 0, vk):
                return False
        self.registered = True

        return True

    def _unregisterHotkeys(self):
        """
        Call Win32 API to unregister global shortcut (hotkey) for current thread id.
        """
        for hk_id in self.HOTKEYS.keys():
            ctypes.windll.user32.UnregisterHotKey(None, hk_id)

        self.registered = False

    @pyqtSlot()
    def _retry_registration(self):
        """
        If first hotkey registration failed, this slot is called every %(retry_delay) sec
        to retry hotkey registration. Retry timer is stopped on success and listener executed.
        """
        if self._registerHotkeys():
            self.retryTimer.stop()
            self.errorSignal.emit(tools.ErrorMessages.INFO,
                                  u"Multimedia hotkeys are now available for playback control.", u"")
            self.retrySignal.emit()
        else:
            self._unregisterHotkeys()

    def stop_listening(self):
        """
        Called when application is about to close to unregister all global hotkeys.
        Worker loop (listener) will be terminated automatically when quit message is sent.
        """
        logger.debug(u"Stopping hotkey listener...")
        self.stop = True