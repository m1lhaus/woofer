# -*- coding: utf-8 -*-

import logging
import urllib2
import ssl
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
    Local server launched when application is started.
    This server is used to communicate between another instances of Woofer player launched by user via LocalSockets.

    Logic when Woofer is started:
    - init server
        - try connect to server if exists
            - yes
                - send command and optional console args
                - close app
            - no
                - start local server and start listening
                - continue and start Woofer player

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
    """
    Downloader component with does, what would you expect. It downloads the file.
    Class is built to run in separated thread!

    @param url: URL to target file (HTTPS supported)
    @param download_dir: where to stored downloaded file
    """

    DOWNLOADING = 1
    COMPLETED = 2
    STOPPED = 3
    ERROR = 4

    errorSignal = pyqtSignal(int, unicode, unicode)

    blockDownloadedSignal = pyqtSignal(int, int)
    downloaderStartedSignal = pyqtSignal(int)               # total size
    downloaderFinishedSignal = pyqtSignal(int, unicode)     # file path

    def __init__(self, url, download_dir=""):
        super(Downloader, self).__init__()

        self.url = url
        self.file_name = url.split("/")[-1]
        self.download_dir = os.path.abspath(download_dir)

        self.status = None
        self.stop = False

        logger.debug(u"Downloader class initialized")

    @pyqtSlot()
    def startDownload(self):
        """
        Thread worker.
        Method will start downloading the file from given URL.
        """
        self.stop = False

        if not os.path.isdir(self.download_dir):
            os.makedirs(self.download_dir)

        logger.debug(u"Starting downloading file '%s' from '%s' to '%s' ..." % 
                     (self.file_name, self.url, self.download_dir))

        dest_filename = os.path.join(self.download_dir, self.file_name)
        size_downloaded = 0

        try:
            # context = ssl._create_unverified_context()                  # CA validation sometimes fails, so disable it
            url_object = urllib2.urlopen(self.url)      #, context=context)
            total_size = int(url_object.info()["Content-Length"])
            num_blocks = int(total_size / 8192)
            one_percent = int(0.01 * num_blocks)                    # how many blocks are 1% from total_size

            with open(dest_filename, 'wb') as fobject:
                logger.debug(u"Starting to read data from server ...")
                self.status = Downloader.DOWNLOADING
                self.downloaderStartedSignal.emit(total_size)           # update GUI

                i = 1
                while True:
                    data = url_object.read(8192)
                    if not data:
                        logger.debug(u"Reading from server finished OK")
                        self.status = Downloader.COMPLETED
                        break

                    # write downloaded data to disk
                    fobject.write(data)
                    size_downloaded += len(data)

                    if self.stop:
                        logger.debug(u"Downloading jop has been interrupted!")
                        self.status = Downloader.STOPPED
                        break

                    # to update download status in GUI and also prevent signal/slot overhead
                    if i == one_percent:
                        self.blockDownloadedSignal.emit(size_downloaded, total_size)
                        i = 1
                    else:
                        i += 1

        except urllib2.HTTPError, urllib2.URLError:
            logger.exception(u"Error when connecting to the server and downloading the file!")
            self.status = Downloader.ERROR
            self.errorSignal.emit(tools.ErrorMessages.ERROR,
                                  u"Error when connecting to the server and downloading the update!",
                                  u"URL: '%s'" % self.url)

        except IOError:
            logger.exception(u"Unable to write downloaded data to file '%s'!" % dest_filename)
            self.status = Downloader.ERROR
            self.errorSignal.emit(tools.ErrorMessages.ERROR,
                                  u"Error when writing downloaded update file!",
                                  u"File: '%s'" % dest_filename)

        except Exception:
            logger.exception(u"Unexpected error when downloading the update from server!")
            self.status = Downloader.ERROR
            self.errorSignal.emit(tools.ErrorMessages.ERROR,
                                  u"Unexpected error when downloading the update from server!",
                                  u"")

        self.downloaderFinishedSignal.emit(self.status, dest_filename)

        # self.errorSignal.emit(tools.ErrorMessages.INFO, u"Update package downloaded", u"")

    def stopDownload(self):
        """
        Method to immediately stop downloading.
        WARNING: This method is called directly from other thread!
        """
        logger.debug(u"Stopping downloader ...")
        self.stop = True

    @staticmethod
    def internetConnection(address='http://74.125.228.100', timeout=1):
        """
        Checks if internet connection is available (ping to given IP)
        @rtype: bool
        """
        try:
            response = urllib2.urlopen(address, timeout=timeout)
        except urllib2.URLError as err:
            pass
        else:
            return True

        return False


