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

    errorSignal = pyqtSignal(int, unicode, unicode)

    blockDownloadedSignal = pyqtSignal(int, int)
    downloaderStartedSignal = pyqtSignal(int)               # total size
    downloaderFinishedSignal = pyqtSignal(int, unicode)     # file path

    def __init__(self, url, download_dir=""):
        super(Downloader, self).__init__()

        self.url = url
        self.progress = None
        self.status = None
        self.file_name = url.split("/")[-1]
        self.download_dir = os.path.abspath(download_dir)
        self.file_size = None
        self.url_object = None
        self.size_downloaded = 0
        self.is_paused = False

        logger.debug("Downloader class initialized")

    @pyqtSlot()
    def startDownload(self, start=None):
        self.is_paused = False

        if not os.path.isdir(self.download_dir):
            os.makedirs(self.download_dir)

        if start is not None:
            logger.debug("Resuming downloading file '%s' from '%s' to '%s' ..." % (self.file_name, self.url, self.download_dir))
            req = urllib2.Request(self.url)
            req.headers["Range"] = "bytes=%s-%s" % (start, self.file_size)
            file_mode = 'ab'
            self.url_object = urllib2.urlopen(req)
            self.size_downloaded = start
        else:
            logger.debug("Starting downloading file '%s' from '%s' to '%s' ..." % (self.file_name, self.url, self.download_dir))
            self.url_object = urllib2.urlopen(self.url)
            self.size_downloaded = 0
            file_mode = 'wb'

        self.file_size = int(self.url_object.info()["Content-Length"])
        block_size = 8192
        num_blocks = int(self.file_size / block_size)
        one_percent = int(0.01 * num_blocks)

        try:
            ffile = os.path.join(self.download_dir, self.file_name)
            with open(ffile, file_mode) as fobject:
                logger.debug(u"Starting to read data from server ...")
                self.status = Downloader.DOWNLOADING
                self.downloaderStartedSignal.emit(self.file_size)           # update GUI

                i = 1
                while True:
                    data = self.url_object.read(block_size)
                    if not data:
                        logger.debug(u"Reading from server finished")
                        self.status = Downloader.COMPLETED
                        break

                    # write downloaded data
                    fobject.write(data)
                    self.size_downloaded += len(data)

                    if self.is_paused:
                        logger.debug(u"Downloading jop has been interrupted!")
                        self.status = Downloader.PAUSED
                        break

                    # to update download status in GUI (prevent signal/slot overhead)
                    if i == one_percent:
                        self.blockDownloadedSignal.emit(self.size_downloaded, self.file_size)
                        i = 1
                    else:
                        i += 1

        except IOError:
            logger.exception(u"Unable to write downloaded data to file '%s'!" % ffile)
            self.status = Downloader.ERROR
            self.errorSignal(tools.ErrorMessages.ERROR, u"Error when writing write downloaded data", u"File: '%s'" % ffile)

        except urllib2.HTTPError, urllib2.URLError:
            logger.exception(u"Error when connecting to the server and downloading the file!")
            self.status = Downloader.ERROR

        except Exception:
            logger.exception(u"Unexpected error when downloading the file from server!")
            self.status = Downloader.ERROR

        self.downloaderFinishedSignal.emit(self.status, ffile)

    def pauseDownload(self):
        logger.debug(u"Stopping downloader ...")
        self.is_paused = True

    # def resumeDownload(self):
    #     self.is_paused = False
    #     self.startDownload(self.url, self.download_dir, self.size_downloaded)

