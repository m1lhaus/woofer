# -*- coding: utf-8 -*-
#
# Woofer - free open-source cross-platform music player
# Copyright (C) 2015 Milan Herbig <milanherbig[at]gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging
import urllib.request, urllib.error, urllib.parse
# import ssl
import os
import sys

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *

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
    """

    SERVER = 0
    CLIENT = 1

    messageReceivedSignal = pyqtSignal(str)

    def __init__(self, name):
        """
        @param name: server name (must be kind of unique)
        @type name: str
        """
        super(LocalServer, self).__init__()

        self.timeout = 3000
        self.server_name = name
        self.socket = QLocalSocket(self)
        self.localServer = QLocalServer(self)

        self.another_instance_running = not self.start()
        self.mode = LocalServer.CLIENT if self.another_instance_running else LocalServer.SERVER

        logger.debug("Application local server initialized")

    def start(self):
        """
        Before it tries to start a server, it tries to connect to local server by name created by another instance.
        @return: False if another instance running; True if successfully created local server
        @rtype: bool
        """
        logging.debug("Trying to connect to server named: %s", self.server_name)
        self.socket.connectToServer(self.server_name)
        if self.socket.waitForConnected(self.timeout):
            logger.debug("Connected -> another application instance is running")
            return False

        logger.debug("Unable to connect -> creating server and listening")
        self.localServer.newConnection.connect(self.newLocalSocketConnection)
        if not (self.localServer.listen(self.server_name) and self.localServer.isListening()):
            raise Exception("Unable to start listening local server!")

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
            logger.debug("Sending message to server...")
            self.socket.writeData(message)
            self.socket.flush()

            return True

        logger.error("Local socket is not connected to server! State: %s", SocketStates.get(state))
        return False

    @pyqtSlot()
    def newLocalSocketConnection(self):
        """
        Server slot called when new connection (client/socket) is pending.
        Incoming data are received and then sent through signal/slot to MainApp gui.
        """
        pendingClient = self.localServer.nextPendingConnection()
        logger.debug("Found new local connection to the server, socket state: %s", SocketStates[pendingClient.state()])

        while not pendingClient.bytesAvailable():
            pendingClient.waitForReadyRead()

        logger.debug("New message is available, reading...")
        message = str(pendingClient.readAll())

        # message must be decoded here, because PyQt somehow convert the str to unicode
        # message = message.decode(sys.getfilesystemencoding())

        self.messageReceivedSignal.emit(message)

    def exit(self):
        """
        Disconnects local sockets and closes server.
        @return: successful
        @rtype: bool
        """
        logger.debug("Disconnecting socket and closing server...")
        self.localServer.close()
        self.socket.disconnectFromServer()
        if self.socket.state() != QLocalSocket.UnconnectedState:
            self.socket.waitForDisconnected(self.timeout)

        return self.socket.state() != QLocalSocket.ConnectedState and not self.localServer.isListening()


class Downloader(QObject):
    """
    Downloader component with does, what would you expect. It downloads the file.
    Class is built to run in separated thread!
    """

    # enums
    DOWNLOADING = 1
    COMPLETED = 2
    STOPPED = 3
    ERROR = 4

    errorSignal = pyqtSignal(int, str, str)

    blockDownloadedSignal = pyqtSignal(int, int)
    downloaderStartedSignal = pyqtSignal(int)               # total size
    downloaderFinishedSignal = pyqtSignal(int, str)     # file path

    def __init__(self, url, download_dir=""):
        """
        @param url: URL to target file (HTTPS supported)
        @type url: unicode
        @param download_dir: where to stored downloaded file
        @type download_dir: unicode
        """
        super(Downloader, self).__init__()

        self.url = url                          # should be valid URL (hardcoded)
        self.file_name = url.split("/")[-1]
        self.download_dir = os.path.abspath(download_dir)
        self.status = None

        self._stop = False
        self._block_size = 8192

        self.mutex = QMutex()

        logger.debug("Downloader class initialized")

    @pyqtSlot()
    def startDownload(self):
        """
        Thread worker. Method must NOT be called from MainThread directly!
        Method will start downloading the file from given URL.
        """
        self._stop = False
        block_size = self._block_size       # prevent overhead

        if not os.path.isdir(self.download_dir):
            os.makedirs(self.download_dir)

        logger.debug("Starting downloading file '%s' from '%s' to '%s' ..." % 
                     (self.file_name, self.url, self.download_dir))

        dest_filename = os.path.join(self.download_dir, self.file_name)
        size_downloaded = 0

        try:
            url_object = urllib.request.urlopen(self.url)
            total_size = int(url_object.info()["Content-Length"])
            num_blocks = int(total_size / block_size)
            one_percent = int(0.01 * num_blocks)                    # how many blocks are 1% from total_size

            with open(dest_filename, 'wb') as fobject:
                logger.debug("Starting to read data from server ...")
                self.status = Downloader.DOWNLOADING
                self.downloaderStartedSignal.emit(total_size)           # update GUI

                i = 1
                while True:
                    data = url_object.read(block_size)
                    if not data:
                        logger.debug("Reading from server finished OK")
                        self.status = Downloader.COMPLETED
                        break

                    # write downloaded data to disk
                    fobject.write(data)
                    size_downloaded += len(data)

                    if self._stop:
                        logger.debug("Downloading jop has been interrupted!")
                        self.status = Downloader.STOPPED
                        break

                    # to update download status in GUI and also prevent signal/slot overhead
                    if i == one_percent:
                        self.blockDownloadedSignal.emit(size_downloaded, total_size)
                        i = 1
                    else:
                        i += 1

        except urllib.error.HTTPError:
            logger.exception("Error when connecting to the server and downloading the file!")
            self.status = Downloader.ERROR
            self.errorSignal.emit(tools.ErrorMessages.ERROR,
                                  "Error when connecting to the server and downloading the update!",
                                  "URL: '%s'" % self.url)

        except IOError:
            logger.exception("Unable to write downloaded data to file '%s'!" % dest_filename)
            self.status = Downloader.ERROR
            self.errorSignal.emit(tools.ErrorMessages.ERROR,
                                  "Error when writing downloaded update file!",
                                  "File: '%s'" % dest_filename)

        except Exception:
            logger.exception("Unexpected error when downloading the update from server!")
            self.status = Downloader.ERROR
            self.errorSignal.emit(tools.ErrorMessages.ERROR,
                                  "Unexpected error when downloading the update from server!",
                                  "")

        self.downloaderFinishedSignal.emit(self.status, dest_filename)

    def stopDownload(self):
        """
        DIRECTLY CALLED method to immediately stop downloading.
        """
        mutexLocker = QMutexLocker(self.mutex)
        try:
            logger.debug("Stopping downloader ...")
            self._stop = True
        finally:
            mutexLocker.unlock()

    @staticmethod
    def pingURL(address='http://www.google.com', timeout=5):
        """
        Checks if internet connection is available (ping to given IP)
        @param address: destination url
        @param timeout: timeout in seconds
        @rtype: bool
        """
        try:
            response = urllib.request.urlopen(address, timeout=timeout)
        except urllib.error.URLError:
            pass
        else:
            return True

        return False
