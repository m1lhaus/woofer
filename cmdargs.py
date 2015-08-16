# -*- coding: utf-8 -*-
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

"""
This script is used as helper on Windows when Woofer is shipped as binary package (exe files).
On Windows, GUI apps has no stdout/stderr, so when app is being launched from console,
no help will be printed on -h/--help command. So when user executes woofer.exe with help arg,
this console application will open in new window and display help content.
"""

import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=u"Woofer player is free and open-source cross-platform music player.",
                                     add_help=False)
    parser.add_argument('input', nargs='?', type=str,
                        help='Media file path.')
    parser.add_argument('-d', "--debug", action='store_true',
                        help=u"debug/verbose mode")
    parser.add_argument('-h', "--help", action='store_true',
                        help=u"show this help message and exit")
    args = parser.parse_args()

    parser.print_help()
    raw_input(u"\n\nPress Enter to continue...")