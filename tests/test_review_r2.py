"""Contracts added after the second independent review for 1.0.0.

Inside a field value the only whitespace is SP and HTAB (RFC 9110 section 5.6.3). Any
other character Python counts as blank (``str.isspace()``) cannot start a directive name
and is a ``syntax`` error wherever it stands, also when the value holds nothing else.
The library already read values this way; these tests pin every such character at every
place where the scanner skips or trims whitespace, so reading one as a space is caught.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hstsheader import HstsError, build, lint, parse, preload_issues
from hstsheader._cli import main

SRC = str(Path(__file__).resolve().parents[1] / "src")
# Every code point str.isspace() accepts besides SP and HTAB, and besides CR and LF, which
# are read as SP (RFC 9110 section 5.5). Computed, so no character is left out.
BLANK = [chr(c) for c in range(sys.maxunicode + 1) if chr(c).isspace() and chr(c) not in " \t\r\n"]
LATIN = [char for char in BLANK if ord(char) <= 0xFF]
NAMES = [f"U+{ord(char):04X}" for char in BLANK]
ALONE = [("syntax", 0), ("max-age.missing", None)]


def found(value: str) -> list[tuple[str, int | None]]:
    return [(issue.code, issue.offset) for issue in lint(value)]


def test_the_blank_set_holds_the_reported_characters() -> None:
    seen = [0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x1F, 0x85, 0xA0, 0x1680, 0x2003, 0x2028, 0x2029]
    for code in [*seen, 0x202F, 0x205F, 0x3000]:
        assert chr(code) in BLANK
    assert " " not in BLANK and "\t" not in BLANK


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_a_value_of_one_blank_character_is_a_syntax_error(char: str) -> None:
    assert found(char) == ALONE
    assert found(char * 3) == ALONE


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_a_blank_character_between_spaces_is_a_syntax_error(char: str) -> None:
    assert found(f" {char} ") == [("syntax", 1), ("max-age.missing", None)]
    assert found(f"\t \t{char}\t") == [("syntax", 3), ("max-age.missing", None)]


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_a_blank_character_is_not_skipped_as_whitespace(char: str) -> None:
    assert found(f"{char}max-age=1") == ALONE
    # A broken max-age is reported once, not also as missing.
    assert found(f"max-age{char}=1") == [("syntax", 7)]
    assert found(f"max-age={char}1") == [("syntax", 8)]
    assert found(f"max-age=1{char}") == [("syntax", 9)]
    assert found(f"max-age=1 {char} ; preload") == [("syntax", 10)]
    assert found(f"max-age=1;{char};preload") == [("syntax", 10)]


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_a_blank_character_in_a_quoted_string_follows_the_grammar(char: str) -> None:
    plain, paired = f'max-age=1; x="a{char}b"', f'max-age=1; x="a\\{char}b"'
    if 0x80 <= ord(char) <= 0xFF:
        # obs-text: allowed in a quoted string and after a backslash.
        assert found(plain) == found(paired) == [("unknown-directive", 11)]
    else:
        assert found(plain) == [("syntax", 15)]
        assert found(paired) == [("syntax", 16)]


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_a_blank_character_is_never_built(char: str) -> None:
    with pytest.raises(HstsError) as caught:
        build(5, extensions={"x": f"a{char}b"})
    assert caught.value.code == "build.value"


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_parsing_a_blank_value_reports_the_syntax_error(char: str) -> None:
    with pytest.raises(HstsError) as caught:
        parse(f" {char}", strict=True)
    assert (caught.value.code, caught.value.offset) == ("syntax", 1)
    with pytest.raises(HstsError) as missing:
        parse(char)
    assert missing.value.code == "max-age.missing"


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_the_preload_check_reports_the_syntax_error(char: str) -> None:
    codes = ["syntax", "max-age.missing", "preload.subdomains-missing", "preload.missing"]
    assert [issue.code for issue in preload_issues(char)] == codes
    assert preload_issues(f" {char} ")[0].offset == 1


def _codes(report: dict[str, object], key: str) -> list[tuple[object, object]]:
    items = report[key]
    assert isinstance(items, list)
    return [(item["code"], item["offset"]) for item in items]


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_the_command_reports_the_syntax_error(
    char: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--preload", char]) == 1
    report = json.loads(capsys.readouterr().out)
    assert (report["field"], report["honoured"], report["policy"]) == (char, False, None)
    assert _codes(report, "issues") == ALONE
    assert _codes(report, "preload_issues") == [
        ("preload.subdomains-missing", None),
        ("preload.missing", None),
    ]


def _run(argv: list[str], stdin: bytes = b"") -> tuple[int, dict[str, object]]:
    done = subprocess.run(
        [sys.executable, "-m", "hstsheader", *argv],
        input=stdin,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": SRC},
        check=False,
    )
    return done.returncode, json.loads(done.stdout)


@pytest.mark.parametrize("char", BLANK, ids=NAMES)
def test_the_command_reports_the_syntax_error_for_an_argument(char: str) -> None:
    # Spaces and tabs around a bare value are trimmed; the blank character is kept.
    code, report = _run([f" {char}\t"])
    assert (code, report["field"]) == (1, char)
    assert _codes(report, "issues") == ALONE


@pytest.mark.parametrize("char", LATIN, ids=[f"U+{ord(c):04X}" for c in LATIN])
def test_the_command_reports_the_syntax_error_for_standard_input(char: str) -> None:
    code, report = _run([], stdin=f"{char}\r\n".encode("latin-1"))
    assert (code, report["field"]) == (1, char)
    assert _codes(report, "issues") == ALONE
