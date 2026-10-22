"""Render a Strict-Transport-Security header value that cannot carry an injection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import overload

from ._chars import ascii_lower, is_sendable, is_token, quote, shorten
from ._model import Hsts, HstsError, recheck

_KNOWN = frozenset({"max-age", "includesubdomains", "preload"})


def _extension(name: object, value: object, seen: set[str]) -> str:
    if not isinstance(name, str):
        raise TypeError(f"extension names must be str, got {type(name).__name__}")
    # Check and write plain str copies: a str subclass could lie in __iter__ or __format__.
    name = str.__str__(name)
    shown = shorten(name)
    if not is_token(name):
        raise HstsError(f"extension name {shown!r} is not an HTTP token", code="build.name")
    key = ascii_lower(name)
    if key in _KNOWN:
        raise HstsError(
            f"{shown} is set by its own argument, not as an extension", code="build.name"
        )
    if key in seen:
        raise HstsError(f"extension {shown} is given twice", code="duplicate")
    seen.add(key)
    if value is None:
        return name
    if not isinstance(value, str):
        raise TypeError(f"extension {shown} needs a str value or None")
    value = str.__str__(value)
    if is_token(value):
        return f"{name}={value}"
    if not is_sendable(value):
        message = f"extension {shown} has a control or non-ASCII character in its value"
        raise HstsError(message, code="build.value")
    return f"{name}={quote(value)}"


@overload
def build(
    max_age: int,
    *,
    include_subdomains: bool | None = None,
    preload: bool | None = None,
    extensions: Mapping[str, str | None] | None = None,
) -> str: ...


@overload
def build(
    max_age: Hsts,
    *,
    include_subdomains: None = None,
    preload: None = None,
    extensions: Mapping[str, str | None] | None = None,
) -> str: ...


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
    A flag left as ``None`` is not given: ``False`` next to an ``int``; next to an
    :class:`Hsts` the flags come from it, and passing one raises ``TypeError`` (the
    overloads let a type checker report that too).
    ``extensions`` maps further directive names (HTTP tokens other than the three known
    ones) to a value, or to ``None`` for a valueless directive; values that are not
    tokens are written as quoted strings, and control or non-ASCII characters are
    refused, so the result is always one well-formed field value. Directives come out
    in a fixed order: max-age, includeSubDomains, preload, then the extensions.
    An :class:`Hsts` is checked again, so one that skipped its checks (a subclass, or
    fields changed by force) raises as :class:`Hsts` would. Arguments of the wrong type
    raise ``TypeError``; values a header cannot carry raise :class:`HstsError`.

    >>> from hstsheader import Hsts, build
    >>> build(63072000, include_subdomains=True, preload=True)
    'max-age=63072000; includeSubDomains; preload'
    >>> build(Hsts(600), extensions={"report-to": "default", "note": "a b"})
    'max-age=600; report-to=default; note="a b"'
    >>> build(600, extensions={"x": "line\\r\\nSet-Cookie: s=1"})
    Traceback (most recent call last):
    ...
    hstsheader.HstsError: extension x has a control or non-ASCII character in its value
    """
    if isinstance(max_age, Hsts):
        if include_subdomains is not None or preload is not None:
            raise TypeError("pass the flags on the Hsts object, not as arguments")
        policy = recheck(max_age)
    else:
        policy = Hsts(
            max_age,
            include_subdomains=False if include_subdomains is None else include_subdomains,
            preload=False if preload is None else preload,
        )
    parts = [f"max-age={policy.max_age}"]
    if policy.include_subdomains:
        parts.append("includeSubDomains")
    if policy.preload:
        parts.append("preload")
    if extensions is not None and not isinstance(extensions, Mapping):
        raise TypeError("extensions must be a mapping of name to value")
    seen: set[str] = set()
    for name, value in (extensions or {}).items():
        parts.append(_extension(name, value, seen))
    return "; ".join(parts)
