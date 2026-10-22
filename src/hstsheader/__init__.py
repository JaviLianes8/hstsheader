"""Parse, check and build the HTTP Strict-Transport-Security header, typed and zero-dependency.

``DELTA_SECONDS_MAX`` is the cap this library applies to ``max-age``: larger values are
read as it, and ``Hsts`` and ``build`` refuse them. RFC 6797 sets no ceiling; the value
follows RFC 9111 section 1.2.2, where a cache that cannot represent a larger delta-seconds
value uses 2^31. ``PRELOAD_MIN_MAX_AGE`` is the shortest ``max-age`` hstspreload.org
accepts (one year). ``Severity`` is the type of ``Issue.severity``.

>>> from hstsheader import DELTA_SECONDS_MAX, PRELOAD_MIN_MAX_AGE, Severity, lint, parse
>>> parse("max-age=99999999999").max_age == DELTA_SECONDS_MAX == 2**31
True
>>> PRELOAD_MIN_MAX_AGE == 365 * 24 * 60 * 60
True
>>> Severity
typing.Literal['error', 'warning']
>>> severity: Severity = lint("max-age=1; x")[0].severity
>>> severity
'warning'
"""

from __future__ import annotations

from ._build import build
from ._lint import lint
from ._model import DELTA_SECONDS_MAX, PRELOAD_MIN_MAX_AGE, Hsts, HstsError, Issue, Severity
from ._parse import parse
from ._preload import is_preloadable, preload_issues

__version__ = "1.0.0"

__all__ = [
    "DELTA_SECONDS_MAX",
    "PRELOAD_MIN_MAX_AGE",
    "Hsts",
    "HstsError",
    "Issue",
    "Severity",
    "build",
    "is_preloadable",
    "lint",
    "parse",
    "preload_issues",
]
