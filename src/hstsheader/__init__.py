"""Parse and build the HTTP Strict-Transport-Security header, typed and zero-dependency."""

from __future__ import annotations

from ._build import build
from ._model import Hsts, HstsError
from ._parse import parse

__version__ = "0.1.0"

__all__ = ["Hsts", "HstsError", "build", "parse"]
