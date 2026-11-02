"""The parsed form of a Strict-Transport-Security header, its findings and its error type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# This library's cap on max-age, by analogy with RFC 9111 section 1.2.2, where a cache that
# cannot represent a larger delta-seconds value uses 2^31 instead.
DELTA_SECONDS_MAX = 2147483648

# hstspreload.org: the header on the base domain needs a max-age of at least one year.
PRELOAD_MIN_MAX_AGE = 31536000

# Public as hstsheader.Severity, so the annotation of Issue.severity resolves there.
Severity = Literal["error", "warning"]


class HstsError(ValueError):
    """Raised when a header cannot be read or a value is not valid.

    ``code`` names the rule that failed (the same codes as :class:`Issue`, plus
    ``max-age.negative``, ``max-age.too-large``, ``build.name`` and ``build.value`` from
    :class:`Hsts` and :func:`build`) and ``offset`` is the index in the field value where
    it failed, or ``None``; as for :class:`Issue`, it can be the length of the value when
    the value ended too early. Library messages omit input names and values. Code
    that raises one itself calls ``HstsError(message, *, code="invalid", offset=None)``:
    ``invalid`` is only that default, never raised by this library, and an offset is
    appended to the message.

    >>> from hstsheader import HstsError, parse
    >>> try:
    ...     parse("max-age=10; max-age=20", strict=True)
    ... except HstsError as error:
    ...     print(error.code, error.offset)
    ...     print(error)
    duplicate 12
    a directive appears more than once; every directive must be unique (at offset 12)
    """

    __module__ = "hstsheader"

    def __init__(self, message: str, *, code: str = "invalid", offset: int | None = None) -> None:
        super().__init__(message if offset is None else f"{message} (at offset {offset})")
        self.code = code
        self.offset = offset

    def __reduce__(self) -> tuple[object, ...]:
        # Keep code and offset through pickle and copy; the message already holds the offset.
        return (type(self), (str(self),), {"code": self.code, "offset": self.offset})


@dataclass(frozen=True, slots=True)
class Issue:
    """One finding about a header value.

    ``code`` is stable and listed in the README; ``message`` is for people and may be
    reworded. Severity refers to the check that produced the finding: a :func:`lint`
    ``error`` means RFC 6797 rejects the header (quoted strings follow RFC 9110), while
    a :func:`preload_issues` ``error`` means it fails the preload header requirements.
    A ``warning`` does not fail that check. Preload checks downgrade duplicate directives
    other than max-age and includeSubDomains to warnings, even though RFC 6797 rejects
    them. A valid RFC header can still fail preload requirements. ``offset`` indexes the field
    value, or is ``None`` for a finding about the header as a whole. A ``syntax`` offset
    equal to the length of the value means it ended where more was needed, and one for an
    unterminated quoted string points at its opening quote.

    >>> from hstsheader import lint
    >>> lint("max-age=600; foo")
    (Issue(code='unknown-directive', message='unknown directive is ignored', severity='warning', offset=13),)
    """  # noqa: E501

    __module__ = "hstsheader"

    code: str
    message: str
    severity: Severity
    offset: int | None = None


def check_flag(name: str, value: object) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")


def check_max_age(value: object) -> int:
    """Return ``value`` as a plain int when it is a valid max-age for a sender, else raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("max_age must be an int")
    # Keep a plain int: an int subclass could render itself as anything in a header.
    value = int.__index__(value)
    if value < 0:
        raise HstsError("max_age must not be negative", code="max-age.negative")
    if value > DELTA_SECONDS_MAX:
        raise HstsError(
            f"max_age must not exceed {DELTA_SECONDS_MAX}, the cap this library applies",
            code="max-age.too-large",
        )
    return value


@dataclass(frozen=True, slots=True)
class Hsts:
    """A Strict-Transport-Security policy: a max-age and two optional flags.

    The two flags are keyword-only. The fields are checked on creation: ``max_age`` is an
    ``int`` from 0 to :data:`DELTA_SECONDS_MAX` (else :class:`HstsError`), and a field of
    the wrong type raises ``TypeError``. Instances are immutable, hashable and compare by
    value.

    >>> from hstsheader import Hsts
    >>> Hsts(31536000, include_subdomains=True)
    Hsts(max_age=31536000, include_subdomains=True, preload=False)
    >>> Hsts(-1)
    Traceback (most recent call last):
    ...
    hstsheader.HstsError: max_age must not be negative
    """

    __module__ = "hstsheader"

    max_age: int
    include_subdomains: bool = field(default=False, kw_only=True)
    preload: bool = field(default=False, kw_only=True)

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_age", check_max_age(self.max_age))
        check_flag("include_subdomains", self.include_subdomains)
        check_flag("preload", self.preload)


def recheck(policy: Hsts) -> Hsts:
    """A plain :class:`Hsts` made from ``policy``'s fields, so every check runs again.

    A subclass that skips ``__post_init__``, an instance changed with
    ``object.__setattr__`` or an object that claims to be an ``Hsts`` could otherwise
    carry any value into a header.
    """
    return Hsts(
        policy.max_age,
        include_subdomains=policy.include_subdomains,
        preload=policy.preload,
    )
