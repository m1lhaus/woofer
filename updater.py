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

"""
Updater component for Woofer player.
Script takes files in root directory where updater.exe is executed and updates files in Woofer install directory.
WINDOWS ONLY!
"""

import os
import shutil
import argparse
import sys
import time
import logging
import datetime

import psutil

from tools import getFullTraceback, win_admin


# ----------- helpers ----------------


class CopyToLogger(object):
    """
    Fake file-like stream object that copies stdout/stderr writes to a logger instance.
    """

    def __init__(self, fdnum, logger, log_level=logging.INFO):
        if fdnum == 0:
            sys.stdout = self
            self.orig_output = sys.__stdout__
        elif fdnum == 1:
            sys.stderr = self
            self.orig_output = sys.__stderr__
        else:
            raise Exception("Given file descriptor num: %s is not supported!" % fdnum)

        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        self.orig_output.write(buf)
        buf = buf.decode(sys.getfilesystemencoding())
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def __getattr__(self, name):
        return self.orig_output.__getattribute__(name)  # pass all other methods to original fd


def copy(src, dst):
    """
    Copy file or dir from source to dst
    """
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(dst, os.path.basename(src)))
    else:
        shutil.copy(src, dst)


def remove(src):
    """
    Remove file or folder
    """
    if os.path.isdir(src):
        shutil.rmtree(src)
    else:
        os.remove(src)


# ------------------------------------

def setup_logging(log_dir):
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)

    date = datetime.datetime.now()
    msg_format = "%(threadName)-10s  %(name)-30s %(lineno)-.5d  %(levelname)-8s %(asctime)-20s  %(message)s"
    log_path = os.path.join(log_dir, "updater_%s.log" % date.strftime("%Y-%m-%d_%H-%M-%S"))
    logging.basicConfig(level=logging.DEBUG, format=msg_format, filename=log_path)
    logger = logging.getLogger('')  # get root logger

    # redirects all stderr output (exceptions, etc.) to logger ERROR level
    sys.stdout = CopyToLogger(0, logger, logging.DEBUG)
    sys.stderr = CopyToLogger(1, logger, logging.ERROR)
    logger.debug("Logger initialized")

    return logger


def woofer_finished():
    def is_running(pid):
        return pid in psutil.pids()

    print("Waiting until parent process PID: %s finishes ..." % args.pid)

    attempts = 10
    while is_running(args.pid) and attempts > 0:  # no more waiting than 5s
        time.sleep(0.5)
        attempts -= 1

    if is_running(args.pid):
        print("Woofer player is still running. CLOSE the player and try it again!")
        return False

    return True


def backup_old_files(backup_dir):
    print("Backing up old Woofer files to '%s'" % backup_dir)

    if os.path.isdir(backup_dir):
        shutil.rmtree(backup_dir)
    os.mkdir(backup_dir)

    # move all except log and data dir to backup directory
    dir_content = [os.path.join(args.installDir, item) for item in os.listdir(args.installDir) if
                   item not in ("data", "log", "updater_backup")]
    print("Creating backup...")
    for item in dir_content:
        copy(item, backup_dir)

    print("Removing old files...")
    for item in dir_content:
        remove(item)


def copy_new_files():
    print("Copying new files ...")
    dir_content = [os.path.abspath(item) for item in os.listdir(os.getcwd()) if not item == "data"]
    for src in dir_content:
        copy(src, args.installDir)


def restore_backup(backup_dir):
    print("Restoring backup files ...")
    # remove new files
    backup_dirname = os.path.basename(backup_dir)
    content_to_remove = [os.path.join(args.installDir, item) for item in os.listdir(args.installDir) if
                         item not in ("data", "log", backup_dirname)]
    for item in content_to_remove:
        try:
            remove(item)
        except Exception:
            pass

    # restore old files
    content_to_restore = [os.path.join(backup_dir, item) for item in os.listdir(backup_dir)]
    for item in content_to_restore:
        try:
            copy(item, args.installDir)
        except Exception:
            pass


def clean(backup_dir):
    print("Removing backup files ...")
    shutil.rmtree(backup_dir)


def init_woofer():
    # find launcher
    launcher = os.path.join(args.installDir, "woofer.exe")
    if not os.path.isfile(launcher):
        raise Exception("Unable to locate Woofer launcher at '%s'!" % args.installDir)

    print("Starting Woofer player ...")
    os.startfile(launcher)


def main():
    logger.debug("Waiting until Woofer player is closed ...")

    # wait until Woofer process finishes, optionally terminate script execution
    terminate = False
    while not terminate and not woofer_finished():
        terminate = input("Try it again? (y/n): ") != 'y'
    if terminate:
        sys.exit(0)

    backup_dir = os.path.join(args.installDir, "updater_backup")
    try:
        backup_old_files(backup_dir)
        copy_new_files()
    except Exception:
        print("\n", getFullTraceback(), "\n")
        restore_backup(backup_dir)
        clean(backup_dir)

        print("\n", "Error occurred when updating Woofer player. "
                    "Update manually instead by downloading most recent version from "
                    "'http://m1lhaus.github.io/woofer/'.")
        print("\n", "-" * 25, "\n")
        input('Press Enter to exit.')
    else:
        clean(backup_dir)
        if args.restart:
            init_woofer()

        print("\n", "OK - Update finished successfully!")
        time.sleep(3)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(
            description="Updater component for Woofer player. Script take downloaded package "
                        "and updates files in Woofer directory."
                        "This script should be always used only by Woofer player!")
        parser.add_argument("installDir", type=str,
                            help="Where Woofer player files are stored")
        parser.add_argument('pid', type=int,
                            help="PID of Woofer player process")
        parser.add_argument('-r', '--restart', action='store_true',
                            help="ReOpen Woofer after update")
        parser.add_argument('-a', '--admin', action='store_true',
                            help="Re-run with elevated rights (admin)")
        args = parser.parse_args()

        if args.admin:
            if not win_admin.isUserAdmin():
                print("Have no admin rights, elevating rights now...")
                win_admin.runAsAdmin()
                print("Admin script launched, exit 0")
        else:
            os.chdir(os.path.dirname(sys.argv[0]))
            # args.installDir = args.installDir.decode(sys.getfilesystemencoding())  # utf8 support
            if not os.path.isdir(args.installDir):
                raise Exception("Install dir '%s' does NOT exist!" % args.installDir)

            logger = setup_logging(log_dir=os.path.join(args.installDir, "log"))
            main()

    except Exception:
        print(getFullTraceback())
        print("\n", "-" * 25, "\n")
        input('Press Enter to exit.')
        raise
