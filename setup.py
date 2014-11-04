# -*- coding: utf-8 -*-

# run script:
# python setup.py build

import subprocess
import sys
import os

from cx_Freeze import setup, Executable


VERSION = "0.7.0"       # todo: get this version from git

branch_name = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
target_dir = os.path.join("build", "woofer_v%s" % VERSION + branch_name)
icon_file = os.path.join("icons", "woofer.ico")

base = None
libEGL = ()
libVLC = ()
if sys.platform == "win32":
    base = "Win32GUI"

    libEGL = ((os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages", "PyQt5", "LibEGL.dll")), "LibEGL.dll")
    libVLC = (os.path.join("libvlc"), "libvlc")


options = {
    "build_exe": {
        "build_exe": target_dir,
        "includes": "atexit",
        "include_msvcr": True,
        "include_files": [libEGL, libVLC],
        "icon": icon_file
    }

}

executables = [
    Executable("woofer.py", base=base)
]

setup(name="Woofer player",
      version=VERSION,
      description="Něco",
      options=options,
      executables=executables, requires=['cx_Freeze']
)

