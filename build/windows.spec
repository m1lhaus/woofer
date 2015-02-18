# -*- mode: python -*-

a = Analysis(['woofer.py'],
             pathex=['build'])

b = Analysis(['cmdargs.py'],
             pathex=['build'])

MERGE((a, "woofer", "woofer.exe"),
      (b, "cmdargs", 'cmdargs.exe'))

# EXCLUDE:
# shell32.dll is part of Windows
a.binaries = [x for x in a.binaries if not x[0].startswith("shell32")]

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
          exclude_binaries=1,
          name='cmdargs.exe',
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