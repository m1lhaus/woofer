#!/usr/bin/env python
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
The script is used as automated  dist builder for Windows only .
Uses pyinstaller python module to build dependency independent binaries.
Optionally built dist could be zipped.
"""

import sys
import os
import subprocess
import shutil
import ujson

import tools

# - WINDOWS
if tools.PLATFORM == 32:
    VLC_PATH = os.path.abspath(os.path.join("..", "libvlc"))
else:
    VLC_PATH = os.path.abspath(os.path.join("..", "libvlc64"))

#  - LINUX
# VLC_LIBVLC_PATH = "/usr/lib/libvlc.so.5"
# VLC_LIBVLCCORE_PATH = "/usr/lib/libvlccore.so.7"
# VLC_PLUGINS_PATH = "/usr/lib/vlc/plugins"


ZIP_ENABLED = False
PRJ_SPEC_FILE = "windows.spec" if os.name == "nt" else "linux.spec"
PYINSTALLER_EXE_NAME = "pyinstaller"


def which(program):
    # append .exe extension on Windows
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


def get_build_info():
    # update version/build data
    subprocess.call([sys.executable, os.path.join(build_dir, "update_version.py")])

    build_info_file = os.path.join(root_dir, "build.info")
    if not os.path.isfile(build_info_file):
        print("Unable to locate build.info file!", file=sys.stderr)
        return None

    with open(build_info_file, 'r') as f:
        build_data = ujson.load(f)               # dict

    return build_data


def get_pyinstaller_exe():
    print("Trying to find PyInstaller executable in system PATH...")
    pyinstaller_exe = which(PYINSTALLER_EXE_NAME)
    # pyinstaller_exe = r"C:\Python35\Scripts\pyinstaller.exe"
    # pyinstaller_exe = r"C:\Python35-32\Scripts\pyinstaller.exe"

    if not pyinstaller_exe:
        raise Exception("PyInstaller executable not found in system PATH!")
    else:
        print("PyInstaller executable found at:", pyinstaller_exe)

    return pyinstaller_exe


def get_project_spec_file():
    spec_file = os.path.join(build_dir, PRJ_SPEC_FILE)

    if not os.path.isfile(spec_file):
        raise Exception("Unable to locate spec file at: %s" % spec_file)
    else:
        print("Pyinstaller spec file found at:", spec_file)

    return spec_file


def copy_dependencies(dst):
    shutil.copy(os.path.join(root_dir, 'LICENSE.txt'), dst)
    shutil.copy(os.path.join(root_dir, 'build.info'), dst)
    shutil.copytree(os.path.join(root_dir, "lang"), os.path.join(dst, "lang"))


def main():
    build_data = get_build_info()
    pyinstaller_exe = get_pyinstaller_exe()
    spec_file = get_project_spec_file()
    dist_path = os.path.join(root_dir, "dist", "woofer")
    version_long = "%s-rev%s-%s" % (build_data['version'], build_data['commits'], build_data['revision'])
    version_short = "%s.%s" % (build_data['version'], build_data['commits'])

    print("Building distribution...")
    print("=" * 100)
    process = subprocess.Popen([pyinstaller_exe, spec_file, '-y', '--clean', '--log-level=WARN'])
    retcode = process.wait()
    print("=" * 100)

    if retcode != 0:
        raise Exception("Building finished with error code: %s!!!" % retcode)

    # move built distribution to release folder
    new_dist_path = os.path.join(build_dir, "release", "woofer_%s_%sbit_v%s" %
                                 (PRJ_SPEC_FILE[:3], tools.PLATFORM, version_long))

    if os.path.isdir(new_dist_path):
        shutil.rmtree(new_dist_path)
    shutil.move(dist_path, new_dist_path)
    dist_path = new_dist_path

    copy_dependencies(new_dist_path)

    print("Distribution package successfully built to:", dist_path)

    if ZIP_ENABLED:
        decision = input("Are you want to ZIP built dist folder? (y/n) ")
        if decision != 'y':
            return

        zip_folder = shutil.make_archive(dist_path, "zip", dist_path)
        print("Dist zipped successfully to:", zip_folder)

        print("Removing dist folder...")
        shutil.rmtree(dist_path)
        shutil.rmtree(os.path.join(root_dir, "dist"))


if __name__ == "__main__":
    if not os.path.isdir(VLC_PATH):
        raise Exception("VLC folder cannot be found at '%s'!" % VLC_PATH)

    build_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    root_dir = os.path.dirname(build_dir)
    os.chdir(root_dir)
    print("Root directory set to: ", os.path.abspath(root_dir))
    print("Working directory set to: ", os.getcwd())

    main()

    print("Finished successfully!")
