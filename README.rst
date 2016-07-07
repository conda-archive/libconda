libconda
--------

A library of `conda` code, base on `conda 4.0.10`.  This library was created
to allow `conda` to undergo more refactoring without breaking projects which
depend on `conda`.  These projects, which now depend on `libconda`,
are `constructor`', `cas-mirror`, as well as the Continuum Analytics
internal Anaconda distribution build system.

The main functionality this package provides is to allow importing the
following:`
```
from libconda.fetch import fetch_index, fetch_pkg
from libconda.resolve import Resolve
```

Another reason for using this package is the ability to install it into
any non-root conda environment.
This means that (for example) `constructor` can now be installed into
a non-root environment.
