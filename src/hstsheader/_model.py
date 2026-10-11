"""The parsed form of a Strict-Transport-Security header and its error type."""

from __future__ import annotations

from dataclasses import dataclass


class HstsError(ValueError):
    """Raised when a header cannot be parsed or a value is not valid."""


@dataclass(frozen=True, slots=True)
class Hsts:
    """A Strict-Transport-Security policy: a max-age and two optional flags."""

    max_age: int
    include_subdomains: bool = False
    preload: bool = False
