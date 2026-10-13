"""Check a header against the hstspreload.org submission requirements."""

from __future__ import annotations

from collections.abc import Iterable

from ._lint import analyse
from ._model import PRELOAD_MIN_MAX_AGE, Hsts, Issue

# hstspreload.org warns above ten years of 365 days.
_TEN_YEARS = 10 * 365 * 86400


def preload_issues(header: Hsts | str | Iterable[str]) -> tuple[Issue, ...]:
    """List what keeps a header from the HSTS preload list.

    A header value is first checked against RFC 6797 (its errors are included, since a
    header that browsers ignore cannot be preloaded); an :class:`Hsts` is taken as
    already valid. Then the hstspreload.org rules apply: ``includeSubDomains`` and
    ``preload`` present, ``max-age`` of at least :data:`PRELOAD_MIN_MAX_AGE` and not
    quoted (the site's checker refuses quoted values). A ``max-age`` above ten years is a
    warning. An empty tuple or warnings only means the header qualifies.
    """
    if isinstance(header, Hsts):
        issues: list[Issue] = []
        max_age: int | None = header.max_age
        subdomains, preload, quoted = header.include_subdomains, header.preload, False
    else:
        analysis = analyse(header)
        issues = list(analysis.errors)
        max_age, quoted = analysis.max_age, analysis.quoted_max_age
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
    if quoted:
        message = "hstspreload.org does not accept a quoted max-age"
        issues.append(Issue("preload.max-age-quoted", message, "error"))
    return tuple(issues)


def is_preloadable(header: Hsts | str | Iterable[str]) -> bool:
    """True when :func:`preload_issues` finds no error."""
    return not any(issue.severity == "error" for issue in preload_issues(header))
