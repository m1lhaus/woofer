# -*- mode: python -*-

# #### include mydir in distribution #######
def extra_datas(mydir):
    def rec_glob(p, files):
        for d in glob.glob(p):
            if os.path.isfile(d):
                files.append(d)
            rec_glob("%s/*" % d, files)

    files = []
    if os.path.isfile(mydir):
        files.append(mydir)
    else:
        rec_glob("%s/*" % mydir, files)

    extra_datas = []
    for f in files:
        extra_datas.append((f, f, 'DATA'))

    return extra_datas

###########################################

a = Analysis(['woofer.py'],
             pathex=['build'])

b = Analysis(['cmdargs.py'],
             pathex=['build'])

MERGE((a, "woofer", "woofer.exe"),
      (b, "cmdargs", 'cmdargs.exe'))

a.binaries = [x for x in a.binaries if not x[0].startswith("shell32")]  # shell32.dll is part of Windows
a.datas += extra_datas('libvlc')
a.datas += extra_datas('LICENSE.txt')
a.datas += extra_datas('build.info')

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