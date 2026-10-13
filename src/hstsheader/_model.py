"""The parsed form of a Strict-Transport-Security header, its findings and its error type."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# RFC 9111 section 1.2.2: a delta-seconds value too large to represent is read as 2^31.
DELTA_SECONDS_MAX = 2147483648

# hstspreload.org: the header on the base domain needs a max-age of at least one year.
PRELOAD_MIN_MAX_AGE = 31536000

Severity = Literal["error", "warning"]


class HstsError(ValueError):
    """Raised when a header cannot be read or a value is not valid.

    ``code`` names the rule that failed (the same codes as :class:`Issue`) and
    ``offset`` is the index in the field value where it failed, when there is one.
    """

    def __init__(self, message: str, *, code: str = "invalid", offset: int | None = None) -> None:
        super().__init__(message if offset is None else f"{message} (at offset {offset})")
        self.code = code
        self.offset = offset


@dataclass(frozen=True, slots=True)
class Issue:
    """One finding about a header value.

    An ``error`` means a conforming user agent ignores the whole header; a ``warning``
    marks something legal that is likely a mistake or is refused by some checkers.
    """

    code: str
    message: str
    severity: Severity
    offset: int | None = None


def _check_flag(name: str, value: object) -> None:
    if not isinstance(value, bool):
        raise HstsError(f"{name} must be a bool, got {type(value).__name__}", code="type")


def check_max_age(value: object) -> int:
    """Return ``value`` when it is a valid max-age for a sender, else raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise HstsError("max_age must be an integer number of seconds", code="type")
    if value < 0:
        raise HstsError("max_age must not be negative", code="max-age.negative")
    if value > DELTA_SECONDS_MAX:
        raise HstsError(
            f"max_age must not exceed {DELTA_SECONDS_MAX}; recipients read larger values as that",
            code="max-age.too-large",
        )
    return value


@dataclass(frozen=True, slots=True)
class Hsts:
    """A Strict-Transport-Security policy: a max-age and two optional flags.

    The fields are checked on creation: ``max_age`` is an ``int`` from 0 to
    :data:`DELTA_SECONDS_MAX` and both flags are ``bool``.
    """

    max_age: int
    include_subdomains: bool = False
    preload: bool = False

    def __post_init__(self) -> None:
        check_max_age(self.max_age)
        _check_flag("include_subdomains", self.include_subdomains)
        _check_flag("preload", self.preload)
