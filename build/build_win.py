#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The script is used as automated  dist builder for Windows only .
Uses pyinstaller python module to build dependency independent binaries.
Optionally built dist could be zipped.
"""

import sys
import os
import subprocess
import platform
import shutil

os.chdir("..")
print "Working directory set to: ", os.getcwd()

VERSION = "0.7.0"                   # todo: get version and revision from GIT
PRJ_SPEC_FILE = "woofer.spec"
PYINSTALLER_EXE_NAME = "pyinstaller"


def which(program):

    # apped .exe extension on Windows
    if os.name == 'nt' and not program.endswith('.exe'):
        program += ".exe"

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return ""


def main():
    print "Trying to find PyInstaller executable in system PATH..."

    pyinstaller_exe = which(PYINSTALLER_EXE_NAME)
    if not pyinstaller_exe:
        raise Exception("PyInstaller executable not found in system PATH!")
    else:
        print "PyInstaller executable found at:", pyinstaller_exe

    spec_file = os.path.join(os.getcwd(), "build", PRJ_SPEC_FILE)
    dist_path = os.path.join(os.getcwd(), "dist", "woofer")
    if not os.path.isfile(spec_file):
        raise Exception("Unable to locate spec file at: %s" % spec_file)
    else:
        print "Pyinstaller spec file found at:", spec_file

    print "Building dist..."
    print "=" * 100

    process = subprocess.Popen([pyinstaller_exe, spec_file, '-y', '--clean'], stdout=sys.stdout, stderr=sys.stderr)
    retcode = process.wait()

    print "=" * 100
    if retcode != 0:
        raise Exception("Building finished with error code: %s!!!" % retcode)

    new_dist_path = os.path.join(os.getcwd(), "build", "release", "woofer_%s_v%s"
                                 % (platform.architecture()[0], VERSION))
    if os.path.isdir(new_dist_path):
        shutil.rmtree(new_dist_path)
    shutil.move(dist_path, new_dist_path)

    dist_path = new_dist_path

    print "Dist package successfully built to:", dist_path

    decision = raw_input("Are you want to ZIP built dist folder? (y/n) ")
    if decision != 'y':
        return

    zip_folder = shutil.make_archive(dist_path, "zip", dist_path)
    print "Dist zipped successfully to:", zip_folder

    print "Removing dist folder..."
    shutil.rmtree(dist_path)
    shutil.rmtree(os.path.join(os.getcwd(), "dist"))


if __name__ == "__main__":
    main()
    print "Finished!"
    raw_input("\nPress Enter key to exit...")