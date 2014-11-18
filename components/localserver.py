# -*- coding: utf-8 -*-

"""
Local server launched when application is started.
This server is used to communicate between another instances of Woofer player launched by user.

Logic when Woofer is started:
- init server
    - try connect to server if exists
        - yes
            - send command and optional console args
            - close app
        - no
            - start local server and start listening
            - continue and start Woofer player
"""

import logging
import sys

from PyQt4.QtCore import *
from PyQt4.QtNetwork import *


logger = logging.getLogger(__name__)

SocketStates = {
    QLocalSocket.UnconnectedState: "Unconnected",
    QLocalSocket.ConnectingState: "Connecting",
    QLocalSocket.ConnectedState: "Connected",
    QLocalSocket.ClosingState: "Closing"
}


class LocalServer(QObject):
    """
    Local server is used to communicate between another instances
    of Woofer player launched by user via LocalSockets.

    @param application_name: server name (must be kind of unique)
    @type application_name: str
    """

    messageReceivedSignal = pyqtSignal(str)

    def __init__(self, application_name):
        super(LocalServer, self).__init__()

        self.timeout = 3000
        self.server_name = application_name
        self.socket = QLocalSocket(self)
        self.localServer = QLocalServer(self)
        self.another_instance_running = not self.start()

        logger.debug(u"Application local server initialized")

    def start(self):
        """
        Before it tries to start a server, it tries to connect to local server by name created by another instance.
        @return: False if another instance running; True if successfully created local server
        @rtype: bool
        """
        logging.debug(u"Trying to connect to server named: %s", self.server_name)
        self.socket.connectToServer(self.server_name)
        if self.socket.waitForConnected(self.timeout):
            logger.debug(u"Connected -> another application instance is running")
            return False

        logger.debug(u"Unable to connect -> creating server and listening")
        self.localServer.newConnection.connect(self.newLocalSocketConnection)
        if not (self.localServer.listen(self.server_name) and self.localServer.isListening()):
            raise Exception(u"Unable to start listening local server!")

        return True

    def sendMessage(self, message):
        """
        Send string message to another running instance.
        @type message: str
        @return: successful
        @rtype: bool
        """
        state = self.socket.state()
        if state == QLocalSocket.ConnectedState:
            logger.debug(u"Sending message to server...")
            self.socket.writeData(message)
            self.socket.flush()

            return True

        logger.error(u"Local socket is not connected to server! State: %s", SocketStates.get(state))
        return False

    @pyqtSlot()
    def newLocalSocketConnection(self):
        """
        Server slot called when new connection (client/socket) is pending.
        Incoming data are received and then sent through signal/slot to MainApp gui.
        """
        pendingClient = self.localServer.nextPendingConnection()
        logger.debug(u"Found new local connection to the server, socket state: %s", SocketStates[pendingClient.state()])

        while not pendingClient.bytesAvailable():
            pendingClient.waitForReadyRead()

        logger.debug(u"New message is available, reading...")
        message = str(pendingClient.readAll())

        # message must be decoded here, because PyQt somehow convert the str to unicode
        message = message.decode(sys.getfilesystemencoding())

        self.messageReceivedSignal.emit(message)

    def exit(self):
        """
        Disconnects local sockets and closes server.
        @return: successful
        @rtype: bool
        """
        logger.debug(u"Disconnecting socket and closing server...")
        self.localServer.close()
        self.socket.disconnectFromServer()
        if self.socket.state() != QLocalSocket.UnconnectedState:
            self.socket.waitForDisconnected(self.timeout)

        return self.socket.state() != QLocalSocket.ConnectedState and not self.localServer.isListening()


