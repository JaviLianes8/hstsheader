"""Render a Strict-Transport-Security header value that cannot carry an injection."""

from __future__ import annotations

from collections.abc import Mapping

from ._chars import ascii_lower, is_sendable, is_token, quote
from ._model import Hsts, HstsError

_KNOWN = frozenset({"max-age", "includesubdomains", "preload"})


def _extension(name: object, value: object, seen: set[str]) -> str:
    if not isinstance(name, str) or not is_token(name):
        raise HstsError(f"extension name {name!r} is not an HTTP token", code="build.name")
    key = ascii_lower(name)
    if key in _KNOWN:
        raise HstsError(
            f"{name} is set by its own argument, not as an extension", code="build.name"
        )
    if key in seen:
        raise HstsError(f"extension {name} is given twice", code="duplicate")
    seen.add(key)
    if value is None:
        return name
    if not isinstance(value, str):
        raise HstsError(f"extension {name} needs a str value or None", code="type")
    if is_token(value):
        return f"{name}={value}"
    if not is_sendable(value):
        message = f"extension {name} has a control or non-ASCII character in its value"
        raise HstsError(message, code="build.value")
    return f"{name}={quote(value)}"


def build(
    max_age: int | Hsts,
    *,
    include_subdomains: bool | None = None,
    preload: bool | None = None,
    extensions: Mapping[str, str | None] | None = None,
) -> str:
    """Build a Strict-Transport-Security header value.

    Pass an :class:`Hsts`, or ``max_age`` (an ``int`` from 0 to
    :data:`DELTA_SECONDS_MAX`) with the ``include_subdomains`` and ``preload`` flags.
    ``extensions`` maps further directive names (HTTP tokens other than the three known
    ones) to a value, or to ``None`` for a valueless directive; values that are not
    tokens are written as quoted strings, and control or non-ASCII characters are
    refused, so the result is always one well-formed field value. Directives come out
    in a fixed order: max-age, includeSubDomains, preload, then the extensions.
    """
    if isinstance(max_age, Hsts):
        if include_subdomains is not None or preload is not None:
            raise TypeError("pass the flags on the Hsts object, not as arguments")
        policy = max_age
    else:
        policy = Hsts(
            max_age,
            False if include_subdomains is None else include_subdomains,
            False if preload is None else preload,
        )
    parts = [f"max-age={policy.max_age}"]
    if policy.include_subdomains:
        parts.append("includeSubDomains")
    if policy.preload:
        parts.append("preload")
    if extensions is not None and not isinstance(extensions, Mapping):
        raise HstsError("extensions must be a mapping of name to value", code="type")
    seen: set[str] = set()
    for name, value in (extensions or {}).items():
        parts.append(_extension(name, value, seen))
    return "; ".join(parts)
