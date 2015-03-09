# -*- coding: utf-8 -*-

"""
Updater component for Woofer player.
Script take downloaded update ZIP file and updates files in Woofer directory.

WINDOWS ONLY for now.
"""

import os
import shutil
import argparse
import zipfile
import sys
import time
import subprocess

import psutil


def woofer_finished():
    def is_running(pid):
        return pid in psutil.get_pid_list()

    print "Waiting until parent process PID: %s finishes ..." % args.pid
    time.sleep(0.5)
    elapsed = 0
    while is_running(args.pid) and elapsed < 2.5:         # no more waiting than 3s
        time.sleep(0.5)
        elapsed += 0.5

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

    dir_content = [os.path.join(args.installDir, item) for item in os.listdir(args.installDir) if not item == "data"]
    for item in dir_content:
        shutil.move(item, back_dir)


def extract_files():
    def get_members(zip_object):
        parts = []
        for name in zip_object.namelist():
            if not name.endswith('/'):
                parts.append(name.split('/')[:-1])
        prefix = os.path.commonprefix(parts) or ''
        if prefix:
            prefix = '/'.join(prefix) + '/'
        offset = len(prefix)
        for zipinfo in zip_object.infolist():
            name = zipinfo.filename
            if len(name) > offset:
                zipinfo.filename = name[offset:]
                yield zipinfo

    print "Extracting new files ..."
    with zipfile.ZipFile(args.zipFile, 'r') as zip_object:
        if zip_object.testzip() is not None:
            raise Exception("Given ZIP archive '%s' is corrupted!" % args.zipFile)

        zip_object.extractall(args.installDir, get_members(zip_object))


def restore_backup():
    print "Restoring old files ..."

    back_dirname = "updater_backup"
    back_dirpath = os.path.join(args.installDir, "updater_backup")

    dir_content = [os.path.join(args.installDir, item) for item in os.listdir(args.installDir) if not item in ("data", back_dirname)]
    for item in dir_content:
        if os.path.isfile(item):
            os.remove(item)
        else:
            shutil.rmtree(item)

    dir_content = [os.path.join(args.installDir, back_dirname, item) for item in os.listdir(back_dirpath)]
    for item in dir_content:
        shutil.move(item, args.installDir)

    shutil.rmtree(back_dirpath)


def clean():
    print "Removing backup files ..."

    back_dirpath = os.path.join(args.installDir, "updater_backup")
    shutil.rmtree(back_dirpath)


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

    if sys.platform.startswith('linux'):
        subprocess.call(["xdg-open", launcher])
    else:
        os.startfile(launcher)


def main():
    if not os.path.isfile(args.zipFile):
        raise Exception("Unable to find  ZIP file at '%s'!" % args.zipFile)

    if not os.path.isdir(args.installDir):
        raise Exception("Install dir '%s' does NOT exist!" % args.installDir)

    terminate = False
    while not terminate and not woofer_finished():
        terminate = raw_input("Try it again? (y/n): ") != 'y'

    if terminate:
        print "TERMINATED"
        sys.exit(0)

    backup_old_files()
    try:
        extract_files()
    except Exception:
        restore_backup()
        raise

    clean()
    if args.restart:
        init_woofer()

    print "FINISHED"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Updater component for Woofer player. Script take downloaded update "
                                                 "ZIP file and updates files in Woofer directory."
                                                 "This script should be always used only by Woofer player!")

    parser.add_argument("zipFile", type=str,
                        help="Source ZIP file")
    parser.add_argument("installDir", type=str,
                        help="Where Woofer player files are stored")
    parser.add_argument('pid', type=int,
                        help="PID of Woofer player process")
    parser.add_argument('-r', '--restart', action='store_true',
                        help="ReOpen Woofer after update")

    args = parser.parse_args()

    main()