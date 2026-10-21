"""Parse, check and build the HTTP Strict-Transport-Security header, typed and zero-dependency.

The two constants are the limits the sources set: ``DELTA_SECONDS_MAX`` is the ceiling
for ``max-age`` (RFC 9111 section 1.2.2, larger values are read as it) and
``PRELOAD_MIN_MAX_AGE`` the shortest ``max-age`` hstspreload.org accepts (one year).

>>> from hstsheader import DELTA_SECONDS_MAX, PRELOAD_MIN_MAX_AGE, parse
>>> parse("max-age=99999999999").max_age == DELTA_SECONDS_MAX == 2**31
True
>>> PRELOAD_MIN_MAX_AGE == 365 * 24 * 60 * 60
True
"""

from __future__ import annotations

from ._build import build
from ._lint import lint
from ._model import DELTA_SECONDS_MAX, PRELOAD_MIN_MAX_AGE, Hsts, HstsError, Issue
from ._parse import parse
from ._preload import is_preloadable, preload_issues

__version__ = "1.0.0"

__all__ = [
    "DELTA_SECONDS_MAX",
    "PRELOAD_MIN_MAX_AGE",
    "Hsts",
    "HstsError",
    "Issue",
    "build",
    "is_preloadable",
    "lint",
    "parse",
    "preload_issues",
]
