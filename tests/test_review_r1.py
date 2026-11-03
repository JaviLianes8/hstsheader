"""Contracts added after the first independent review for 1.0.0.

The library already read these heads this way; these tests pin it. In a response head the
whitespace around a field value and around a folded continuation line is SP and HTAB only
(RFC 9110 section 5.6.3, RFC 9112 section 5.2). Python's ``str.strip()`` with no argument
also removes VT, FF, the file, group, record and unit separators, NEL, the no-break space
and wider spaces; reading the head with it turned these hand-written heads into a clean,
preloadable header. Each character is kept in the value, so the header is rejected.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from hstsheader import lint
from hstsheader._cli import main
from hstsheader._head import field_lines, response_fields

SRC = str(Path(__file__).resolve().parents[1] / "src")
GOOD = "max-age=31536000; includeSubDomains; preload"
# The characters up to U+00FF that Python's str.strip() removes besides SP, HTAB, CR and
# LF (CR and LF end a line here); they reach the command line as single latin-1 octets.
# WIDE_SPACE samples two of the wider ones; tests/test_review_r2.py sweeps them all.
PY_SPACE = ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x1f", "\x85", "\xa0"]
WIDE_SPACE = [chr(0x2003), chr(0x3000)]


def folded(char: str) -> str:
    rest = f" {char}includeSubDomains; preload{char}"
    return f"HTTP/2 200\r\nstrict-transport-security: max-age=31536000;\r\n{rest}\r\n\r\n"


def edged(char: str) -> str:
    return f"HTTP/2 200\r\nstrict-transport-security: {char}{GOOD}{char}\r\n\r\n"


def led(char: str) -> str:
    return f"{char}\r\nHTTP/2 200\r\nstrict-transport-security: {GOOD}\r\n\r\n"


def _cli(*argv: str, stdin: bytes = b"") -> tuple[int, dict[str, object]]:
    done = subprocess.run(
        [sys.executable, "-m", "hstsheader", *argv],
        input=stdin,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": SRC},
        check=False,
    )
    return done.returncode, json.loads(done.stdout)


def _main(*argv: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, object]]:
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("char", PY_SPACE + WIDE_SPACE)
def test_a_folded_line_keeps_other_spaces_at_its_ends(char: str) -> None:
    value = f"max-age=31536000; {char}includeSubDomains; preload{char}"
    assert field_lines(folded(char)) == [value]
    assert response_fields(folded(char)) == [[value]]
    assert [i.code for i in lint(value)] == ["syntax", "syntax"]


@pytest.mark.parametrize("char", PY_SPACE + WIDE_SPACE)
def test_a_field_value_keeps_other_spaces_at_its_ends(char: str) -> None:
    value = f"{char}{GOOD}{char}"
    assert field_lines(edged(char)) == [value]
    assert response_fields(edged(char)) == [[value]]
    assert "syntax" in [i.code for i in lint(value)]


@pytest.mark.parametrize("char", PY_SPACE + WIDE_SPACE)
def test_a_first_line_of_other_spaces_is_not_empty(char: str) -> None:
    # The first line is neither a status line nor a field line: the input is a bare value.
    assert field_lines(led(char)) is None
    assert response_fields(led(char)) is None


@pytest.mark.parametrize("build", [folded, edged, led])
@pytest.mark.parametrize("char", PY_SPACE + WIDE_SPACE)
def test_the_command_rejects_heads_with_other_spaces(
    build: Callable[[str], str], char: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report = _main("--preload", build(char), capsys=capsys)
    assert (code, report["honoured"], report["preloadable"]) == (1, False, False)


@pytest.mark.parametrize("char", PY_SPACE)
def test_a_bare_value_keeps_other_spaces_at_its_ends(
    char: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report = _main("--preload", f"{char}{GOOD}{char}", capsys=capsys)
    assert (code, report["field"], report["preloadable"]) == (1, f"{char}{GOOD}{char}", False)


@pytest.mark.parametrize("build", [folded, edged, led])
@pytest.mark.parametrize("char", ["\x0c", "\x85", "\xa0"])
def test_standard_input_with_other_spaces_is_rejected(
    build: Callable[[str], str], char: str
) -> None:
    code, report = _cli("--preload", stdin=build(char).encode("latin-1"))
    assert (code, report["honoured"], report["preloadable"]) == (1, False, False)


def test_the_reviewed_heads_give_the_reviewed_fields() -> None:
    # The octets the reviewer piped, each with the field the real code reads.
    for head, field in (
        (folded("\xa0"), "max-age=31536000; \xa0includeSubDomains; preload\xa0"),
        (edged("\xa0").replace(f"{GOOD}\xa0", f"{GOOD}\x0b"), f"\xa0{GOOD}\x0b"),
    ):
        code, report = _cli("--preload", stdin=head.encode("latin-1"))
        assert (code, report["field"], report["preloadable"]) == (1, field, False)
    code, report = _cli("--preload", stdin=led("\x0c").encode("latin-1"))
    assert (code, report["preloadable"]) == (1, False)
    assert str(report["field"]).startswith("\x0c\r\nHTTP/2 200")
