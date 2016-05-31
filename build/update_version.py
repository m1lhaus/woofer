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
Script retrieves version info from git and updates file build.info.
"""

import sys
import os
import subprocess
import re
import ujson
import datetime


build_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
root_dir = os.path.dirname(build_dir)
os.chdir(root_dir)


def get_git_version_and_hash():
    full_version_info = subprocess.getoutput('git describe --tags --long')
    pattern = re.compile('v([^-]+)-?([^-]+)?-([0-9]+)-(.+)')
    matchObj = pattern.match(full_version_info)
    if matchObj:
        version = matchObj.group(1)
        vlabel = matchObj.group(2) or ""
        commits = matchObj.group(3)
        revision = matchObj.group(4)
    else:
        raise Exception("Unable to parse retrieved git version info! "
                        "Expected something like this: 'v1.0.0-0-ge502b4a', but given %s" % full_version_info)

    vlabel = "-" + vlabel if vlabel else vlabel
    return version + vlabel, commits, revision


def get_git_revision_hash():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'])


def get_git_revision_short_hash():
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'])


def write_version_file(data):
    with open("build.info", 'w') as f:
        ujson.dump(data, f, indent=4)

if __name__ == "__main__":
    version, commits, revision = get_git_version_and_hash()

    data = {'author': "Milan Herbig",
            'email': "milanherbig(at)gmail.com",
            'web': "http://m1lhaus.github.io/woofer",
            'version': version,
            'commits': commits,
            'revision': revision,
            'date': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")}

    write_version_file(data)