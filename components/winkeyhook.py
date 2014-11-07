# -*- coding: utf-8 -*-

"""
Windows classes for catching global (system-wide) shortcuts.
"""

import logging
import ctypes

from PyQt5.QtCore import *

from tools.misc import ErrorMessages

logger = logging.getLogger(__name__)
logger.debug('Import ' + __name__)


class GlobalHKListener(QObject):
    """
    Registers global hotkeys through win32 api.
    If registering fails, WindowsKeyHook class should be used instead!

    Based on http://timgolden.me.uk/python/win32_how_do_i/catch_system_wide_hotkeys.html
    """

    mediaPlayKeyPressed = pyqtSignal()
    mediaStopKeyPressed = pyqtSignal()
    mediaNextTrackKeyPressed = pyqtSignal()
    mediaPrevTrackKeyPressed = pyqtSignal()
    errorSignal = pyqtSignal(int, str, str)

    WM_HOTKEY = 0x0312
    HOTKEYS = {
        1: (0xB3, 'VK_MEDIA_PLAY_PAUSE'),
        2: (0xB2, 'VK_MEDIA_STOP'),
        3: (0xB0, 'VK_MEDIA_NEXT_TRACK'),
        4: (0xB1, 'VK_MEDIA_PREV_TRACK'),
    }

    def __init__(self):
        super(GlobalHKListener, self).__init__()

        self.HOTKEY_ACTIONS = {
            1: self.mediaPlayKeyPressed,
            2: self.mediaStopKeyPressed,
            3: self.mediaNextTrackKeyPressed,
            4: self.mediaPrevTrackKeyPressed
        }

        logger.debug("Windows global hotkey listener initialized.")

    @pyqtSlot()
    def start_listening(self):
        """
        Thread worker. Called when thread is executed.
        Listens for all system-wide messages. Method makes thread busy, unresponsive!
        When thread.quit() method is invoked, system-wide quit(0) message is sent to worker which also
        terminates message listener.
        """
        if self.__registerHotkeys():
            currentThread = self.thread()
            logger.debug("Starting windows key-down hook (listener) loop.")
            try:
                msg = ctypes.wintypes.MSG()

                # GetMessageA() is blocking function - it waits until some message is received
                # so timer posts its WM_TIMER every 100ms and wakes GetMessageA() function
                timerId = ctypes.windll.user32.SetTimer(None, None, 100, None)

                # handles the WM_HOTKEY messages and pass everything else along.
                while not currentThread.isInterruptionRequested() and ctypes.windll.user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == self.WM_HOTKEY:
                        # process -> call handler
                        keySignal = self.HOTKEY_ACTIONS.get(msg.wParam)
                        if keySignal:
                            keySignal.emit()

                ctypes.windll.user32.KillTimer(None, timerId)
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageA(ctypes.byref(msg))

            except:
                logger.warning("Some unexpected thing happened in main listener loop, unregistering hotkeys...")

                # don't forget to unregister hotkeys, so application could register them again next time
                for hk_id in self.HOTKEYS.keys():
                    ctypes.windll.user32.UnregisterHotKey(None, hk_id)

        else:
            logger.warning("Unable to register all multimedia hotkeys, this global media hotkeys won't be available!")
            self.errorSignal.emit(ErrorMessages.ERROR, "Unable to register all multimedia hotkeys, "
                                  "global media hotkeys won't be available", "Check log for more information.")

        logger.debug("Main listener loop ended.")

    def stop_listening(self):
        """
        Called when application is about to close to unregister all global hotkeys.
        Worker loop (listener) will be terminated automatically when quit message is sent.
        """
        logger.debug("Stopping hotkey listener, unregistering global hotkeys...")
        for hk_id in self.HOTKEYS.keys():
            ctypes.windll.user32.UnregisterHotKey(None, hk_id)

        logger.debug("Hotkeys unregistered successfully.")

    def __registerHotkeys(self):
        def unregister_all():
            for hk_id in GlobalHKListener.HOTKEYS.keys():
                ctypes.windll.user32.UnregisterHotKey(None, hk_id)

        for hk_id, (vk, vk_name) in self.HOTKEYS.items():
            logger.debug("Registering hotkey id %s for key %s named %s", hk_id, vk, vk_name)

            if not ctypes.windll.user32.RegisterHotKey(None, hk_id, 0, vk):
                logger.warning("Unable to register hotkey id %s for key %s named %s", hk_id, vk, vk_name)
                unregister_all()
                return False

        return True
