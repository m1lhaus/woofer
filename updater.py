# -*- coding: utf-8 -*-

import os
import shutil
import argparse


def backup():
    back_dir = os.path.join(args.installDir, "updater_backup")
    if os.path.isdir(back_dir):
        shutil.rmtree(back_dir)
    os.mkdir(back_dir)

    dir_content = [os.path.join(args.installDir, item) for item in os.listdir(args.installDir)]
    for item in dir_content:
        shutil.move(item, back_dir)


def main():
    if not os.path.isfile(args.zipFile):
        raise Exception("Unable to find  ZIP file at '%s'!" % args.zipFile)

    if not os.path.isdir(args.installDir):
        raise Exception("Install dir '%s' does NOT exist!" % args.installDir)

    # backup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("zipFile", type=str,
                        help="")
    parser.add_argument("installDir", type=str,
                        help="")
    parser.add_argument('pid', type=int,
                        help="")

    args = parser.parse_args()

    main()