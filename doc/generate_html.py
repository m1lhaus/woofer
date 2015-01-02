#!/usr/bin/env python
# -*- coding: utf-8 -*

"""
Script finds (recursively) all Markdown files and generates HTML files with CSS to ./html folder in same store order.
Pandoc converter is required!
Pandoc: http://johnmacfarlane.net/pandoc/index.html
"""

__version__ = "$Id: generate_html.py 27 2014-12-29 23:31:56Z herbig $"

import os
import sys
import shutil
import time


def which(program):
    # apped .exe extension on Windows
    if os.name == 'nt' and not program.endswith('.exe'):
        program += ".exe"

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return ""


def get_pandoc_exe(command):
    print "Trying to find Pandoc executable in system PATH..."
    pandoc_exe = which(command)
    if not pandoc_exe:
        raise Exception("Pandoc executable not found in system PATH!")
    else:
        print "Pandoc executable found at:", pandoc_exe

    return pandoc_exe


def convert(md_file, html_file):
    print "Converting", md_file, "..."
    err_code = os.system(" ".join([pandoc_exe, md_file, '-f markdown -t html -s -o ', html_file, '-c',
                                   os.path.relpath(os.path.join(html_dir, 'style.css'), os.path.dirname(html_file))]))

    if err_code != 0:
        print >> sys.stderr, "Error when converting %s" % md_file


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    html_dir = os.path.join(root_dir, 'html')

    t0 = time.time()

    to_conversion = []
    pandoc_exe = get_pandoc_exe('pandoc')
    for root, subdirs, files in os.walk(root_dir):
        for ffile in files:
            if ffile.endswith(".md"):
                ffile = ffile.decode(sys.getfilesystemencoding())
                md_file = os.path.join(os.path.abspath(root), ffile)

                relative_path = os.path.abspath(root).replace(root_dir + os.sep, u"") if root != root_dir else ""
                tree_folder = os.path.join(root_dir, "html", relative_path)
                if not os.path.isdir(tree_folder):
                    os.makedirs(tree_folder)

                html_file = os.path.join(tree_folder, ffile[:-2] + u"html")
                to_conversion.append((md_file, html_file))

    # should be palatalized, i.e. by map() function
    for md_file, html_file in to_conversion:
        convert(md_file, html_file)

    print "Copping CSS file ... "
    shutil.copy2(os.path.join(root_dir, 'style.css'), html_dir)         # ship html with css

    t1 = time.time()

    # --------------

    print "-" * 20
    print u"Time elapsed:", round(t1 - t0, 4), u"sec"
    print u"Finished!"