# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
'''
These API functions have argument names referring to:

    dist:        canonical package name (e.g. 'numpy-1.6.2-py26_0')

    pkgs_dir:    the "packages directory" (e.g. '/opt/anaconda/pkgs' or
                 '/home/joe/envs/.pkgs')

    prefix:      the prefix of a particular environment, which may also
                 be the "default" environment (i.e. sys.prefix),
                 but is otherwise something like '/opt/anaconda/envs/foo',
                 or even any prefix, e.g. '/home/joe/myenv'
'''
from __future__ import print_function, division, absolute_import

import json
import os
from os.path import isdir, isfile, join


LINK_HARD = 1
LINK_SOFT = 2
LINK_COPY = 3
link_name_map = {
    LINK_HARD: 'hard-link',
    LINK_SOFT: 'soft-link',
    LINK_COPY: 'copy',
}


def fetched(pkgs_dir):
    if not isdir(pkgs_dir):
        return set()
    return set(fn[:-8] for fn in os.listdir(pkgs_dir)
               if fn.endswith('.tar.bz2'))


def is_fetched(pkgs_dir, dist):
    return isfile(join(pkgs_dir, dist + '.tar.bz2'))


def extracted(pkgs_dir):
    """
    return the (set of canonical names) of all extracted packages
    """
    if not isdir(pkgs_dir):
        return set()
    return set(dn for dn in os.listdir(pkgs_dir)
               if (isfile(join(pkgs_dir, dn, 'info', 'files')) and
                   isfile(join(pkgs_dir, dn, 'info', 'index.json'))))


def is_extracted(pkgs_dir, dist):
    return (isfile(join(pkgs_dir, dist, 'info', 'files')) and
            isfile(join(pkgs_dir, dist, 'info', 'index.json')))


def linked_data(prefix):
    """
    Return a dictionary of the linked packages in prefix.
    """
    res = {}
    meta_dir = join(prefix, 'conda-meta')
    if isdir(meta_dir):
        for fn in os.listdir(meta_dir):
            if fn.endswith('.json'):
                try:
                    res[fn[:-5]] = json.load(open(join(meta_dir,fn)))
                except IOError:
                    pass
    return res


def linked(prefix):
    """
    Return the (set of canonical names) of linked packages in prefix.
    """
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        return set()
    return set(fn[:-5] for fn in os.listdir(meta_dir) if fn.endswith('.json'))


def is_linked(prefix, dist):
    """
    Return the install meta-data for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    meta_path = join(prefix, 'conda-meta', dist + '.json')
    try:
        with open(meta_path) as fi:
            info = json.load(fi)
            # TODO: see if info corresponds to dist
            return True
    except IOError:
        return False
