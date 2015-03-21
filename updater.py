# -*- coding: utf-8 -*-

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


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects stdout/stderr writes to a logger instance.
    """

    def __init__(self, fdnum, logger, log_level=logging.INFO):
        if fdnum == 0:
            sys.stdout = self
            self.orig_output = sys.__stdout__
        elif fdnum == 1:
            sys.stderr = self
            self.orig_output = sys.__stderr__
        else:
            raise Exception(u"Given file descriptor num: %s is not supported!" % fdnum)

        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        if buf == '\n':
            self.orig_output.write(buf)
        else:
            if isinstance(buf, str):
                buf = unicode(buf, u'utf-8')
            for line in buf.rstrip().splitlines():
                self.logger.log(self.log_level, line.rstrip())

    def __getattr__(self, name):
        return self.orig_output.__getattribute__(name)              # pass all other methods to original fd


def setup_logging(log_dir):
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)

    date = datetime.datetime.now()
    msg_format = u"%(threadName)-10s  %(name)-30s %(lineno)-.5d  %(levelname)-8s %(asctime)-20s  %(message)s"
    log_path = os.path.join(log_dir, u"updater_%s.log" % date.strftime("%Y-%m-%d_%H-%M-%S"))
    logging.basicConfig(level=logging.DEBUG, format=msg_format, filename=log_path)
    logger = logging.getLogger('')      # get root logger

    # redirects all stderr output (exceptions, etc.) to logger ERROR level
    sys.stdout = StreamToLogger(0, logger, logging.DEBUG)
    sys.stderr = StreamToLogger(1, logger, logging.ERROR)
    logger.debug("Logger initialized")

    return logger


def woofer_finished():
    def is_running(pid):
        return pid in psutil.get_pid_list()

    print "Waiting until parent process PID: %s finishes ..." % args.pid

    attempts = 5
    time.sleep(0.5)
    while is_running(args.pid) and attempts > 0:         # no more waiting than 3s
        time.sleep(0.5)
        attempts -= 1

    if is_running(args.pid):
        print "Woofer player is still running. CLOSE the player and try it again!"
        return False

    return True


def backup_old_files():
    print "Backing up old Woofer files ..."

    back_dir = os.path.join(args.installDir, "updater_backup")
    if os.path.isdir(back_dir):
        shutil.rmtree(back_dir)
    os.mkdir(back_dir)

    # move all except log and data dir to backup directory
    dir_content = [os.path.join(args.installDir, item) for item in os.listdir(args.installDir) if item not in ("data", "log")]
    for item in dir_content:
        shutil.move(item, back_dir)

    return back_dir


def copy_new_files():
    print "Copying new files to install directory ..."

    dir_content = [os.path.abspath(item) for item in os.listdir(os.getcwd()) if not item == "data"]
    for src in dir_content:
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(args.installDir, os.path.basename(src)))
        else:
            shutil.copy(src, args.installDir)


def restore_backup(backup_dir):
    print "Restoring old files ..."

    # remove new files
    backup_dirname = os.path.basename(backup_dir)
    content_to_remove = [os.path.join(args.installDir, item) for item in os.listdir(args.installDir) if item not in ("data", "log", backup_dirname)]
    for item in content_to_remove:
        if os.path.isfile(item):
            os.remove(item)
        else:
            shutil.rmtree(item)

    # restore old files
    content_to_restore = [os.path.join(backup_dir, item) for item in os.listdir(backup_dir)]
    for item in content_to_restore:
        shutil.move(item, args.installDir)

    shutil.rmtree(backup_dir)


def clean(backup_dir):
    print "Removing backup files ..."
    shutil.rmtree(backup_dir)


def init_woofer():
    # find launcher
    if sys.platform.startswith('win'):
        launcher = os.path.join(args.installDir, "woofer.exe")
    elif sys.platform.startswith('linux'):
        launcher = os.path.join(args.installDir, "woofer")
    else:
        raise NotImplementedError("Unknown platform type '%s'!" % sys.platform)
    if not os.path.isfile(launcher):
        raise Exception("Unable to locate Woofer launcher at '%s'!" % args.installDir)

    print "Starting Woofer player ..."
    os.system(" ".join(["start", launcher]))


def main():
    logger.debug("Waiting until Woofer player is closed ...")

    # wait until Woofer process finishes, optionally terminate script execution
    terminate = False
    while not terminate and not woofer_finished():
        terminate = raw_input("Try it again? (y/n): ") != 'y'
    if terminate:
        sys.exit(0)

    backup_dir = backup_old_files()
    try:
        copy_new_files()
    except Exception:
        logger.exception("Error occurred when copying new files to install directory!")
        restore_backup(backup_dir)
        print "ERROR - Error occurred when copying new files to install directory!"
    else:
        clean(backup_dir)
        if args.restart:
            init_woofer()

        print "OK - Update finished successfully!"


if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]))

    parser = argparse.ArgumentParser(description="Updater component for Woofer player. Script take downloaded package "
                                                 "and updates files in Woofer directory."
                                                 "This script should be always used only by Woofer player!")
    parser.add_argument("installDir", type=str,
                        help="Where Woofer player files are stored")
    parser.add_argument('pid', type=int,
                        help="PID of Woofer player process")
    parser.add_argument('-r', '--restart', action='store_true',
                        help="ReOpen Woofer after update")
    args = parser.parse_args()

    if not os.path.isdir(args.installDir):
        raise Exception("Install dir '%s' does NOT exist!" % args.installDir)

    logger = setup_logging(log_dir=os.path.join(args.installDir, "log"))
    main()
