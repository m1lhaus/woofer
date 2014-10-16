# -*- mode: python -*-
a = Analysis(['..\\woofer.py'],
             pathex=['d:\\Programovani\\Woofer-dev\\build'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

a.binaries = [x for x in a.binaries if not x[0].startswith("shell32")]		# shell32.dll is part of Windows

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='woofer.exe',
          debug=False,
          strip=None,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='woofer')