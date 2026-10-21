"""Contracts added after the third round of independent QA for 1.0.0.

The misread, unordered input, lazy input and blank line tests failed on 2fd8202, the
commit the reviewers checked. The others pin behaviour that was already right there but
that a mutant could change without any test noticing.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from hstsheader import Hsts, HstsError, build, is_preloadable, lint, parse, preload_issues
from hstsheader._head import response_fields

GOOD = "max-age=31536000; includeSubDomains; preload"


def _codes(header: str) -> list[tuple[str, str, int | None]]:
    return [(i.code, i.severity, i.offset) for i in preload_issues(header)]


def test_a_name_starting_with_max_age_is_misread_by_the_preload_checker() -> None:
    header = f"{GOOD}; max-agex=5"
    assert lint(header)[0].code == "unknown-directive"
    assert _codes(header) == [("preload.misread", "error", 46)]
    assert not is_preloadable(header)


@pytest.mark.parametrize("name", ["max-age-v2", "MAX-AGE-hint", "Max-Agefoo"])
def test_every_name_with_the_max_age_prefix_is_misread(name: str) -> None:
    assert not is_preloadable(f"{GOOD}; {name}")
    assert not is_preloadable(f"{name}=1; {GOOD}")


def test_a_semicolon_in_a_built_quoted_value_is_misread() -> None:
    policy = Hsts(31536000, include_subdomains=True, preload=True)
    header = build(policy, extensions={"report-uri": "https://r.example/c?a=1;max-age=2"})
    assert not any(issue.severity == "error" for issue in lint(header))
    assert _codes(header) == [("preload.misread", "error", header.index("max-age=2"))]


def test_directives_cut_out_of_a_quoted_string_are_misread() -> None:
    header = 'note="x;preload;includeSubDomains;y"; max-age=31536000'
    found = [i for i in preload_issues(header) if i.code == "preload.misread"]
    assert [i.offset for i in found] == [header.index("preload"), header.index("include")]
    assert "includeSubDomains" in found[1].message


@pytest.mark.parametrize("space", ["\xa0", "\x85", "\r\n ", " \t"])
def test_the_checker_trims_more_than_spaces_and_tabs(space: str) -> None:
    header = f'{GOOD}; note="a;{space}PRELOAD;b"'
    assert not any(i.severity == "error" for i in lint(header))
    assert [i.code for i in preload_issues(header)] == ["preload.misread"]


@pytest.mark.parametrize(
    "extra", ['report-uri="a;b"', 'x="a; preloadx"', 'x="1;includeSubDomainsY"', 'x=";"']
)
def test_a_semicolon_the_checker_reads_harmlessly_is_no_misread(extra: str) -> None:
    assert is_preloadable(f"{GOOD}; {extra}")


def test_a_broken_max_age_is_not_also_misread() -> None:
    assert "preload.misread" not in [i.code for i in preload_issues("max-age=1 2; x")]


def test_quoted_applies_only_to_the_max_age_that_was_used() -> None:
    first = 'max-age=400000000; includeSubDomains; preload; max-age="1"'
    assert [i.code for i in preload_issues(first)] == [
        "duplicate",
        "preload.max-age-over-ten-years",
    ]
    assert "preload.max-age-quoted" not in [i.code for i in preload_issues('max-age="a;b"')]


def test_spaced_applies_only_to_the_max_age_that_was_used() -> None:
    first = "max-age=400000000; includeSubDomains; preload; max-age = 1"
    assert [i.code for i in preload_issues(first)] == [
        "duplicate",
        "preload.max-age-over-ten-years",
    ]
    assert "preload.max-age-spaced" not in [i.code for i in preload_issues("max-age =1x")]


def test_field_missing_is_about_the_header_as_a_whole() -> None:
    assert [(i.code, i.offset) for i in lint([])] == [("field.missing", None)]
    with pytest.raises(HstsError) as caught:
        parse([])
    assert (caught.value.code, caught.value.offset) == ("field.missing", None)
    assert "offset" not in str(caught.value)
    assert [i.offset for i in preload_issues([]) if i.code == "field.missing"] == [None]


@pytest.mark.parametrize(
    "lines",
    [{"max-age=0", GOOD}, frozenset({"max-age=0"}), {"max-age=1": 1}.keys(), {GOOD: 1}.items()],
    ids=["set", "frozenset", "keys", "items"],
)
def test_unordered_collections_are_refused(lines: object) -> None:
    for reader in (parse, lint, preload_issues, is_preloadable):
        with pytest.raises(TypeError, match="order"):
            reader(lines)  # type: ignore[arg-type]


def test_dict_values_and_tuples_keep_their_order() -> None:
    assert parse({"a": "max-age=5", "b": "max-age=6"}.values()).max_age == 5
    assert parse(("max-age=7", "max-age=8")).max_age == 7


def _two_then_fail() -> Iterator[str]:
    yield "max-age=5"
    yield "max-age=6"
    raise AssertionError("a third field line was read")


def test_only_the_first_two_field_lines_are_read() -> None:
    assert parse(_two_then_fail()).max_age == 5
    assert [i.code for i in lint(_two_then_fail())] == ["multiple-fields"]
    assert "more than one" in lint(_two_then_fail())[0].message
    assert lint(iter(["max-age=1", "x", 5])) == lint(["max-age=1", "x"])  # type: ignore[arg-type]


def test_a_line_of_spaces_in_a_head_continues_the_field_line() -> None:
    head = "Strict-Transport-Security: max-age=1\r\n \r\n x"
    assert response_fields(head) == [["max-age=1  x"]]
    other = "HTTP/1.1 200 OK\r\nX-A: b\r\n \t\r\nStrict-Transport-Security: max-age=1\r\n"
    assert response_fields(other) == [["max-age=1"]]
    assert response_fields("HTTP/1.1 200 OK\r\nX-A: b\r\n\r\nStrict-Transport-Security: x") == [[]]


def test_none_flags_mean_not_given() -> None:
    assert build(1, include_subdomains=None, preload=None) == "max-age=1"
    assert build(Hsts(1, preload=True), include_subdomains=None, preload=None) == (
        "max-age=1; preload"
    )
    with pytest.raises(TypeError, match="on the Hsts object"):
        build(Hsts(1), preload=False)  # type: ignore[call-overload]


def test_flags_next_to_an_hsts_are_a_type_error_for_type_checkers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    api = pytest.importorskip("mypy.api")
    src = Path(__file__).resolve().parents[1] / "src"
    if src.is_dir():
        monkeypatch.setenv("MYPYPATH", str(src))
    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        "from hstsheader import Hsts, build\n"
        "build(Hsts(1), include_subdomains=True)\n"
        "build(Hsts(1), extensions={'a': None})\n"
        "build(1, include_subdomains=True, preload=None)\n",
        encoding="utf-8",
    )
    out, _, status = api.run(["--strict", "--cache-dir", str(tmp_path / "c"), str(consumer)])
    assert status == 1, out
    assert re.findall(r":(\d+): error:", out) == ["2"], out


def test_a_caller_made_error_has_the_documented_default_code() -> None:
    error = HstsError("made by the caller")
    assert (error.code, error.offset, str(error)) == ("invalid", None, "made by the caller")
