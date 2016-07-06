"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""

from __future__ import print_function, division, absolute_import

from logging import getLogger

from libconda import config
from libconda.resolve import MatchSpec

log = getLogger(__name__)



def dist2spec3v(dist):
    name, version, unused_build = dist.rsplit('-', 2)
    return '%s %s*' % (name, version[:3])


def name_dist(dist):
    return dist.rsplit('-', 2)[0]


def add_defaults_to_specs(r, linked, specs):
    # TODO: This should use the pinning mechanism. But don't change the API:
    # cas uses it.
    if r.explicit(specs):
        return
    log.debug('H0 specs=%r' % specs)
    names_linked = {name_dist(dist): dist for dist in linked}
    names_ms = {MatchSpec(s).name: MatchSpec(s) for s in specs}

    for name, def_ver in [('python', config.default_python),
                          # Default version required, but only used for Python
                          ('lua', None)]:
        ms = names_ms.get(name)
        if ms and ms.strictness > 1:
            # if any of the specifications mention the Python/Numpy version,
            # we don't need to add the default spec
            log.debug('H1 %s' % name)
            continue

        any_depends_on = any(ms2.name == name
                             for spec in specs
                             for fn in r.find_matches(spec)
                             for ms2 in r.ms_depends(fn))
        log.debug('H2 %s %s' % (name, any_depends_on))

        if not any_depends_on and name not in names_ms:
            # if nothing depends on Python/Numpy AND the Python/Numpy is not
            # specified, we don't need to add the default spec
            log.debug('H2A %s' % name)
            continue

        if (any_depends_on and len(specs) >= 1 and
                MatchSpec(specs[0]).strictness == 3):
            # if something depends on Python/Numpy, but the spec is very
            # explicit, we also don't need to add the default spec
            log.debug('H2B %s' % name)
            continue

        if name in names_linked:
            # if Python/Numpy is already linked, we add that instead of the
            # default
            log.debug('H3 %s' % name)
            specs.append(dist2spec3v(names_linked[name]))
            continue

        if (name, def_ver) in [('python', '3.3'), ('python', '3.4'),
            ('python', '3.5')]:
            # Don't include Python 3 in the specs if this is the Python 3
            # version of conda.
            continue

        specs.append('%s %s*' % (name, def_ver))
    log.debug('HF specs=%r' % specs)
