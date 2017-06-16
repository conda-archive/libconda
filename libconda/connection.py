# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import cgi
import re
import json

import requests

import libconda

from email.utils import formatdate
from io import BytesIO
from logging import getLogger
from mimetypes import guess_type
from os import lstat
from tempfile import SpooledTemporaryFile

from requests.models import Response
from requests.structures import CaseInsensitiveDict

from libconda.common.compat import ensure_binary
from libconda.compat import urlparse
from libconda.config import get_proxy_servers, ssl_verify

RETRIES = 3

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')

# Modified from code in pip/download.py:

# Copyright (c) 2008-2014 The pip developers (see AUTHORS.txt file)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

class CondaSession(requests.Session):

    timeout = None

    def __init__(self, *args, **kwargs):
        retries = kwargs.pop('retries', RETRIES)

        super(CondaSession, self).__init__(*args, **kwargs)

        proxies = get_proxy_servers()
        if proxies:
            self.proxies = proxies

        # Configure retries
        if retries:
            http_adapter = requests.adapters.HTTPAdapter(max_retries=retries)
            self.mount("http://", http_adapter)
            self.mount("https://", http_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())

        self.headers['User-Agent'] = "libconda/%s %s" % (
                          libconda.__version__, self.headers['User-Agent'])

        self.verify = ssl_verify


class LocalFSAdapter(requests.adapters.BaseAdapter):

    def send(self, request, stream=None, timeout=None, verify=None, cert=None, proxies=None):
        pathname = url_to_path(request.url)

        resp = Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            stats = lstat(pathname)
        except (IOError, OSError) as exc:
            resp.status_code = 404
            message = {
                "error": "file does not exist",
                "path": pathname,
                "exception": repr(exc),
            }
            fh = SpooledTemporaryFile()
            fh.write(ensure_binary(json.dumps(message)))
            fh.seek(0)
            resp.raw = fh
            resp.close = resp.raw.close
        else:
            modified = formatdate(stats.st_mtime, usegmt=True)
            content_type = guess_type(pathname)[0] or "text/plain"
            resp.headers = CaseInsensitiveDict({
                "Content-Type": content_type,
                "Content-Length": stats.st_size,
                "Last-Modified": modified,
            })

            resp.raw = open(pathname, "rb")
            resp.close = resp.raw.close
        return resp

    def close(self):
        pass


def url_to_path(url):
    """
    Convert a file: URL to a path.
    """
    assert url.startswith('file:'), (
        "You can only turn file: urls into filenames (not %r)" % url)
    path = url[len('file:'):].lstrip('/')
    path = urlparse.unquote(path)
    if _url_drive_re.match(path):
        path = path[0] + ':' + path[2:]
    elif not path.startswith(r'\\'):
        # if not a Windows UNC path
        path = '/' + path
    return path

_url_drive_re = re.compile('^([a-z])[:|]', re.I)


def data_callback_factory(variable):
    '''Returns a callback suitable for use by the FTP library. This callback
    will repeatedly save data into the variable provided to this function. This
    variable should be a file-like structure.'''
    def callback(data):
        variable.write(data)
        return

    return callback


class AuthError(Exception):
    '''Denotes an error with authentication.'''
    pass

def build_text_response(request, data, code):
    '''Build a response for textual data.'''
    return build_response(request, data, code, 'ascii')

def build_binary_response(request, data, code):
    '''Build a response for data whose encoding is unknown.'''
    return build_response(request, data, code,  None)

def build_response(request, data, code, encoding):
    '''Builds a response object from the data returned by ftplib, using the
    specified encoding.'''
    response = requests.Response()

    response.encoding = encoding

    # Fill in some useful fields.
    response.raw = data
    response.url = request.url
    response.request = request
    response.status_code = int(code.split()[0])

    # Make sure to seek the file-like raw object back to the start.
    response.raw.seek(0)

    # Run the response hook.
    response = requests.hooks.dispatch_hook('response', request.hooks, response)
    return response

def parse_multipart_files(request):
    '''Given a prepared reqest, return a file-like object containing the
    original data. This is pretty hacky.'''
    # Start by grabbing the pdict.
    _, pdict = cgi.parse_header(request.headers['Content-Type'])

    # Now, wrap the multipart data in a BytesIO buffer. This is annoying.
    buf = BytesIO()
    buf.write(request.body)
    buf.seek(0)

    # Parse the data. Simply take the first file.
    data = cgi.parse_multipart(buf, pdict)
    _, filedata = data.popitem()
    buf.close()

    # Get a BytesIO now, and write the file into it.
    buf = BytesIO()
    buf.write(''.join(filedata))
    buf.seek(0)

    return buf

# Taken from urllib3 (actually
# https://github.com/shazow/urllib3/pull/394). Once it is fully upstreamed to
# requests.packages.urllib3 we can just use that.


def unparse_url(U):
    """
    Convert a :class:`.Url` into a url

    The input can be any iterable that gives ['scheme', 'auth', 'host',
    'port', 'path', 'query', 'fragment']. Unused items should be None.

    This function should more or less round-trip with :func:`.parse_url`. The
    returned url may not be exactly the same as the url inputted to
    :func:`.parse_url`, but it should be equivalent by the RFC (e.g., urls
    with a blank port).


    Example: ::

        >>> Url = parse_url('http://google.com/mail/')
        >>> unparse_url(Url)
        'http://google.com/mail/'
        >>> unparse_url(['http', 'username:password', 'host.com', 80,
        ... '/path', 'query', 'fragment'])
        'http://username:password@host.com:80/path?query#fragment'
    """
    scheme, auth, host, port, path, query, fragment = U
    url = ''

    # We use "is not None" we want things to happen with empty strings (or 0 port)
    if scheme is not None:
        url = scheme + '://'
    if auth is not None:
        url += auth + '@'
    if host is not None:
        url += host
    if port is not None:
        url += ':' + str(port)
    if path is not None:
        url += path
    if query is not None:
        url += '?' + query
    if fragment is not None:
        url += '#' + fragment

    return url
