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

# ---------------- find correct VLC folder ---------------------------
import os
import platform
PLATFORM = 32 if platform.architecture()[0] == '32bit' else 64
if PLATFORM == 32:
    VLC_PATH = os.path.abspath(os.path.join(".", "libvlc"))
else:
    VLC_PATH = os.path.abspath(os.path.join(".", "libvlc64"))
assert os.path.isdir(VLC_PATH)
assert os.path.isfile(os.path.join(VLC_PATH, "libvlc.dll"))
# ---------------------------------------------------------------------

woofer_app = Analysis(['../woofer.py'], pathex=[VLC_PATH], binaries=[(VLC_PATH, '.')])
cmdargs_app = Analysis(['../cmdargs.py'])
updater_app = Analysis(['../updater.py'])

MERGE((woofer_app, "woofer", "woofer.exe"),
      (cmdargs_app, "cmdargs", 'cmdargs.exe'),
      (updater_app, "updater", 'updater.exe'))

# ---------------- EXCLUDE: ------------------------------
# skip Windows system binaries
woofer_app.binaries = [x for x in woofer_app.binaries if not x[1].startswith(r"C:\Windows")]
# ---------------------------------------------------------

pyz = PYZ(woofer_app.pure)
exe = EXE(pyz,
          woofer_app.scripts,
          exclude_binaries=True,
          name='woofer.exe',
          debug=False,
          strip=None,
          upx=False,
          console=False,
          icon=os.path.join("icons", "woofer.ico"))

pyzB = PYZ(cmdargs_app.pure)
exeB = EXE(pyzB,
           cmdargs_app.scripts,
           exclude_binaries=True,
           name='cmdargs.exe',
           debug=False,
           strip=None,
           upx=False,
           console=True,
           icon=os.path.join("icons", "cmdargs.ico"))

pyzC = PYZ(updater_app.pure)
exeC = EXE(pyzC,
           updater_app.scripts,
           exclude_binaries=True,
           name='updater.exe',
           debug=False,
           strip=None,
           upx=False,
           console=True,
           icon=os.path.join("icons", "cmdargs.ico"))


coll = COLLECT(exe, exeB, exeC,
               woofer_app.binaries,
               woofer_app.zipfiles,
               woofer_app.datas,
               updater_app.binaries,
               strip=None,
               upx=True,
               name='woofer')
