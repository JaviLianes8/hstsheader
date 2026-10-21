"""Read a Strict-Transport-Security header value into an :class:`Hsts`."""

from __future__ import annotations

from collections.abc import Iterable

from ._lint import Analysis, analyse
from ._model import Hsts, HstsError, check_flag


def parse(header: str | Iterable[str], *, strict: bool = False) -> Hsts:
    """Parse a Strict-Transport-Security header value.

    ``header`` is one field value, or the field lines of a response in order (only the
    first is read, RFC 6797 section 8.1). Directive names match ASCII case-insensitively,
    whitespace around ``;`` and ``=`` is allowed, unknown directives are ignored and
    ``max-age`` may be quoted. Values above :data:`DELTA_SECONDS_MAX` are read as it.

    With ``strict=True`` the header must be one a conforming user agent honours: any
    finding of severity ``error`` from :func:`lint` raises :class:`HstsError` with its
    code and offset. By default the reader is tolerant: it skips broken directives, keeps
    the first valid ``max-age`` and raises only when no valid ``max-age`` is left.
    ``bytes`` or anything that is not text, and a ``strict`` that is not a ``bool``, raise
    ``TypeError``.

    >>> from hstsheader import parse
    >>> parse("max-age=31536000; includeSubDomains")
    Hsts(max_age=31536000, include_subdomains=True, preload=False)
    >>> parse(["max-age=600; preload", "max-age=0"]).max_age
    600
    >>> parse("max-age=600; preload=yes", strict=True)
    Hsts(max_age=600, include_subdomains=False, preload=False)
    >>> parse("max-age=600; includeSubDomains=yes", strict=True)
    Traceback (most recent call last):
    ...
    hstsheader.HstsError: includeSubDomains takes no value (at offset 13)
    """
    check_flag("strict", strict)
    analysis = analyse(header)
    if strict and analysis.errors:
        first = analysis.errors[0]
        raise HstsError(first.message, code=first.code, offset=first.offset)
    if analysis.max_age is None:
        raise _no_max_age(analysis)
    return Hsts(analysis.max_age, analysis.include_subdomains, analysis.preload)


def _no_max_age(analysis: Analysis) -> HstsError:
    """The error that explains why no max-age is usable."""
    found = analysis.errors
    reason = next((i for i in found if i.code.startswith(("max-age", "field"))), None)
    if reason is None:
        # No max-age finding, so a max-age directive broke the grammar: its syntax error is
        # the first one at or after its start (issues come sorted by offset).
        start = analysis.max_age_broken_at or 0
        reason = next(
            i for i in found if i.code == "syntax" and i.offset is not None and i.offset >= start
        )
    return HstsError(reason.message, code=reason.code, offset=reason.offset)
