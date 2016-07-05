from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
from os.path import isdir, join

from libconda import config
from libconda import install
from libconda.fetch import fetch_index
from libconda.compat import iteritems, itervalues
from libconda.resolve import Package, Resolve


def _name_fn(fn):
    assert fn.endswith('.tar.bz2')
    return install.name_dist(fn[:-8])

def _fn2spec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2)[:2])

def _fn2fullspec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2))


def get_index(channel_urls=(), prepend=True, platform=None,
              use_cache=False, unknown=False, offline=False,
              prefix=None):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.
    """
    channel_urls = config.normalize_urls(channel_urls, platform=platform)
    if prepend:
        channel_urls += config.get_channel_urls(platform=platform)
    if offline:
        channel_urls = [url for url in channel_urls if url.startswith('file:')]
    index = fetch_index(tuple(channel_urls), use_cache=use_cache,
                        unknown=unknown)
    if prefix:
        for dist, info in iteritems(install.linked_data(prefix)):
            fn = dist + '.tar.bz2'
            if fn not in index:
                # only if the package in not in the repodata, use local
                # conda-meta (with 'depends' defaulting to [])
                info.setdefault('depends', [])
                index[fn] = info
    return index


def get_package_versions(package, offline=False):
    index = get_index(offline=offline)
    r = Resolve(index)
    return r.get_pkgs(package, emptyok=True)
