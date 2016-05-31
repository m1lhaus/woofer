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

def check_binary_type(path):
    import struct
    bin_type = None
    IMAGE_FILE_MACHINE_I386 = 332
    IMAGE_FILE_MACHINE_IA64 = 512
    IMAGE_FILE_MACHINE_AMD64 = 34404

    with open(path, "rb") as f:
        s = f.read(2)
        if s != b"MZ":
            print("check_binary_type - Not an EXE file!")

        else:
            f.seek(60)
            s = f.read(4)
            header_offset = struct.unpack("<L", s)[0]
            f.seek(header_offset + 4)
            s = f.read(2)
            machine = struct.unpack("<H", s)[0]

            if machine == IMAGE_FILE_MACHINE_I386:
                return 32
            elif machine == IMAGE_FILE_MACHINE_IA64:
                return 64
            elif machine == IMAGE_FILE_MACHINE_AMD64:
                return 64
            else:
                raise Exception("Unknown binary type!")

# ---------------- find correct VLC folder ---------------------------
import os
import sys
if check_binary_type(sys.executable) == 32:
    VLC_PATH = os.path.abspath(os.path.join(".", "libvlc"))
else:
    VLC_PATH = os.path.abspath(os.path.join(".", "libvlc64"))
assert os.path.isdir(VLC_PATH)
assert os.path.isfile(os.path.join(VLC_PATH, "libvlc.dll"))
# ---------------------------------------------------------------------

woofer_app = Analysis(['../woofer.py'], pathex=[VLC_PATH], binaries=[(VLC_PATH, '.')])
cmdargs_app = Analysis(['../cmdargs.py'])
updater_app = Analysis(['../updater.py'])
reset_app = Analysis(['../reset_settings.py'])

MERGE((woofer_app, "woofer", "woofer.exe"),
      (cmdargs_app, "cmdargs", 'cmdargs.exe'),
      (updater_app, "updater", 'updater.exe'),
      (reset_app, "reset_settings", 'reset_settings.exe'))

# ---------------- EXCLUDE: ------------------------------
# skip Windows system binaries
# woofer_app.binaries = [x for x in woofer_app.binaries if not x[1].startswith(r"C:\Windows")]
# ---------------------------------------------------------

# # print binaries
# paths = sorted([lib[1] for lib in woofer_app.binaries])
# paths2 = sorted([lib[1] for lib in cmdargs_app.binaries])
# paths3 = sorted([lib[1] for lib in updater_app.binaries])
# print("\n".join(paths))
# print("----------------")
# print("\n".join(paths2))
# print("----------------")
# print("\n".join(paths3))


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

pyzD = PYZ(reset_app.pure)
exeD = EXE(pyzD,
           reset_app.scripts,
           exclude_binaries=True,
           name='reset_settings.exe',
           debug=False,
           strip=None,
           upx=False,
           console=True,
           icon=os.path.join("icons", "cmdargs.ico"))


coll = COLLECT(exe, exeB, exeC, exeD,
               woofer_app.binaries,
               woofer_app.zipfiles,
               woofer_app.datas,
               updater_app.binaries,
               strip=None,
               upx=True,
               name='woofer')
