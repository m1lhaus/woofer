# -*- coding: utf-8 -*-

"""
Platform dependent classes for catching global (system-wide) shortcuts.
"""

__version__ = "$Id$"

import logging
import os

from PyQt4.QtCore import *

# WINDOWS ONLY
if os.name == 'nt':
    import pythoncom
    import pyHook

# LINUX ONLY
elif os.name == 'posix':
    pass

logger = logging.getLogger(__name__)
logger.debug(u'Import ' + __name__)


class WindowsHook(QObject):

    mediaPlayKeyPressed = pyqtSignal()
    mediaStopKeyPressed = pyqtSignal()
    mediaNextTrackKeyPressed = pyqtSignal()
    mediaPrevTrackKeyPressed = pyqtSignal()

    def __init__(self):
        super(WindowsHook, self).__init__()

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
    def startHook(self):
        """
        Thread worker. Called when thread is executed.
        Listens for all system-wide messages. Method makes thread busy, unresponsive!
        When thread.quit() method is invoked, system-wide quit(0) message is sent to worker which also
        terminates message listener.
        """
        logger.debug(u"Starting windows key-down hook (listener)")
        pythoncom.PumpMessages()        # endless loop
