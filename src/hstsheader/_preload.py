"""Check a header against the hstspreload.org submission requirements."""

from __future__ import annotations

from collections.abc import Iterable

from ._lint import Analysis, analyse
from ._model import PRELOAD_MIN_MAX_AGE, Hsts, Issue

# hstspreload.org warns above ten years of 365 days.
_TEN_YEARS = 10 * 365 * 86400


def _form_issues(analysis: Analysis) -> list[Issue]:
    """RFC errors, with repeats the site tolerates turned into warnings, plus its own rules."""
    issues = [
        Issue(i.code, i.message, "warning", i.offset)
        if i.code == "duplicate" and i.offset in analysis.soft_repeats
        else i
        for i in analysis.errors
    ]
    if analysis.max_age_quoted:
        message = "hstspreload.org does not accept a quoted max-age"
        issues.append(Issue("preload.max-age-quoted", message, "error"))
    if analysis.max_age_spaced:
        message = "hstspreload.org does not accept space around '=' in max-age"
        issues.append(Issue("preload.max-age-spaced", message, "error"))
    if analysis.max_age_beyond_uint64:
        message = "hstspreload.org cannot read a max-age above 2^64 - 1"
        issues.append(Issue("preload.max-age-unreadable", message, "error"))
    return issues


def preload_issues(header: Hsts | str | Iterable[str]) -> tuple[Issue, ...]:
    """List what keeps a header from the HSTS preload list.

    A header value is first checked against RFC 6797: its errors are included, except a
    repeated directive other than max-age and includeSubDomains, which Chromium and the
    site's checker tolerate and which comes back as a warning. An :class:`Hsts` is taken
    as already valid. Then the hstspreload.org rules apply: ``includeSubDomains`` and
    ``preload`` present, and a ``max-age`` of at least :data:`PRELOAD_MIN_MAX_AGE`,
    written the way the site's checker reads it (unquoted, no space around ``=``, at most
    2^64 - 1). A ``max-age`` above ten years is a warning. An empty tuple or warnings only
    means the header qualifies.

    >>> from hstsheader import Hsts, preload_issues
    >>> [i.code for i in preload_issues("max-age=86400; includeSubDomains")]
    ['preload.missing', 'preload.max-age-too-short']
    >>> preload_issues(Hsts(63072000, include_subdomains=True, preload=True))
    ()
    """
    if isinstance(header, Hsts):
        issues: list[Issue] = []
        max_age: int | None = header.max_age
        subdomains, preload = header.include_subdomains, header.preload
    else:
        analysis = analyse(header)
        issues = _form_issues(analysis)
        max_age = analysis.max_age
        subdomains, preload = analysis.include_subdomains, analysis.preload
    if not subdomains:
        message = "the includeSubDomains directive is required"
        issues.append(Issue("preload.subdomains-missing", message, "error"))
    if not preload:
        issues.append(Issue("preload.missing", "the preload directive is required", "error"))
    if max_age == 0:
        message = "max-age=0 asks for removal; use the hstspreload.org removal form instead"
        issues.append(Issue("preload.max-age-zero", message, "error"))
    elif max_age is not None and max_age < PRELOAD_MIN_MAX_AGE:
        message = f"max-age must be at least {PRELOAD_MIN_MAX_AGE} seconds (one year)"
        issues.append(Issue("preload.max-age-too-short", message, "error"))
    elif max_age is not None and max_age > _TEN_YEARS:
        message = "max-age is longer than ten years, an unusually long value"
        issues.append(Issue("preload.max-age-over-ten-years", message, "warning"))
    return tuple(issues)


def is_preloadable(header: Hsts | str | Iterable[str]) -> bool:
    """True when :func:`preload_issues` finds no error.

    >>> from hstsheader import is_preloadable
    >>> is_preloadable("max-age=63072000; includeSubDomains; preload")
    True
    >>> is_preloadable('max-age="63072000"; includeSubDomains; preload')
    False
    """
    return not any(issue.severity == "error" for issue in preload_issues(header))
