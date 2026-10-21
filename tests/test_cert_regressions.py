"""Behaviour fixed for 1.0.0; each test fails on 0.2.0."""

from __future__ import annotations

import pytest

import hstsheader
from hstsheader import HstsError, lint, parse, preload_issues
from hstsheader._cli import main


@pytest.mark.parametrize(
    "header",
    [
        'max-age="400000000"; includeSubDomains; preload',
        "max-age = 400000000; includeSubDomains; preload",
        "max-age=" + "9" * 25 + "; includeSubDomains; preload",
    ],
)
def test_no_ten_year_warning_where_the_site_cannot_read_max_age(header: str) -> None:
    codes = [issue.code for issue in preload_issues(header)]
    assert "preload.max-age-over-ten-years" not in codes
    assert any(code.startswith("preload.max-age-") for code in codes)


def test_the_ten_year_warning_stays_for_a_plain_max_age() -> None:
    found = preload_issues("max-age=315360001; includeSubDomains; preload")
    assert [(i.code, i.severity) for i in found] == [("preload.max-age-over-ten-years", "warning")]
    assert preload_issues("max-age=315360000; includeSubDomains; preload") == ()


def test_the_tolerant_error_names_the_broken_max_age() -> None:
    header = "x=1; x=2; preload=1; Max-Age="
    with pytest.raises(HstsError) as caught:
        parse(header)
    assert (caught.value.code, caught.value.offset) == ("syntax", len(header))
    assert "expected a value for Max-Age" in str(caught.value)
    with pytest.raises(HstsError) as early:
        parse('a b; max-age="1')
    # The unterminated quote of max-age, not the earlier "a b".
    assert (early.value.code, early.value.offset) == ("syntax", 13)


class _Odd(str):
    def __getitem__(self, index: object) -> str:
        return "\0"

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter("\0")


def test_a_str_subclass_is_read_as_its_text() -> None:
    assert parse(_Odd("max-age=5; preload")).preload is True
    assert parse([_Odd("max-age=6")]).max_age == 6
    assert lint(_Odd("max-age=1")) == ()


def test_messages_quote_at_most_forty_characters() -> None:
    name = "n" * 41
    (issue,) = [i for i in lint(f"max-age=1; {name}") if i.code == "unknown-directive"]
    assert issue.message == f"unknown directive {'n' * 40}... (41 characters) is ignored"
    (exact,) = [i for i in lint(f"max-age=1; {name[:40]}") if i.code == "unknown-directive"]
    assert exact.message == f"unknown directive {'n' * 40} is ignored"
    (digits,) = [i for i in lint("max-age=" + "9" * 40 + "x") if i.code == "max-age.not-digits"]
    assert digits.message == f"max-age must be ASCII digits, got {'9' * 40!r}... (41 characters)"


def test_version_option(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as done:
        main(["--version"])
    assert done.value.code == 0
    assert capsys.readouterr().out == f"hstsheader {hstsheader.__version__}\n"
