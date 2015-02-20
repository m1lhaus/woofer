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
import urllib2
import os
import sys

from PyQt4.QtCore import *
from PyQt4.QtNetwork import *

import tools


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

    @param name: server name (must be kind of unique)
    @type name: str
    """

    SERVER = 0
    CLIENT = 1

    messageReceivedSignal = pyqtSignal(str)

    def __init__(self, name):
        super(LocalServer, self).__init__()

        self.timeout = 3000
        self.server_name = name
        self.socket = QLocalSocket(self)
        self.localServer = QLocalServer(self)

        self.another_instance_running = not self.start()
        self.mode = LocalServer.CLIENT if self.another_instance_running else LocalServer.SERVER

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


class Downloader(QObject):

    DOWNLOADING = 1
    COMPLETED = 2
    PAUSED = 3
    ERROR = 4

    completedSignal = pyqtSignal()
    blockDownloadedSignal = pyqtSignal(int)
    errorSignal = pyqtSignal(int, unicode, unicode)

    def __init__(self):
        super(Downloader, self).__init__()

        self.url = None
        self.progress = None
        self.status = None
        self.file_name = None
        self.download_dir = ""
        self.file_size = None
        self.url_object = None
        self.size_downloaded = 0
        self.is_paused = False
        self.is_downloading = False

        logger.debug("Downloader class initialized")

    def startDownload(self, url, download_dir="", start=None):
        self.is_paused = False
        self.url = url
        self.file_name = url.split("/")[-1]
        self.download_dir = download_dir
        if not os.path.isdir(self.download_dir):
            os.makedirs(self.download_dir)

        if start is not None:
            logger.debug("Resuming downloading file '%s' from '%s' to '%s' ..." % (self.file_name, self.url, self.download_dir))
            req = urllib2.Request(url)
            req.headers["Range"] = "bytes=%s-%s" % (start, self.file_size)
            self.url_object = urllib2.urlopen(req)
            self.size_downloaded = start
        else:
            logger.debug("Starting downloading file '%s' from '%s' to '%s' ..." % (self.file_name, self.url, self.download_dir))
            self.url_object = urllib2.urlopen(url)
            self.size_downloaded = 0

        self.file_size = int(self.url_object.info()["Content-Length"])
        block_sz = 8192

        try:
            ffile = os.path.join(self.download_dir, self.file_name)
            with open(ffile, "ab") as fobject:
                while True:
                    buffer = self.url_object.read(block_sz)
                    if not buffer:
                        self.status = Downloader.COMPLETED
                        break
                    fobject.write(buffer)
                    self.size_downloaded += len(buffer)
                    self.status = Downloader.DOWNLOADING
                    if self.is_paused:
                        break

            self.completedSignal.emit()

        except IOError:
            logger.exception(u"Unable to write downloaded data to file '%s'!" % ffile)
            self.status = Downloader.ERROR
            self.errorSignal(tools.ErrorMessages.ERROR, u"Error when writing write downloaded data", u"File: '%s'" % ffile)

    def pauseDownload(self):
        self.is_paused = True

    def resumeDownload(self):
        self.is_paused = False
        self.startDownload(self.url, self.download_dir, self.size_downloaded)


