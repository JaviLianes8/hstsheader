"""Read a Strict-Transport-Security header value into an :class:`Hsts`."""

from __future__ import annotations

from ._model import Hsts, HstsError


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def parse(header: str) -> Hsts:
    """Parse a Strict-Transport-Security header value.

    Directive names are matched case-insensitively. Empty directives, surrounding
    whitespace and unknown directives are tolerated and ignored. ``max-age`` is
    required; a missing, repeated-conflicting or non-integer ``max-age`` raises
    :class:`HstsError`.
    """
    max_age: int | None = None
    include_subdomains = False
    preload = False

    for raw in header.split(";"):
        directive = raw.strip()
        if not directive:
            continue
        name, sep, value = directive.partition("=")
        key = name.strip().lower()
        if key == "max-age":
            if not sep:
                raise HstsError("max-age directive has no value")
            max_age = _parse_max_age(_unquote(value.strip()))
        elif key == "includesubdomains":
            include_subdomains = True
        elif key == "preload":
            preload = True

    if max_age is None:
        raise HstsError("max-age directive is required")
    return Hsts(max_age=max_age, include_subdomains=include_subdomains, preload=preload)


def _parse_max_age(value: str) -> int:
    if not value.isdigit():
        raise HstsError(f"max-age must be a non-negative integer, got {value!r}")
    return int(value)
