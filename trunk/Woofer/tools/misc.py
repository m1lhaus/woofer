# -*- coding: utf-8 -*-

"""
Various tools and functions
"""

__version__ = "$Id$"


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


def enumm(**enums):
    return type('Enum', (), enums)

Errors = enum('WARNING', 'SERIOUS', 'CRITICAL')
