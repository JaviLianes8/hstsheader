"""Contracts added after the sixth round of independent QA for 1.0.0.

The library already read these headers as the checker does; these tests pin it. Every
code point outside ASCII is swept, so no member of Go's space set can be added or dropped
anywhere, and a misread piece between two runs of characters above U+00FF must map its
octets back to the right characters. As in test_qa_round5.py, "\\xc2\\xa0" is the UTF-8
octets of one no-break space seen through a latin-1 decode. The expected verdicts are the
checker's own on the same octets (see test_oracle_octets.py).
"""

from __future__ import annotations

import pytest
from conftest import NO_PRELOAD_NAMES, SWEEPS, sweep_headers

from hstsheader import is_preloadable, preload_issues
from hstsheader._checker import misreads as check

GOOD = "max-age=31536000; includeSubDomains; preload"
NO_PRELOAD = "max-age=31536000; includeSubDomains"
# Go's unicode.IsSpace outside ASCII, the code points strings.TrimSpace removes there.
WIDE_SPACE = {0x85, 0xA0, 0x1680, *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F}
WIDE_SPACE |= {0x3000}
WIDE = chr(0x3000)
HANGUL_FILLER = chr(0x3164)


def misreads(header: str) -> list[tuple[int | None, str]]:
    found = preload_issues(header)
    return [(i.offset, i.message) for i in found if i.code == "preload.misread"]


@pytest.mark.parametrize("kind", ["octets before", "octets after"])
def test_every_code_point_in_utf8_is_trimmed_exactly_when_go_trims_it(
    misread_sweep: dict[str, tuple[set[int], list[str]]], kind: str
) -> None:
    trimmed, stray = misread_sweep[kind]
    assert (sorted(trimmed), stray) == (sorted(WIDE_SPACE), [])


def test_every_character_above_latin1_is_trimmed_exactly_when_go_trims_it(
    misread_sweep: dict[str, tuple[set[int], list[str]]],
) -> None:
    # A character up to U+00FF is one octet, so 0x85 and 0xA0 alone are invalid UTF-8.
    trimmed, stray = misread_sweep["character before"]
    assert (sorted(trimmed), stray) == (sorted(WIDE_SPACE - {0x85, 0xA0}), [])


def test_the_hangul_filler_is_kept() -> None:
    # It renders blank but is not in Go's unicode.IsSpace.
    for form in ("\xe3\x85\xa4", HANGUL_FILLER):
        assert not misreads(f'{NO_PRELOAD}; note="x;{form}preload;y"')
    header = f'{GOOD}; note="x;\xe3\x85\xa4max-age=1;y"'
    assert preload_issues(header) == ()
    assert is_preloadable(header)


def test_a_misread_between_two_wide_runs_is_quoted_whole() -> None:
    header = f'{NO_PRELOAD}; note="{WIDE}x;\xc2\xa0preload;{WIDE}y"'
    found = misreads(header)
    assert [offset for offset, _ in found] == [header.index("preload")] == [48]
    assert found[0][1].endswith("reads 'preload' as preload")


def test_a_piece_between_two_wide_runs_is_not_misread() -> None:
    for header in (
        f'{NO_PRELOAD}; note="{WIDE * 5}x;preload;yy{WIDE}"',
        f'{NO_PRELOAD}; note="{WIDE * 5}x;preload;{WIDE}y"',
    ):
        assert misreads(header) == []


def test_preload_issues_reports_the_misreads_the_sweep_counts() -> None:
    # The sweep calls the misread check alone; these headers hold every Go space above
    # U+007F, and the last one the last code points.
    for kind in SWEEPS:
        headers = [header for header, _ in sweep_headers(kind)]
        for header in headers[:3] + headers[-1:]:
            found = [i for i in preload_issues(header) if i.code == "preload.misread"]
            assert found == check(header, NO_PRELOAD_NAMES)
