"""
For compatibility between Python versions.
Taken mostly from six.py by Benjamin Peterson.
"""

import sys
import types
import os

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    input = input
    def lchmod(path, mode):
        try:
            os.chmod(path, mode, follow_symlinks=False)
        except (TypeError, NotImplementedError, SystemError):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not os.path.islink(path):
                os.chmod(path, mode)
    import configparser
    from io import StringIO
    import urllib.parse as urlparse
    from urllib.parse import quote as urllib_quote
    from itertools import zip_longest
    from math import log2, ceil
    from shlex import quote
    range = range
    zip = zip
else:
    import ConfigParser as configparser
    from cStringIO import StringIO
    import urlparse
    from urllib import quote as urllib_quote
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    input = raw_input
    try:
        lchmod = os.lchmod
    except AttributeError:
        def lchmod(path, mode):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not os.path.islink(path):
                os.chmod(path, mode)
    from itertools import izip_longest as zip_longest
    from math import log
    def log2(x):
        return log(x, 2)
    def ceil(x):
        from math import ceil
        return int(ceil(x))
    from pipes import quote

    # Modified from http://hg.python.org/cpython/file/3.3/Lib/tempfile.py. Don't
    # use the 3.4 one. It uses the new weakref.finalize feature.
    import shutil as _shutil
    import warnings as _warnings
    import os as _os
    from tempfile import mkdtemp
    range = xrange
    from itertools import izip as zip


if PY3:
    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)())

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)())

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)())

def get_http_value(u, key):
    if PY3:
        return u.headers.get(key)
    else:
        return u.info().getheader(key)
