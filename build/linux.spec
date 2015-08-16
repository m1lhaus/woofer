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

a = Analysis(['woofer.py'],
             pathex=['build'])

b = Analysis(['cmdargs.py'],
             pathex=['build'])

MERGE((a, "woofer", "woofer"),
      (b, "cmdargs", 'cmdargs'))

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='woofer',
          debug=False,
          strip=None,
          upx=False,
          console=False,
          icon=os.path.join("icons", "woofer.ico"))

pyzB = PYZ(b.pure)
exeB = EXE(pyzB,
          b.scripts,
          exclude_binaries=1,
          name='cmdargs',
          debug=False,
          strip=None,
          upx=False,
          console=True,
          icon=os.path.join("icons", "cmdargs.ico"))


coll = COLLECT(exe, exeB,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='woofer')