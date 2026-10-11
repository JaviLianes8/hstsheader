"""Render a Strict-Transport-Security header value."""

from __future__ import annotations

from ._model import HstsError


def build(max_age: int, *, include_subdomains: bool = False, preload: bool = False) -> str:
    """Build a Strict-Transport-Security header value.

    ``max_age`` is required and must be a non-negative integer (seconds). The
    ``includeSubDomains`` and ``preload`` directives are appended when requested,
    in the canonical order.
    """
    if isinstance(max_age, bool) or not isinstance(max_age, int):
        raise HstsError("max_age must be an integer number of seconds")
    if max_age < 0:
        raise HstsError("max_age must not be negative")

    parts = [f"max-age={max_age}"]
    if include_subdomains:
        parts.append("includeSubDomains")
    if preload:
        parts.append("preload")
    return "; ".join(parts)
