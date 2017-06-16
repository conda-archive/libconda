# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

log = getLogger(__name__)

from ..compat import *  # NOQA


def ensure_binary(value):
    return value.encode('utf-8') if hasattr(value, 'encode') else value


def ensure_text_type(value):
    return value.decode('utf-8') if hasattr(value, 'decode') else value
