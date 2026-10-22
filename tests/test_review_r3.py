"""Contracts added after the third independent review for 1.0.0.

tests/test_review_r1.py pins that characters other than SP and HTAB are kept when a head
is read. These tests pin the other side: SP and HTAB themselves. A first line made only of
them counts as empty, so the head after it is found; a folded line loses them at both
ends, also in the middle of a value; a line made only of them is a fold, not the end of
the head (RFC 9112 section 5.2). A line that starts with any other blank character is
neither a fold nor the end of the head. The library already read heads this way.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from hstsheader._cli import main
from hstsheader._head import field_lines, response_fields

SRC = str(Path(__file__).resolve().parents[1] / "src")
STS = "Strict-Transport-Security"
AGE = "max-age=31536000"
# A first line of SP and HTAB only, optionally followed by more blank lines.
LEAD = [" ", "  ", "\t", " \t ", "\t\t", " \r\n", "\t\r\n \r\n"]
LEAD_IDS = ["sp", "sp-sp", "tab", "sp-tab-sp", "tab-tab", "sp-then-empty", "tab-then-sp"]
OTHER = ["\x0b", "\x0c", "\x1c", "\x85", "\xa0"]
# Folded lines with SP and HTAB at their ends; each head gives FOLDED with "foo" at 38.
FOLDED = f"{AGE}; includeSubDomains ; foo"
FOLDS = {
    "trailing": " includeSubDomains \t\r\n ; foo",
    "both-ends": "\t \tincludeSubDomains \t \r\n\t; foo",
    "tab-led": "\tincludeSubDomains\t\r\n\t;\t\r\n foo",
}


def status_led(lead: str) -> str:
    return f"{lead}\r\nHTTP/1.1 200 OK\r\n{STS}: {AGE}\r\n\r\n"


def fields_led(lead: str) -> str:
    return f"{lead}\r\n{STS}: {AGE}\r\n\r\n"


def folded(rest: str) -> str:
    return f"HTTP/1.1 200 OK\r\n{STS}: {AGE};\r\n{rest}\r\n\r\n"


def _report(raw: dict[str, object]) -> tuple[object, list[tuple[object, object]]]:
    issues = raw["issues"]
    assert isinstance(issues, list)
    return raw["field"], [(issue["code"], issue["offset"]) for issue in issues]


def _main(text: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, object, list[object]]:
    code = main([text])
    field, issues = _report(json.loads(capsys.readouterr().out))
    return code, field, list(issues)


def _sub(*argv: str, stdin: bytes = b"") -> tuple[int, object, list[object]]:
    done = subprocess.run(
        [sys.executable, "-m", "hstsheader", *argv],
        input=stdin,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": SRC},
        check=False,
    )
    field, issues = _report(json.loads(done.stdout))
    return done.returncode, field, list(issues)


@pytest.mark.parametrize("lead", LEAD, ids=LEAD_IDS)
@pytest.mark.parametrize("build", [status_led, fields_led])
def test_a_first_line_of_spaces_and_tabs_is_empty(build: Callable[[str], str], lead: str) -> None:
    assert field_lines(build(lead)) == [AGE]
    assert response_fields(build(lead)) == [[AGE]]


@pytest.mark.parametrize("lead", LEAD, ids=LEAD_IDS)
@pytest.mark.parametrize("build", [status_led, fields_led])
def test_the_command_finds_the_head_after_a_line_of_spaces_and_tabs(
    build: Callable[[str], str], lead: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _main(build(lead), capsys) == (0, AGE, [])


@pytest.mark.parametrize("lead", [" ", "\t", " \t \r\n"])
def test_standard_input_and_arguments_skip_a_line_of_spaces_and_tabs(lead: str) -> None:
    for build in (status_led, fields_led):
        assert _sub(stdin=build(lead).encode("latin-1")) == (0, AGE, [])
        assert _sub(build(lead)) == (0, AGE, [])


def test_the_reviewed_heads_after_a_blank_line_give_the_field() -> None:
    assert _sub(stdin=status_led("  ").encode("latin-1")) == (0, AGE, [])
    assert _sub(stdin=fields_led("\t").encode("latin-1")) == (0, AGE, [])
    redirect = "HTTP/1.1 301 Moved\r\nLocation: x\r\n\r\nHTTP/1.1 200 OK\r\n"
    head = f" \r\n\r\n{redirect}{STS}: max-age=1\r\n\r\n"
    # The first final response (the redirect) has no field: exit status 1, field null.
    assert _sub(stdin=head.encode("latin-1")) == (1, None, [("field.missing", None)])


@pytest.mark.parametrize("rest", list(FOLDS.values()), ids=list(FOLDS))
def test_a_folded_line_loses_spaces_and_tabs_at_both_ends(rest: str) -> None:
    assert field_lines(folded(rest)) == [FOLDED]
    assert response_fields(folded(rest)) == [[FOLDED]]


@pytest.mark.parametrize("rest", list(FOLDS.values()), ids=list(FOLDS))
def test_the_command_reports_offsets_in_the_joined_value(
    rest: str, capsys: pytest.CaptureFixture[str]
) -> None:
    found = (0, FOLDED, [("unknown-directive", 38)])
    assert _main(folded(rest), capsys) == found
    assert _sub(folded(rest)) == found
    assert _sub(stdin=folded(rest).encode("latin-1")) == found


def test_the_reviewed_folded_head_gives_the_reviewed_field() -> None:
    raw = f"HTTP/1.1 200 OK\r\n{STS}: {AGE};\r\n includeSubDomains \t\r\n ; foo\r\n\r\n"
    done = subprocess.run(
        [sys.executable, "-m", "hstsheader", "--preload"],
        input=raw.encode("latin-1"),
        capture_output=True,
        env={**os.environ, "PYTHONPATH": SRC},
        check=False,
    )
    field, issues = _report(json.loads(done.stdout))
    assert (done.returncode, field) == (1, FOLDED)
    assert issues[0] == ("unknown-directive", 38)


@pytest.mark.parametrize("line", [" ", "\t", " \t "])
def test_a_line_of_spaces_and_tabs_is_a_fold_not_the_end(line: str) -> None:
    head = folded(f"{line}\r\n includeSubDomains")
    # The blank fold joins as one space: two spaces before includeSubDomains.
    assert field_lines(head) == [f"{AGE};  includeSubDomains"]
    assert response_fields(head) == [[f"{AGE};  includeSubDomains"]]


@pytest.mark.parametrize("char", OTHER)
def test_a_line_of_another_blank_character_does_not_end_the_head(char: str) -> None:
    head = f"HTTP/1.1 200 OK\r\nX: a\r\n{char}\r\n{STS}: {AGE}\r\n\r\n"
    assert field_lines(head) == [AGE]
    assert response_fields(head) == [[AGE]]


@pytest.mark.parametrize("char", OTHER)
def test_a_line_led_by_another_blank_character_is_not_a_fold(char: str) -> None:
    # It is a broken field line of its own, so it is not joined to the value.
    head = folded(f"{char}includeSubDomains")
    assert field_lines(head) == [f"{AGE};"]
    assert response_fields(head) == [[f"{AGE};"]]


def test_a_fold_right_after_the_status_line_has_nothing_to_join() -> None:
    head = f"HTTP/1.1 200 OK\r\n folded\r\n{STS}: {AGE}\r\n\r\n"
    assert field_lines(head) == [AGE]
    assert response_fields(head) == [[AGE]]
