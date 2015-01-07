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
import json


ZIP_ENABLED = False
PRJ_SPEC_FILE = "woofer.spec"
PYINSTALLER_EXE_NAME = "pyinstaller"


build_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
root_dir = os.path.dirname(build_dir)
os.chdir(root_dir)
print "Root directory set to: ", os.path.abspath(root_dir)
print "Working directory set to: ", os.getcwd()


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


def get_build_data():
    subprocess.call([sys.executable, os.path.join(build_dir, "update_version.py")])           # update version/build data

    build_info_file = os.path.join(root_dir, u"build.info")
    if not os.path.isfile(build_info_file):
        print >> sys.stderr, "Unable to locate build.info file!"
        return None

    with open(build_info_file, 'r') as f:
        build_data = json.load(f)               # dict

    return build_data


def get_pyinstaller_exe():
    print "Trying to find PyInstaller executable in system PATH..."
    pyinstaller_exe = which(PYINSTALLER_EXE_NAME)
    if not pyinstaller_exe:
        raise Exception("PyInstaller executable not found in system PATH!")
    else:
        print "PyInstaller executable found at:", pyinstaller_exe

    return pyinstaller_exe


def get_project_spec_file():
    spec_file = os.path.join(build_dir, PRJ_SPEC_FILE)

    if not os.path.isfile(spec_file):
        raise Exception("Unable to locate spec file at: %s" % spec_file)
    else:
        print "Pyinstaller spec file found at:", spec_file

    return spec_file


def main():
    build_data = get_build_data()
    pyinstaller_exe = get_pyinstaller_exe()
    spec_file = get_project_spec_file()
    dist_path = os.path.join(root_dir, "dist", "woofer")
    version_long = "%s-rev%s-%s" % (build_data['version'], build_data['commits'], build_data['revision'])
    version_short = "%s.%s" % (build_data['version'], build_data['commits'])

    print "Building distribution..."
    print "=" * 100
    process = subprocess.Popen([pyinstaller_exe, spec_file, '-y', '--clean'], stdout=sys.stdout, stderr=sys.stderr)
    retcode = process.wait()
    print "=" * 100

    if retcode != 0:
        raise Exception("Building finished with error code: %s!!!" % retcode)

    # move built distribution to release folder
    new_dist_path = os.path.join(build_dir, "release", "woofer_%s_v%s" % (platform.architecture()[0], version_long))
    if os.path.isdir(new_dist_path):
        shutil.rmtree(new_dist_path)
    shutil.move(dist_path, new_dist_path)
    dist_path = new_dist_path

    print "Dist package successfully built to:", dist_path

    if ZIP_ENABLED:
        decision = raw_input("Are you want to ZIP built dist folder? (y/n) ")
        if decision != 'y':
            return

        zip_folder = shutil.make_archive(dist_path, "zip", dist_path)
        print "Dist zipped successfully to:", zip_folder

        print "Removing dist folder..."
        shutil.rmtree(dist_path)
        shutil.rmtree(os.path.join(root_dir, "dist"))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print >> sys.stderr, str(e).decode(sys.getfilesystemencoding())
        raw_input("\nPress Enter key to exit...")

    print "Finished!"
