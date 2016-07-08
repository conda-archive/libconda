# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import sys
import logging
from platform import machine
from os.path import abspath, expanduser, isfile, isdir, join

from libconda.compat import urlparse
from libconda.utils import memoized


log = logging.getLogger(__name__)
stderrlog = logging.getLogger('stderrlog')

default_python = '%d.%d' % sys.version_info[:2]
# CONDA_FORCE_32BIT should only be used when running conda-build (in order
# to build 32-bit packages on a 64-bit system).  We don't want to mention it
# in the documentation, because it can mess up a lot of things.
force_32bit = bool(int(os.getenv('CONDA_FORCE_32BIT', 0)))

# ----- operating system and architecture -----

_sys_map = {'linux2': 'linux', 'linux': 'linux',
            'darwin': 'osx', 'win32': 'win', 'openbsd5': 'openbsd'}
non_x86_linux_machines = {'armv6l', 'armv7l', 'ppc64le'}
platform = _sys_map.get(sys.platform, 'unknown')
bits = 8 * tuple.__itemsize__
if force_32bit:
    bits = 32

if platform == 'linux' and machine() in non_x86_linux_machines:
    arch_name = machine()
    subdir = 'linux-%s' % arch_name
else:
    arch_name = {64: 'x86_64', 32: 'x86'}[bits]
    subdir = '%s-%d' % (platform, bits)

# ----- rc file -----

DEFAULT_CHANNEL_ALIAS = 'https://conda.anaconda.org/'

ADD_BINSTAR_TOKEN = True

user_rc_path = abspath(expanduser('~/.condarc'))
sys_rc_path = join(sys.prefix, '.condarc')

def get_rc_path():
    path = os.getenv('CONDARC')
    if path == ' ':
        return None
    if path:
        return path
    for path in user_rc_path, sys_rc_path:
        if isfile(path):
            return path
    return None

rc_path = get_rc_path()

def load_condarc(path):
    if not path or not isfile(path):
        return {}
    import yaml

    with open(path) as f:
        return yaml.load(f) or {}

rc = load_condarc(rc_path)
sys_rc = load_condarc(sys_rc_path) if isfile(sys_rc_path) else {}

# ----- local directories -----

# root_dir should only be used for testing, which is why don't mention it in
# the documentation, to avoid confusion (it can really mess up a lot of
# things)
root_dir = abspath(expanduser(os.getenv('CONDA_ROOT',
                                        rc.get('root_dir', sys.prefix))))
root_env_name = 'root'

def _default_envs_dirs():
    return [join(root_dir, 'envs')]

def _pathsep_env(name):
    x = os.getenv(name)
    if x is None:
        return []
    res = []
    for path in x.split(os.pathsep):
        if path == 'DEFAULTS':
            for p in rc.get('envs_dirs') or _default_envs_dirs():
                res.append(p)
        else:
            res.append(path)
    return res

envs_dirs = [abspath(expanduser(path)) for path in (
        _pathsep_env('CONDA_ENVS_PATH') or
        rc.get('envs_dirs') or
        _default_envs_dirs()
        )]

def pkgs_dir_from_envs_dir(envs_dir):
    if abspath(envs_dir) == abspath(join(root_dir, 'envs')):
        return join(root_dir, 'pkgs32' if force_32bit else 'pkgs')
    else:
        return join(envs_dir, '.pkgs')

pkgs_dirs = [pkgs_dir_from_envs_dir(envs_dir) for envs_dir in envs_dirs]

# ----- default environment prefix -----

_default_env = os.getenv('CONDA_DEFAULT_ENV')
if _default_env in (None, root_env_name):
    default_prefix = root_dir
elif os.sep in _default_env:
    default_prefix = abspath(_default_env)
else:
    for envs_dir in envs_dirs:
        default_prefix = join(envs_dir, _default_env)
        if isdir(default_prefix):
            break
    else:
        default_prefix = join(envs_dirs[0], _default_env)

# ----- channels -----

# Note, get_default_urls() and get_rc_urls() return unnormalized urls.

def get_default_urls():
    if isfile(sys_rc_path):
        sys_rc = load_condarc(sys_rc_path)
        if 'default_channels' in sys_rc:
            return sys_rc['default_channels']

    return ['https://repo.continuum.io/pkgs/free',
            'https://repo.continuum.io/pkgs/pro']

def get_rc_urls():
    if rc.get('channels') is None:
        return []
    if 'system' in rc['channels']:
        raise RuntimeError("system cannot be used in .condarc")
    return rc['channels']

def is_url(url):
    return urlparse.urlparse(url).scheme != ""

@memoized
def binstar_channel_alias(channel_alias):
    if rc.get('add_anaconda_token',
              rc.get('add_binstar_token', ADD_BINSTAR_TOKEN)):
        try:
            from binstar_client.utils import get_binstar
            bs = get_binstar()
            channel_alias = bs.domain.replace("api", "conda")
            if not channel_alias.endswith('/'):
                channel_alias += '/'
            if bs.token:
                channel_alias += 't/%s/' % bs.token
        except ImportError:
            log.debug("Could not import binstar")
            pass
        except Exception as e:
            stderrlog.info("Warning: could not import binstar_client (%s)" %
                e)
    return channel_alias

channel_alias = rc.get('channel_alias', DEFAULT_CHANNEL_ALIAS)
if not sys_rc.get('allow_other_channels', True) and 'channel_alias' in sys_rc:
    channel_alias = sys_rc['channel_alias']

def normalize_urls(urls, platform=None):
    channel_alias = binstar_channel_alias(rc.get('channel_alias',
                                                 DEFAULT_CHANNEL_ALIAS))

    platform = platform or subdir
    newurls = []
    for url in urls:
        if url == "defaults":
            newurls.extend(normalize_urls(get_default_urls(),
                                          platform=platform))
        elif url == "system":
            if not rc_path:
                newurls.extend(normalize_urls(get_default_urls(),
                                              platform=platform))
            else:
                newurls.extend(normalize_urls(get_rc_urls(),
                                              platform=platform))
        elif not is_url(url):
            moreurls = normalize_urls([channel_alias+url], platform=platform)
            newurls.extend(moreurls)
        else:
            newurls.append('%s/%s/' % (url.rstrip('/'), platform))
            newurls.append('%s/noarch/' % url.rstrip('/'))
    return newurls

# ----- proxy -----

def get_proxy_servers():
    res = rc.get('proxy_servers') or {}
    if isinstance(res, dict):
        return res
    sys.exit("Error: proxy_servers setting not a mapping")

# ----- misc -----

# ssl_verify can be a boolean value or a filename string
ssl_verify = rc.get('ssl_verify', True)

try:
    track_features = set(rc['track_features'])
except KeyError:
    track_features = None
