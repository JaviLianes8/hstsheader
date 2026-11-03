"""Contracts added after the second round of independent QA for 1.0.0.

The preload test failed on 98e3f77, the commit the reviewers checked. The others pin
behaviour that was already right there but that a mutant could change without any test
noticing.
"""

from __future__ import annotations

import pytest

from hstsheader import is_preloadable, lint, parse, preload_issues
from hstsheader._head import field_lines

TAIL = "HTTP/1.1 200 OK\r\nStrict-Transport-Security: max-age=2\r\n"


def _found(value: str) -> list[tuple[str, int | None]]:
    return [(issue.code, issue.offset) for issue in lint(value)]


@pytest.mark.parametrize(
    "header",
    [
        "max-age=31536000; includeSubDomains; preload; preload=yes",
        "max-age=315360001;;INCLUDESUBDOMAINS;;preload=1 ;preload;",
        '\tmax-age=31536000; ; preload ;preload="";includeSubDomains ',
    ],
)
def test_a_value_on_preload_next_to_a_bare_preload_is_only_a_warning(header: str) -> None:
    # The hstspreload.org checker raises header.parse.invalid.preload as a warning.
    found = [(i.code, i.severity) for i in preload_issues(header)]
    assert ("preload.invalid", "warning") in found
    assert is_preloadable(header)


def test_a_value_on_the_only_preload_still_fails_as_missing() -> None:
    found = preload_issues("max-age=63072000; includeSubDomains; preload=1")
    assert [(i.code, i.severity) for i in found] == [
        ("preload.invalid", "warning"),
        ("preload.missing", "error"),
    ]
    assert not is_preloadable("max-age=63072000; includeSubDomains; preload=1")


def test_the_preload_value_warning_says_the_value_is_ignored() -> None:
    (issue,) = lint("max-age=1; preload=1")
    assert issue.message == "preload with a value is not the preload directive and is ignored"


@pytest.mark.parametrize(
    "head", ["HTTP/1.1 200 Connection established\r\n\r\n", "HTTP/1.1 100 Continue\r\n\r\n"]
)
def test_a_head_of_interim_responses_only_has_no_field(head: str) -> None:
    assert field_lines(head) == []


@pytest.mark.parametrize("status", ["HTTP/1.1 110 X", "HTTP/1.1 199 Late", "HTTP/1.1 101 Up"])
def test_every_1xx_code_is_interim(status: str) -> None:
    assert field_lines(status + "\r\n\r\n" + TAIL) == ["max-age=2"]


@pytest.mark.parametrize("gap", ["  ", "\t", " \t "])
def test_space_or_tab_after_the_version_is_tolerated(gap: str) -> None:
    assert field_lines(f"HTTP/1.1{gap}100 Continue\r\n\r\n" + TAIL) == ["max-age=2"]


@pytest.mark.parametrize("status", ["1000", "1001", "1999"])
def test_a_four_digit_status_is_not_interim(status: str) -> None:
    head = f"HTTP/1.1 {status} X\nStrict-Transport-Security: max-age=1\n\n" + TAIL
    assert field_lines(head) == ["max-age=1"]


def test_two_broken_quoted_directives_in_a_row_are_both_reported() -> None:
    assert _found('a=b "x"; "y;z"; max-age=9') == [("syntax", 4), ("syntax", 9)]


# Round 7 (lens b, F1 and F2): a skipped string runs to its closing quote whatever it
# holds; until then an invalid quoted-pair or a control character ended it.
@pytest.mark.parametrize("pair", [chr(127), chr(256), chr(1)])
def test_an_invalid_quoted_pair_does_not_end_a_skipped_string(pair: str) -> None:
    value = 'a=b "x' + "\\" + pair + ';"; max-age=13'
    assert _found(value) == [("syntax", 4)]
    assert parse(value).max_age == 13


@pytest.mark.parametrize("char", [chr(1), chr(31), chr(127), chr(256)])
def test_a_control_character_does_not_end_a_skipped_string(char: str) -> None:
    value = 'a=b "x' + char + ';"; max-age=13'
    assert _found(value) == [("syntax", 4)]
    assert parse(value).max_age == 13
    # A ';' inside the skipped string never starts a directive.
    assert parse('a=b "x' + char + ';max-age=1;"; max-age=13').max_age == 13


@pytest.mark.parametrize("char", ["\x00", "\r", "\n"])
def test_the_skip_reads_cr_lf_and_nul_as_space(char: str) -> None:
    assert _found('a=b "' + char + ';x";max-age=7') == [("syntax", 4), ("control-character", 5)]
