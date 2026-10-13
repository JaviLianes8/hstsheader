from __future__ import annotations

import pytest

from hstsheader import PRELOAD_MIN_MAX_AGE, Hsts, is_preloadable, preload_issues

GOOD = "max-age=31536000; includeSubDomains; preload"


def _codes(header: Hsts | str | list[str]) -> list[str]:
    return [issue.code for issue in preload_issues(header)]


def test_the_minimal_eligible_header_passes() -> None:
    assert preload_issues(GOOD) == ()
    assert is_preloadable(GOOD)
    assert is_preloadable(Hsts(PRELOAD_MIN_MAX_AGE, True, True))


def test_each_missing_flag_is_reported() -> None:
    assert _codes("max-age=31536000; preload") == ["preload.subdomains-missing"]
    assert _codes("max-age=31536000; includeSubDomains") == ["preload.missing"]
    assert _codes(Hsts(31536000)) == ["preload.subdomains-missing", "preload.missing"]


def test_one_second_short_of_a_year_fails() -> None:
    assert _codes(Hsts(PRELOAD_MIN_MAX_AGE - 1, True, True)) == ["preload.max-age-too-short"]
    assert not is_preloadable(Hsts(PRELOAD_MIN_MAX_AGE - 1, True, True))


def test_zero_points_to_the_removal_form() -> None:
    (issue,) = preload_issues(Hsts(0, True, True))
    assert issue.code == "preload.max-age-zero" and "removal" in issue.message


def test_more_than_ten_years_is_only_a_warning() -> None:
    ten_years = 10 * 365 * 86400
    assert preload_issues(Hsts(ten_years, True, True)) == ()
    (issue,) = preload_issues(Hsts(ten_years + 1, True, True))
    assert (issue.code, issue.severity) == ("preload.max-age-over-ten-years", "warning")
    assert is_preloadable(Hsts(ten_years + 1, True, True))


def test_a_quoted_max_age_is_refused_by_the_preload_checker() -> None:
    header = 'max-age="31536000"; includeSubDomains; preload'
    assert _codes(header) == ["preload.max-age-quoted"]
    assert not is_preloadable(header)


def test_rfc_errors_block_preloading() -> None:
    header = GOOD + "; includeSubDomains"
    assert _codes(header) == ["duplicate"]
    assert not is_preloadable(header)
    assert not is_preloadable(GOOD + "; max-age=31536000")
    assert _codes("includeSubDomains; preload") == ["max-age.missing"]


def test_a_repeated_preload_is_only_a_warning_as_on_the_site() -> None:
    for header in (GOOD + "; preload", GOOD + "; x; x"):
        (issue,) = preload_issues(header)
        assert (issue.code, issue.severity) == ("duplicate", "warning")
        assert is_preloadable(header)


def test_a_header_with_no_usable_max_age_lists_every_gap() -> None:
    assert _codes("") == ["max-age.missing", "preload.subdomains-missing", "preload.missing"]


@pytest.mark.parametrize("header", [[GOOD], [GOOD, "max-age=0"]])
def test_field_lines_are_accepted_and_the_first_one_counts(header: list[str]) -> None:
    assert is_preloadable(header)
    assert not is_preloadable(["max-age=0", GOOD])
