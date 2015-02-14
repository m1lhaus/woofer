# Woofer player

<img height="100px" align="right" src="icons/app_icon.png">Woofer player is **free open-source cross-platform** music player that plays most multimedia files, CDs, DVDs and also various online streams *(future)*. Whole written in Python and Qt provides easy, reliable, and high quality playback thanks to **LibVLC library** developed by [VideoLAN community](http://www.videolan.org/vlc/libvlc.html "").

## Main features

- **Wide media support:** Woofer will play all audio what [VLC Media player](http://www.videolan.org/vlc/features.php?cat=audio "") can play.
- **Folder based:** Your music is not ordered by album or interpret name, but only by its folder structure (on disk).
- **Multi-platform:** Currently supports both Windows (XP and higher) and Linux (tested on Ubuntu distros).
- **Fully portable:** No installation needed. Woofer will play right from your pen drive. 
- more will be coming ...

## Cross-platform

Thanks to Python, Qt and LibVLC, Woofer is developed to run on multiple operating systems. **Windows, Linux and Mac OS** platforms are supported. Currently Woofer is being tested only on Windows and Linux distribution, because I don't have any Mac OS device to test and debug. 

<div align="center"><img style="max-width:100p;height:auto;" src="doc/img/woofer-mp.jpg"></div>

## Open-source

Most recent code is always available here on Github. Python code is readable, well documented and self-explanatory. Feel free to join or fork the project. Woofer is published under **GPL v2 license**.

**Used packages (Requirements):**

- [Python 2.7](https://www.python.org/downloads/)
- [PyQt4](http://www.riverbankcomputing.co.uk/software/pyqt/download) (Qt 4.8)
- [LibVLC Python wrapper](https://wiki.videolan.org/Python_bindings/)
- [PyInstaller](https://github.com/pyinstaller/pyinstaller/wiki) (only for build)
- Python packages - [Send2Trash](https://pypi.python.org/pypi/Send2Trash), [Python-XLib](http://python-xlib.sourceforge.net/) (only for Linux)

Woofer uses new PyQt4 API v2, so migration to PyQt5/Python3 is possible and quite easy. But, I will stick with Python 2.7 because there is no reliable bug-free alternative to PyInstaller for Python 3.

## Download

For Windows there are available binary distributions. On Linux you can run Woofer like any other Python application by `woofer.py`. Linux binary distribution will come later.

### Binaries

Latest binary version for Windows can be found in [release section](https://github.com/m1lhaus/woofer/releases). This is a standalone version, no other libraries or VLC is needed!

### Run from source

Refer to requirements for all needed packages to run Woofer. Both for Windows and Linux there are available suitable binaries (PyQt, etc.). No need to build anything from source. Unfortunately you also need VLC Media player installed (core libraries). Note that all these libraries are shipped with Woofer binary distribution.

Finally run `woofer.py` or `woofer.py --debug` in debug mode. 

###How to make standalone binary distribution (Windows)

To create standalone binary distribution, install all listed requirements packages. Make sure to install PyInstaller package and add binary to PATH. Before you run build script, you need to edit PyInstaller runtime hook for PyQt4, because PyInstaller doesn't consider setting PyQt (Sip) API to v2. So edit file at `%Python-dir%\Lib\site-packages\PyInstaller\loader\rthooks\pyi_rth_qt4plugins.py` and add these `setapi()` lines:

	...
	import sip
	# set PyQt API to v2
	sip.setapi('QDate', 2)
	sip.setapi('QDateTime', 2)
	sip.setapi('QString', 2)
	sip.setapi('QTextStream', 2)
	sip.setapi('QTime', 2)
	sip.setapi('QUrl', 2)
	sip.setapi('QVariant', 2) 
	...   

*Note that from now whenever PyInstaller will package any PyQt4 script, it will set API v2 as default!* 

You also need to provide VLC libraries to build standalone distribution. Woofer has been tested with VLC 2.1x libraries, but any newer version should be fine. Download and extract VLC Media player (ZIP package) to `.\libvlc` folder. Of course not all VLC files are needed. To delete unnecessary files, run Woofer. Woofer should now locate our local VLC binaries in `.\libvlc` folder and loads them into memory. Now all needed .dll files are held by operating system, so when you try to delete `.\libvlc` folder, only necessary files held by OS will remain (dirty but simple solution).

Now when you have all packages installed and LibVLC core libraries prepared, you can run `.\build\build_win.py` script. Result will be stored in `.\build\release` directory.

## Future work

- Linux binary distribution
- save/load playlists
- automatic application updates
- media streaming (live broadcasts)
