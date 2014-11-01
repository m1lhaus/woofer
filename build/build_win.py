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
import zipfile
import platform
import shutil

os.chdir("..")
print "Working directory set to: ", os.getcwd()


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


def find_svn(start_dir):
    current_dir = start_dir
    depth = 0
    while depth < 5:
        if '.svn' in os.listdir(current_dir):
            return current_dir

        depth += 1
        current_dir = os.path.dirname(current_dir)


def get_svn_revision(folder='.'):
    p = subprocess.Popen(["svnversion", folder, '-n'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return stdout if stdout[0].isdigit() else ""


def main():
    print "Finding subversion working copy root dir to retrieve revision number."
    svn_dir = find_svn(os.getcwd())
    svn_rev = get_svn_revision(svn_dir)

    if not svn_rev:
        print "Unable to get svn revision number of working copy in tree from:", os.getcwd()
        decision = raw_input("Are you want to continue anyway? (y/n) ")
        if decision != 'y':
            return False
    svn_rev = svn_rev.replace(':', '-')
    print "Subversion working copy found, revision:", svn_rev

    try:
        int(svn_rev)
    except ValueError:
        print "Subversion revision number isn't pure integer."
        print "You should first commit all changes and update working copy to get nice and clean working copy."
        decision = raw_input("Are you want to continue anyway? (y/n) ")

        if decision != 'y':
            return

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

    new_dist_path = os.path.join(os.getcwd(), "build", "release", "woofer_%s_rev%s"
                                 % (platform.architecture()[0], svn_rev))
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