# -*- coding: utf-8 -*-

"""
Windows classes for catching global (system-wide) shortcuts.
"""

import logging
import ctypes

from PyQt4.QtCore import *

from tools import ErrorMessages

logger = logging.getLogger(__name__)


class GlobalHKListener(QObject):
    """
    Registers global hotkeys through win32 api.
    If registering fails, WindowsKeyHook class should be used instead!
    """
    errorSignal = pyqtSignal(int, unicode, unicode)

    mediaPlayKeyPressed = pyqtSignal()
    mediaStopKeyPressed = pyqtSignal()
    mediaNextTrackKeyPressed = pyqtSignal()
    mediaPrevTrackKeyPressed = pyqtSignal()

    def __init__(self):
        super(GlobalHKListener, self).__init__()
        self._stop = False

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

        logger.debug(u"Windows global hotkey listener initialized.")

    @pyqtSlot()
    def start_listening(self):
        """
        Thread worker. Called when thread is executed.
        Listens for all system-wide messages. Method makes thread busy, unresponsive!
        When thread.quit() method is invoked, system-wide quit(0) message is sent to worker which also
        terminates message listener.
        """
        if not self._registerHotkeys():
            logger.warning(u"Unable to register all multimedia hotkeys, this global media hotkeys won't be available!")
            self._unregisterHotkeys()
            self.errorSignal.emit(ErrorMessages.ERROR, u"Unable to register all multimedia hotkeys, "
                                  u"global media hotkeys won't be available", u"Check log for more information.")
            return

        logger.debug(u"Starting windows key-down hook (listener) loop.")
        try:
            msg = ctypes.wintypes.MSG()

            # GetMessageA() is blocking function - it waits until some message is received
            # so timer posts its WM_TIMER every 100ms and wakes GetMessageA() function
            timerId = ctypes.windll.user32.SetTimer(None, None, 100, None)

            # handles the WM_HOTKEY messages and pass everything else along.
            while not self._stop and ctypes.windll.user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
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
        logger.debug(u"Registering Windows media hotkeys...")
        for hk_id, (vk, vk_name) in self.HOTKEYS.items():
            if not ctypes.windll.user32.RegisterHotKey(None, hk_id, 0, vk):
                logger.error(u"Unable to register hotkey id %s for key %s named %s", hk_id, vk, vk_name)
                return False

        return True

    def _unregisterHotkeys(self):
        logger.debug(u"Un-registering Windows media hotkeys...")
        for hk_id in self.HOTKEYS.keys():
            ctypes.windll.user32.UnregisterHotKey(None, hk_id)

    def stop_listening(self):
        """
        Called when application is about to close to unregister all global hotkeys.
        Worker loop (listener) will be terminated automatically when quit message is sent.
        """
        logger.debug(u"Stopping hotkey listener...")
        self._stop = True