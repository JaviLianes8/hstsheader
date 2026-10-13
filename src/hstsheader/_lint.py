"""Check a header value against RFC 6797 and collect what a reader can recover from it."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ._chars import DIGITS
from ._model import DELTA_SECONDS_MAX, Issue
from ._scan import Directive, scan

_VALUELESS = {"includesubdomains": "includeSubDomains", "preload": "preload"}


@dataclass(frozen=True, slots=True)
class Analysis:
    """Everything known about one header: findings plus the tolerant reading."""

    issues: tuple[Issue, ...]
    max_age: int | None
    include_subdomains: bool
    preload: bool
    quoted_max_age: bool

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


def _max_age(directive: Directive, issues: list[Issue]) -> int | None:
    value = directive.value
    if value is None:
        issues.append(Issue("max-age.no-value", "max-age needs a value", "error", directive.offset))
        return None
    offset = directive.value_offset
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
        message = "max-age is quoted; valid, but some checkers (hstspreload.org) refuse it"
        issues.append(Issue("max-age.quoted", message, "warning", offset))
    return seconds


def _first_field(value: str | Iterable[str]) -> tuple[str | None, int]:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError("pass the header as str; decode bytes with latin-1 first")
    if isinstance(value, str):
        return value, 1
    fields = list(value)
    for item in fields:
        if not isinstance(item, str):
            raise TypeError(f"field lines must be str, got {type(item).__name__}")
    return (fields[0] if fields else None), len(fields)


def analyse(value: str | Iterable[str]) -> Analysis:
    """Scan the first field line of ``value`` and judge each directive."""
    text, count = _first_field(value)
    if text is None:
        issue = Issue("field.missing", "no Strict-Transport-Security field", "error")
        return Analysis((issue,), None, False, False, False)
    found = scan(text)
    issues = list(found.issues)
    if count > 1:
        message = f"{count} field lines; a user agent processes only the first (RFC 6797 8.1)"
        issues.append(Issue("multiple-fields", message, "warning"))
    seen: set[str] = set()
    max_age: int | None = None
    flags = {key: False for key in _VALUELESS}
    quoted = False
    has_max_age = "max-age" in found.broken
    for directive in found.directives:
        if directive.key in seen:
            message = f"{directive.name} appears more than once; every directive must be unique"
            issues.append(Issue("duplicate", message, "error", directive.offset))
        seen.add(directive.key)
        if directive.key == "max-age":
            has_max_age = True
            seconds = _max_age(directive, issues)
            if max_age is None and seconds is not None:
                max_age, quoted = seconds, directive.quoted
        elif directive.key in _VALUELESS:
            if directive.value is not None:
                message = f"{_VALUELESS[directive.key]} takes no value"
                issues.append(Issue("value-not-allowed", message, "error", directive.offset))
            else:
                flags[directive.key] = True
        else:
            message = f"unknown directive {directive.name} is ignored"
            issues.append(Issue("unknown-directive", message, "warning", directive.offset))
    if not has_max_age:
        issues.append(Issue("max-age.missing", "max-age is required", "error"))
    if max_age == 0 and flags["includesubdomains"]:
        message = "max-age=0 removes the policy; includeSubDomains has no effect"
        issues.append(Issue("max-age.zero-subdomains", message, "warning"))
    issues.sort(key=lambda issue: (issue.offset is None, issue.offset or 0))
    return Analysis(tuple(issues), max_age, flags["includesubdomains"], flags["preload"], quoted)


def lint(value: str | Iterable[str]) -> tuple[Issue, ...]:
    """List every finding about a Strict-Transport-Security value, in field order.

    Pass one field value, or every field line of a response (only the first is
    processed, as RFC 6797 section 8.1 requires). Findings with severity ``error`` mean a
    conforming user agent ignores the header; an empty tuple means a clean header.
    """
    return analyse(value).issues
