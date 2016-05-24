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

import os
import logging
import codecs
import configparser

import tools

logger = logging.getLogger(__name__)

tr = None


def init(lang_code=None):
    global tr
    tr = Translator(lang_code)
    return tr


class Translator:
    """
    Translator class which merges default EN language with custom translation.
    By given key is then returned translated string or default one if no translation is available.
    All language files must be encoded in UTF8 without BOM!
    """

    DEFAULT_LANG = "en_US"
    DEFAULT_ENCODING = "utf8"

    def __init__(self, lang_filename):
        """
        @param lang_filename: language code, i.e. en_US is default
        @type lang_filename: string
        """
        if not lang_filename:
            logger.debug("No language code given, default language used")
            lang_filename = Translator.DEFAULT_LANG

        self.default_langfile = os.path.join(tools.APP_ROOT_DIR, "lang", "en_US.ini")
        self.langfile = os.path.join(tools.APP_ROOT_DIR, "lang", lang_filename)
        self.parser = configparser.ConfigParser()

        # load default language
        if not os.path.isfile(self.default_langfile):
            raise Exception("Unable to locate default language file at '%s'" % self.default_langfile)
        try:
            with codecs.open(self.default_langfile, "r", Translator.DEFAULT_ENCODING) as f:
                self.parser.readfp(f)
        except Exception:
            logger.exception("Error when opening and parsing default language file '%s'", self.default_langfile)
            raise

        # load custom language
        filepath = self.langfile
        if not os.path.isfile(self.langfile):
            logger.error("Unable to locate language file '%s'. Falling back to default",  self.langfile)
            filepath = self.default_langfile
        if filepath != self.default_langfile:
            try:
                with codecs.open(filepath, "r", Translator.DEFAULT_ENCODING) as f:
                    self.parser.readfp(f)
            except Exception:
                logger.exception("Error when opening and parsing custom language file '%s'", filepath)
                raise

        if not self.parser.has_section("Main"):
            raise Exception("Wrong language file format. No 'Main' section found!")

        logger.debug("Translator initialised to '%s' language" % lang_filename)

    def __getitem__(self, key):
        """
        Returns translated string by given key.
        """
        try:
            string = self.parser.get("Main", key)
        except configparser.NoOptionError:
            logger.exception("Given key '%s' not found in translation strings!", key)
            raise

        return string
