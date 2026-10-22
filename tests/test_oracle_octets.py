"""The hstspreload.org checker on headers with octets outside ASCII.

The checker reads the header's octets as UTF-8. These headers are written as a latin-1
decode of those octets, as the command line reads them, and the checker gets the octets
themselves (in hex), so a lone 0xA0 reaches it as an invalid octet, not as U+00A0. A
character above U+00FF reaches it as its UTF-8 octets, as preload_issues reads it.
Like test_oracle_hstspreload.py, they skip while HSTSHEADER_ORACLE is unset.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

import pytest
from conftest import NO_PRELOAD, SWEEPS, sweep_headers

from hstsheader import is_preloadable, lint, preload_issues

ORACLE = os.environ.get("HSTSHEADER_ORACLE", "")
pytestmark = pytest.mark.skipif(not ORACLE, reason="set HSTSHEADER_ORACLE to the built checker")

GOOD = "max-age=31536000; includeSubDomains; preload"
# Go's unicode.IsSpace and the code points around it, as UTF-8 octets.
CODES = [*range(0x08, 0x0F), 0x1F, 0x20, 0x21, 0x84, 0x85, 0x86, 0x9F, 0xA0, 0xA1, 0x167F]
CODES += [0x1680, 0x1681, 0x1FFF, *range(0x2000, 0x200C), 0x2027, 0x2028, 0x2029, 0x202A]
CODES += [0x202E, 0x202F, 0x2030, 0x205E, 0x205F, 0x2060, 0x2FFF, 0x3000, 0x3001]
CODES += [0x180E, 0xFEFF]
# Every code point to U+30FF but the surrogates, which UTF-8 cannot carry, and a few past it.
SWEEP = [c for c in range(0x3100) if not 0xD800 <= c < 0xE000]
SWEEP += [0xFEFF, 0xFFFD, 0x10000, 0x1F600, 0x10FFFF]
WIDE = chr(0x3000)
# Lone octets that are not UTF-8, which Go keeps.
LONE = ["\x85", "\xa0", "\xc2", "\xe3\x80", "\xff"]
# Each header, whether it is misread here, and the checker's preload, includeSubDomains
# and whether it finds no error.
CASES = [
    (f'{GOOD}; note="x;\xe2\x80\x80max-age=1"', True, True, True, False),
    (f'{GOOD}; note="x;\xc2\xa0max-age"', True, True, True, False),
    (f'{NO_PRELOAD}; note="x;\xe3\x80\x80preload\xe3\x80\x80;y"', True, True, True, True),
    (
        'max-age=31536000; preload; note="x;include\xc5\xbfubDomain\xc5\xbf;y"',
        True,
        True,
        True,
        True,
    ),
    (f'{GOOD}; note="x;\xa0max-age=1;y"', False, True, True, True),
    (f'{NO_PRELOAD}; note="x;\x85preload;y"', False, False, True, False),
    ("max-age=31536000; preload; include\xc5\xbfubdomains", True, True, True, True),
    (f'{NO_PRELOAD}; note="{WIDE}x;\xc2\xa0preload;y"', True, True, True, True),
    (f'{GOOD}; note="{WIDE}x;\xa0max-age=1;y"', False, True, True, True),
    # Runs above U+00FF on both sides of the piece.
    (f'{NO_PRELOAD}; note="{WIDE}x;\xc2\xa0preload;{WIDE}y"', True, True, True, True),
    (f'{NO_PRELOAD}; note="{WIDE * 5}x;preload;yy{WIDE}"', False, True, True, True),
    (f'{NO_PRELOAD}; note="{WIDE * 5}x;preload;{WIDE}y"', False, True, True, True),
    # U+3164, the hangul filler, renders blank but is not a space to Go.
    (f'{NO_PRELOAD}; note="x;\xe3\x85\xa4preload;y"', False, False, True, False),
    (f'{GOOD}; note="x;\xe3\x85\xa4max-age=1;y"', False, True, True, True),
]


def _wire(code: int) -> str:
    return chr(code).encode("utf-8").decode("latin-1")


def _octets(header: str) -> bytes:
    return b"".join(
        char.encode("latin-1") if char <= "\xff" else char.encode("utf-8") for char in header
    )


def _run(headers: list[str]) -> list[dict[str, Any]]:
    payload = json.dumps([_octets(header).hex() for header in headers]).encode()
    done = subprocess.run([ORACLE], input=payload, capture_output=True, check=True)
    verdicts: list[dict[str, Any]] = json.loads(done.stdout)
    assert len(verdicts) == len(headers)
    return verdicts


def _misread(header: str) -> bool:
    return any(issue.code == "preload.misread" for issue in preload_issues(header))


def test_a_misread_is_reported_exactly_where_the_checker_sees_preload() -> None:
    spaces = [_wire(code) for code in CODES] + LONE
    headers = [f'{NO_PRELOAD}; note="x;{space}preload;y"' for space in spaces]
    headers += [f'{NO_PRELOAD}; note="x;preload{space};y"' for space in spaces]
    for header, verdict in zip(headers, _run(headers), strict=True):
        if any(issue.severity == "error" for issue in lint(header)):
            continue  # a control character breaks the quote, and RFC 6797 reads names after it
        assert _misread(header) == verdict["preload"], header


def test_the_reported_cases_read_as_the_checker_reads_them() -> None:
    headers = [case[0] for case in CASES]
    for (header, misread, *expected), verdict in zip(CASES, _run(headers), strict=True):
        seen = [verdict["preload"], verdict["include_subdomains"], verdict["errors"] == []]
        assert (_misread(header), seen) == (misread, expected), header
        if is_preloadable(header):
            assert verdict["errors"] == [], header


def _quotable(form: str) -> bool:
    return all(char == "\t" or (" " <= char <= "\xff" and char != "\x7f") for char in form)


def test_every_code_point_is_trimmed_exactly_when_the_checker_trims_it() -> None:
    forms = [_wire(code) for code in SWEEP] + [chr(code) for code in SWEEP if code > 0x7F]
    latin1 = [chr(code) for code in range(0x100)] + [_wire(code) for code in range(0x80, 0x100)]
    headers = []
    # With a character above U+00FF after the quote, each one up to U+00FF is still one octet.
    for tail, probes in (("", forms), (f"; {WIDE}", latin1)):
        for form in probes:
            headers.append(f'{NO_PRELOAD}; note="x;{form}preload;y"{tail}')
            # Past the name, a character a quoted string cannot hold ends the quote, and
            # RFC 6797 then reads the name itself.
            if _quotable(form):
                headers.append(f'{NO_PRELOAD}; note="x;preload{form};y"{tail}')
    verdicts = _run(headers)
    wrong = [h for h, v in zip(headers, verdicts, strict=True) if _misread(h) != v["preload"]]
    assert wrong == []


def _checker_trims(kind: str) -> set[int]:
    """The code points of a sweep the checker trims, by halving each header it misreads."""
    _, write, before = SWEEPS[kind]

    def header(codes: list[int]) -> str:
        forms = [write(code) for code in codes]
        pieces = "".join(f";{form}preload" if before else f";preload{form}" for form in forms)
        return f'{NO_PRELOAD}; note="x{pieces};y"'

    pending = [list(where.values()) for _, where in sweep_headers(kind)]
    found: set[int] = set()
    while pending:
        verdicts = []
        for at in range(0, len(pending), 64):
            verdicts += _run([header(codes) for codes in pending[at : at + 64]])
        halves = []
        for codes, verdict in zip(pending, verdicts, strict=True):
            if verdict["preload"] and len(codes) == 1:
                found.add(codes[0])
            elif verdict["preload"]:
                halves += [codes[: len(codes) // 2], codes[len(codes) // 2 :]]
        pending = halves
    return found


def test_every_code_point_outside_ascii_is_trimmed_exactly_when_the_checker_trims_it(
    misread_sweep: dict[str, tuple[set[int], list[str]]],
) -> None:
    before = _checker_trims("octets before")
    after = _checker_trims("octets after")
    # A character above U+00FF reaches the checker as its UTF-8 octets, as in "octets before".
    expected: dict[str, tuple[set[int], list[str]]] = {
        "octets before": (before, []),
        "octets after": (after, []),
        "character before": ({code for code in before if code > 0xFF}, []),
    }
    assert misread_sweep == expected
