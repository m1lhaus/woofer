# -*- coding: utf-8 -*-
# -*- mode: python -*-
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

# - WINDOWS

# find VLC folder
import os
import platform
PLATFORM = 32 if platform.architecture()[0] == '32bit' else 64
if PLATFORM == 32:
    VLC_PATH = os.path.abspath(os.path.join(".", "libvlc"))
else:
    VLC_PATH = os.path.abspath(os.path.join(".", "libvlc64"))
assert os.path.isdir(VLC_PATH)
assert os.path.isfile(os.path.join(VLC_PATH, "libvlc.dll"))

a = Analysis(['../woofer.py'],
             pathex=['build'],
             binaries=[(VLC_PATH, '.')])

b = Analysis(['../cmdargs.py'],
             pathex=['build'])
c = Analysis(['../updater.py'],
             pathex=['build'])

MERGE((a, "woofer", "woofer.exe"),
      (b, "cmdargs", 'cmdargs.exe'),
      (c, "updater", 'updater.exe'))

# EXCLUDE:
# shell32.dll is part of Windows
# a.binaries = [x for x in a.binaries if not x[0].startswith("shell32")]

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='woofer.exe',
          debug=False,
          strip=None,
          upx=False,
          console=False,
          icon=os.path.join("icons", "woofer.ico"))

pyzB = PYZ(b.pure)
exeB = EXE(pyzB,
          b.scripts,
          exclude_binaries=True,
          name='cmdargs.exe',
          debug=False,
          strip=None,
          upx=False,
          console=True,
          icon=os.path.join("icons", "cmdargs.ico"))

pyzC = PYZ(c.pure)
exeC = EXE(pyzC,
          c.scripts,
          exclude_binaries=True,
          name='updater.exe',
          debug=False,
          strip=None,
          upx=False,
          console=True,
          icon=os.path.join("icons", "cmdargs.ico"))


coll = COLLECT(exe, exeB, exeC,
               a.binaries,
               a.zipfiles,
               a.datas,
               c.binaries,
               strip=None,
               upx=True,
               name='woofer')