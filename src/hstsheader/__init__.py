"""Parse, check and build the HTTP Strict-Transport-Security header, typed and zero-dependency."""

from __future__ import annotations

from ._build import build
from ._lint import lint
from ._model import DELTA_SECONDS_MAX, PRELOAD_MIN_MAX_AGE, Hsts, HstsError, Issue
from ._parse import parse
from ._preload import is_preloadable, preload_issues

__version__ = "0.2.0"

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
