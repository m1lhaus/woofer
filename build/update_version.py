#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script retrieves verison info from git and updates file build.info.
"""

import sys
import os
import subprocess
import re
import json
import datetime


build_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
root_dir = os.path.dirname(build_dir)
os.chdir(root_dir)


def get_git_version_and_hash():
    full_version_info = subprocess.check_output(['git', 'describe', '--tags', '--long'])
    pattern = re.compile('v([^-]+)-?([^-]+)?-([0-9]+)-(.+)')
    matchObj = pattern.match(full_version_info)
    if matchObj:
        version = matchObj.group(1)
        vlabel = matchObj.group(2) or ""
        commits = matchObj.group(3)
        revision = matchObj.group(4)
    else:
        raise Exception("Unable to parse retrieved git version info! "
                        "Expected something like this: 'v0.7-0-ge502b4a', but given %s" % full_version_info)

    vlabel = "-" + vlabel if vlabel else vlabel
    return version + vlabel, commits, revision


def get_git_revision_hash():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'])


def get_git_revision_short_hash():
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'])


def write_version_file(data):
    with open("build.info", 'w') as f:
        json.dump(data, f)

if __name__ == "__main__":
    version, commits, revision = get_git_version_and_hash()

    data = {'author': u"Milan Herbig",
            'email': u"milanherbig(at)gmail.com",
            'web': u"http://m1lhaus.github.io/woofer",
            'version': version,
            'commits': commits,
            'revision': revision,
            'date': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")}

    write_version_file(data)