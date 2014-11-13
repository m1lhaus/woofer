# -*- coding: utf-8 -*-

"""
Windows classes for catching global (system-wide) shortcuts.
"""

import logging
import pythoncom
import pyHook
import ctypes
import win32con

from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


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

        logger.debug(u"Windows global hotkey listener initialized.")

    @pyqtSlot()
    def start_listening(self):
        """
        Thread worker. Called when thread is executed.
        Listens for all system-wide messages. Method makes thread busy, unresponsive!
        When thread.quit() method is invoked, system-wide quit(0) message is sent to worker which also
        terminates message listener.
        """
        self.__registerHotkeys()

        # handles the WM_HOTKEY messages and pass everything else along.
        logger.debug(u"Starting windows key-down hook (listener) loop.")
        try:
            msg = ctypes.wintypes.MSG()
            while ctypes.windll.user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == win32con.WM_HOTKEY:
                    # process -> call handler
                    keySignal = self.HOTKEY_ACTIONS.get(msg.wParam)
                    if keySignal:
                        keySignal.emit()

            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageA(ctypes.byref(msg))

        finally:
            # if anything goes wrong, don't forget to unregister hotkeys,
            # so application could register them again next time
            logger.warning(u"Some unexpected thing happened in main listener loop, unregistering hotkeys...")
            for hk_id in self.HOTKEYS.keys():
                ctypes.windll.user32.UnregisterHotKey(None, hk_id)

        logger.debug(u"Main listener loop ended.")

    def stop_listening(self):
        """
        Called when application is about to close to unregister all global hotkeys.
        Worker loop (listener) will be terminated automatically when quit message is sent.
        """
        logger.debug(u"Stopping hotkey listener, unregistering global hotkeys...")
        for hk_id in self.HOTKEYS.keys():
            ctypes.windll.user32.UnregisterHotKey(None, hk_id)

        logger.debug(u"Hotkeys unregistered successfully.")

    def __registerHotkeys(self):
        for hk_id, (vk, vk_name) in self.HOTKEYS.items():
            logger.debug(u"Registering hotkey id %s for key %s named %s", hk_id, vk, vk_name)

            if not ctypes.windll.user32.RegisterHotKey(None, hk_id, 0, vk):
                logger.error(u"Unable to register hotkey id %s for key %s named %s", hk_id, vk, vk_name)

    @staticmethod
    def isAbleToRegisterHK():
        logger.debug(u"Trying to test media hotkeys for a test...")
        try:
            for hk_id, (vk, vk_name) in GlobalHKListener.HOTKEYS.items():
                if not ctypes.windll.user32.RegisterHotKey(None, hk_id, 0, vk):
                    logger.warning(u"Unable to register hotkey id: %s named %s", hk_id, vk_name)
                    return False

            logger.debug(u"All hotkeys has been successfully registered, now unregister them...")
        finally:
            for hk_id in GlobalHKListener.HOTKEYS.keys():
                ctypes.windll.user32.UnregisterHotKey(None, hk_id)

        logger.debug(u"All hotkeys unregistered successfully.")
        return True


class WindowsKeyHook(QObject):

    mediaPlayKeyPressed = pyqtSignal()
    mediaStopKeyPressed = pyqtSignal()
    mediaNextTrackKeyPressed = pyqtSignal()
    mediaPrevTrackKeyPressed = pyqtSignal()

    def __init__(self):
        super(WindowsKeyHook, self).__init__()

        # create a hook manager
        self.hm = pyHook.HookManager()
        self.hm.KeyDown = self.OnKeyboardEvent      # watch for all keyboard events
        self.hm.HookKeyboard()                      # set the hook

        logger.debug(u"Windows key-down hook initialized")

    def OnKeyboardEvent(self, event):
        """
        Callback called when keyboard message 'key down' is sent system-wide. If one of the media keys is being pressed,
        sent signal to GUI app and filter this event, so another multimedia application wont get this event.

        Available properties:
        ---------------------------------
        'MessageName:',event.MessageName
        'Message:',event.Message
        'Time:',event.Time
        'Window:',event.Window
        'WindowName:',event.WindowName
        'Ascii:', event.Ascii, chr(event.Ascii)
        'Key:', event.Key
        'KeyID:', event.KeyID
        'ScanCode:', event.ScanCode
        'Extended:', event.Extended
        'Injected:', event.Injected
        'Alt', event.Alt
        'Transition', event.Transition
        ---------------------------------
        @type event: pyhook.HookManager.KeyboardEvent
        @return: bool - ignore event or not
        """
        ignore_event = True

        # Media_Play_Pause
        if event.KeyID == 179:
            logger.debug(u"Global key Media_Play_Pause caught")
            ignore_event = False
            self.mediaPlayKeyPressed.emit()

        # Media_Stop
        elif event.KeyID == 178:
            logger.debug(u"Global key Media_Stop caught")
            ignore_event = False
            self.mediaStopKeyPressed.emit()

        # Media_Next_Track
        elif event.KeyID == 176:
            logger.debug(u"Global key Media_Play_Pause caught")
            ignore_event = False
            self.mediaNextTrackKeyPressed.emit()

        # Media_Prev_Track
        elif event.KeyID == 177:
            logger.debug(u"Global key Media_Play_Pause caught")
            ignore_event = False
            self.mediaPrevTrackKeyPressed.emit()

        return ignore_event

    @pyqtSlot()
    def start_listening(self):
        """
        Thread worker. Called when thread is executed.
        Listens for all system-wide messages. Method makes thread busy, unresponsive!
        When thread.quit() method is invoked, system-wide quit(0) message is sent to worker which also
        terminates message listener.
        """
        logger.debug(u"Starting windows key-down hook (listener)")
        pythoncom.PumpMessages()        # endless loop

    def stop_listening(self):
        """
        Listening is stopped automatically when QThread.quit() is invoked => quit message is caught
        @return:
        """
        pass