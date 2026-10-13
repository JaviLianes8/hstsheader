"""Check a header value against RFC 6797 and collect what a reader can recover from it."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ._chars import DIGITS
from ._model import DELTA_SECONDS_MAX, Issue
from ._scan import Directive, scan

_VALUELESS = {"includesubdomains": "includeSubDomains", "preload": "preload"}
# Chromium refuses a header only when these repeat; the preload checker only warns otherwise.
_HARD_REPEATS = frozenset({"max-age", "includesubdomains"})
# The hstspreload.org checker reads max-age as a 64-bit unsigned integer.
_UINT64_MAX = 2**64 - 1


@dataclass(frozen=True, slots=True)
class Analysis:
    """Everything known about one header: findings plus the tolerant reading.

    The ``max_age_*`` flags describe the max-age directive that was used.
    ``soft_repeats`` holds the offsets of repeated directives other than max-age and
    includeSubDomains: errors for RFC 6797, tolerated by Chromium and the preload checker.
    """

    issues: tuple[Issue, ...]
    max_age: int | None = None
    include_subdomains: bool = False
    preload: bool = False
    max_age_quoted: bool = False
    max_age_spaced: bool = False
    max_age_beyond_uint64: bool = False
    soft_repeats: frozenset[int] = frozenset()

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")


def delta_seconds(digits: str) -> tuple[int, bool]:
    """Read ASCII digits as seconds; values past 2^31 become 2^31 (flag set)."""
    significant = digits.lstrip("0") or "0"
    # Never convert a long digit string: int() refuses more than 4300 digits.
    if len(significant) > len(str(DELTA_SECONDS_MAX)):
        return DELTA_SECONDS_MAX, True
    value = int(significant)
    return (DELTA_SECONDS_MAX, True) if value > DELTA_SECONDS_MAX else (value, False)


def _beyond_uint64(digits: str) -> bool:
    significant = digits.lstrip("0")
    return len(significant) > len(str(_UINT64_MAX)) or int(significant or "0") > _UINT64_MAX


def _max_age(directive: Directive, issues: list[Issue]) -> int | None:
    value, offset = directive.value, directive.value_offset
    if value is None:
        issues.append(Issue("max-age.no-value", "max-age needs a value", "error", directive.offset))
        return None
    if not value or not all(char in DIGITS for char in value):
        message = f"max-age must be ASCII digits, got {value!r}"
        issues.append(Issue("max-age.not-digits", message, "error", offset))
        return None
    seconds, capped = delta_seconds(value)
    if len(value) > 1 and value[0] == "0":
        issues.append(
            Issue("max-age.leading-zero", "max-age has a leading zero", "warning", offset)
        )
    if capped:
        message = f"max-age is larger than {DELTA_SECONDS_MAX} and is read as that value"
        issues.append(Issue("max-age.capped", message, "warning", offset))
    if directive.quoted:
        message = "max-age is quoted; valid, but the hstspreload.org checker refuses it"
        issues.append(Issue("max-age.quoted", message, "warning", offset))
    if directive.spaced:
        message = "space around '=' in max-age; valid, but the hstspreload.org checker refuses it"
        issues.append(Issue("max-age.spaced", message, "warning", directive.offset))
    return seconds


def _first_field(value: str | Iterable[str]) -> tuple[str | None, int]:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError("pass the header as str; decode bytes with latin-1 first")
    if isinstance(value, str):
        return value, 1
    if isinstance(value, Mapping) or not isinstance(value, Iterable):
        raise TypeError(f"pass a str or a list of str, got {type(value).__name__}")
    fields = list(value)
    for item in fields:
        if not isinstance(item, str):
            raise TypeError(f"field lines must be str, got {type(item).__name__}")
    return (fields[0] if fields else None), len(fields)


def analyse(value: str | Iterable[str]) -> Analysis:
    """Scan the first field line of ``value`` and judge each directive."""
    text, count = _first_field(value)
    if text is None:
        return Analysis((Issue("field.missing", "no Strict-Transport-Security field", "error"),))
    found = scan(text)
    issues = list(found.issues)
    if count > 1:
        message = f"{count} field lines; a user agent processes only the first (RFC 6797 8.1)"
        issues.append(Issue("multiple-fields", message, "warning"))
    # Broken directives count for repeats too, in the order they appear.
    order: list[tuple[int, str, Directive | None]] = [
        (d.offset, d.key, d) for d in found.directives
    ]
    order += [(offset, key, None) for offset, key in found.broken]
    seen: set[str] = set()
    soft: set[int] = set()
    used: Directive | None = None
    max_age: int | None = None
    flags = {key: False for key in _VALUELESS}
    for offset, key, directive in sorted(order, key=lambda item: item[0]):
        if key in seen:
            name = directive.name if directive else key
            message = f"{name} appears more than once; every directive must be unique"
            issues.append(Issue("duplicate", message, "error", offset))
            if key not in _HARD_REPEATS:
                soft.add(offset)
        seen.add(key)
        if directive is None:
            continue
        if key == "max-age":
            seconds = _max_age(directive, issues)
            if max_age is None and seconds is not None:
                max_age, used = seconds, directive
        elif key in _VALUELESS:
            if directive.value is not None:
                message = f"{_VALUELESS[key]} takes no value"
                issues.append(Issue("value-not-allowed", message, "error", offset))
            else:
                flags[key] = True
        else:
            message = f"unknown directive {directive.name} is ignored"
            issues.append(Issue("unknown-directive", message, "warning", offset))
    if "max-age" not in seen:
        issues.append(Issue("max-age.missing", "max-age is required", "error"))
    if max_age == 0 and flags["includesubdomains"]:
        message = "max-age=0 removes the policy; includeSubDomains has no effect"
        issues.append(Issue("max-age.zero-subdomains", message, "warning"))
    issues.sort(key=lambda issue: (issue.offset is None, issue.offset or 0))
    return Analysis(
        tuple(issues),
        max_age,
        flags["includesubdomains"],
        flags["preload"],
        used is not None and used.quoted,
        used is not None and used.spaced,
        used is not None and _beyond_uint64(used.value or ""),
        frozenset(soft),
    )


def lint(value: str | Iterable[str]) -> tuple[Issue, ...]:
    """List every finding about a Strict-Transport-Security value, in field order.

    Pass one field value, or every field line of a response (only the first is
    processed, as RFC 6797 section 8.1 requires). Findings with severity ``error`` mean a
    user agent that follows RFC 6797 ignores the header; an empty tuple means a clean
    header. Chromium is more lenient in places (see the README).
    """
    return analyse(value).issues
