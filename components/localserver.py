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

from PyQt4.QtCore import *
from PyQt4.QtNetwork import *


logger = logging.getLogger(__name__)

SocketStates = {
    QLocalSocket.UnconnectedState: "UnconnectedState",
    QLocalSocket.ConnectingState: "ConnectingState",
    QLocalSocket.ConnectedState: "ConnectedState",
    QLocalSocket.ClosingState: "ClosingState"
}


class LocalServer(QObject):

    messageReceivedSignal = pyqtSignal(str)

    def __init__(self, application_name):
        super(LocalServer, self).__init__()

        self.timeout = 3000
        self.server_name = application_name
        self.socket = QLocalSocket(self)
        self.localServer = QLocalServer(self)

        self.another_instance_running = self.start()

        logger.debug(u"Application local server initialized")

    def start(self):
        logging.debug(u"Trying to connect to server named: %s", self.server_name)
        self.socket.connectToServer(self.server_name)
        if self.socket.waitForConnected(self.timeout):
            logger.debug(u"Connected -> another application instance is running")
            return True

        logger.debug(u"Unable to connect -> creating server and listening")

        self.localServer.newConnection.connect(self.newLocalSocketConnection)
        self.localServer.listen(self.server_name)
        return False

    def sendMessage(self, message):
        if self.socket.waitForConnected(500):
            logger.debug(u"Sending message to server...")
            self.socket.writeData(message)
            self.socket.flush()

    @pyqtSlot()
    def newLocalSocketConnection(self):
        pendingClient = self.localServer.nextPendingConnection()
        logger.debug(u"Found new local connection to the server, socket state: %s", SocketStates[pendingClient.state()])

        while not pendingClient.bytesAvailable():
            pendingClient.waitForReadyRead()

        logger.debug(u"New message is available, reading...")
        message = str(pendingClient.readAll())

        self.messageReceivedSignal.emit(message)

    def exit(self):
        logger.debug(u"Disconnecting socket and closing server...")
        self.socket.disconnectFromServer()
        self.socket.waitForDisconnected(self.timeout)
        logger.debug(u"Socket state: %s", SocketStates[self.socket.state()])
        self.localServer.close()


