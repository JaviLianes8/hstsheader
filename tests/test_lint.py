from __future__ import annotations

from hstsheader import Issue, lint


def _codes(header: str | list[str]) -> list[tuple[str, str, int | None]]:
    return [(issue.code, issue.severity, issue.offset) for issue in lint(header)]


def test_a_clean_header_has_no_findings() -> None:
    assert lint("max-age=31536000; includeSubDomains; preload") == ()


def test_findings_are_issue_objects_with_a_message() -> None:
    (issue,) = lint("max-age=1; x")
    assert isinstance(issue, Issue)
    assert issue == Issue("unknown-directive", issue.message, "warning", 11)
    assert "x" in issue.message


def test_warnings_flag_legal_but_doubtful_choices() -> None:
    assert _codes('max-age="0031536000"; ; foo') == [
        ("max-age.leading-zero", "warning", 8),
        ("max-age.quoted", "warning", 8),
        ("empty-directive", "warning", 22),
        ("unknown-directive", "warning", 24),
    ]


def test_a_capped_value_is_a_warning() -> None:
    assert _codes("max-age=99999999999") == [("max-age.capped", "warning", 8)]


def test_a_single_zero_is_not_a_leading_zero() -> None:
    assert lint("max-age=0") == ()


def test_zero_with_include_subdomains_is_flagged() -> None:
    assert _codes("max-age=0; includeSubDomains") == [("max-age.zero-subdomains", "warning", None)]
    assert lint("max-age=1; includeSubDomains") == ()


def test_more_than_one_field_line_is_flagged() -> None:
    assert _codes(["max-age=1", "max-age=2"]) == [("multiple-fields", "warning", None)]
    assert lint(["max-age=1"]) == ()


def test_every_repeat_is_reported_and_findings_follow_the_text() -> None:
    assert _codes("preload; max-age=1; preload; preload") == [
        ("duplicate", "error", 20),
        ("duplicate", "error", 29),
    ]


def test_cr_and_lf_are_each_reported_and_then_read_as_space() -> None:
    assert _codes("max-age=1;\r\n preload") == [
        ("control-character", "error", 10),
        ("control-character", "error", 11),
    ]


def test_an_empty_or_blank_value_only_misses_max_age() -> None:
    for header in ("", "  \t "):
        assert _codes(header) == [("max-age.missing", "error", None)]


def test_a_broken_max_age_is_not_also_reported_missing() -> None:
    assert [code for code, _, _ in _codes('max-age="1')] == ["syntax"]


def test_the_messages_quote_the_offending_character() -> None:
    issue = lint("max-age=1 ,x")[0]
    assert "','" in issue.message
    (control,) = [i for i in lint("max-age=1; x=\x7f") if i.code == "syntax"]
    assert "U+007F" in control.message


def test_exactly_two_to_the_31_is_not_capped() -> None:
    assert lint("max-age=2147483648") == ()


def test_non_ascii_characters_are_named_by_code_point() -> None:
    (issue,) = [i for i in lint("max-age=1; x=\u00e9") if i.code == "syntax"]
    assert "U+00E9" in issue.message
