import pytest

from hstsheader import Hsts, HstsError, parse


def test_parse_full_header() -> None:
    result = parse("max-age=31536000; includeSubDomains; preload")
    assert result == Hsts(max_age=31536000, include_subdomains=True, preload=True)


def test_parse_minimal_header() -> None:
    assert parse("max-age=0") == Hsts(max_age=0)


def test_flags_absent_default_to_false() -> None:
    result = parse("max-age=600")
    assert result.include_subdomains is False
    assert result.preload is False


def test_include_subdomains_present_without_preload() -> None:
    result = parse("max-age=600; includeSubDomains")
    assert result.include_subdomains is True
    assert result.preload is False


def test_directive_names_are_case_insensitive() -> None:
    result = parse("MAX-AGE=100; INCLUDESUBDOMAINS; PRELOAD")
    assert result == Hsts(max_age=100, include_subdomains=True, preload=True)


def test_mixed_case_directive_names() -> None:
    assert parse("Max-Age=5; IncludeSubDomains").include_subdomains is True


def test_quoted_max_age_value_is_accepted() -> None:
    assert parse('max-age="31536000"') == Hsts(max_age=31536000)


def test_tolerates_extra_whitespace_and_empty_directives() -> None:
    result = parse("  max-age = 600 ;; includeSubDomains ; ")
    assert result == Hsts(max_age=600, include_subdomains=True)


def test_unknown_directives_are_ignored() -> None:
    result = parse("max-age=600; something=else; preload")
    assert result == Hsts(max_age=600, preload=True)


def test_missing_max_age_raises() -> None:
    with pytest.raises(HstsError):
        parse("includeSubDomains; preload")


def test_non_integer_max_age_raises() -> None:
    with pytest.raises(HstsError):
        parse("max-age=soon")


def test_negative_max_age_raises() -> None:
    with pytest.raises(HstsError):
        parse("max-age=-1")


def test_max_age_without_value_raises() -> None:
    with pytest.raises(HstsError):
        parse("max-age; preload")
