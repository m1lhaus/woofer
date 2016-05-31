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
Simple script that removes Woofer user data and preferences
"""

import os
import shutil
import time

from PyQt5.QtCore import QSettings

import tools

print("Removing LOG_DIR at: %s", tools.LOG_DIR)
if os.path.isdir(tools.LOG_DIR):
    shutil.rmtree(tools.LOG_DIR)

print("Removing DATA_DIR at: %s", tools.DATA_DIR)
if os.path.isdir(tools.DATA_DIR):
    shutil.rmtree(tools.DATA_DIR)

print("Removing user preferences (QSettings)")
qsettings = QSettings("WooferPlayer", "Woofer")
qsettings.clear()

print("=" * 50)
print("All done")

time.sleep(3)
