"""Contracts added after the fourth round of independent QA for 1.0.0.

The hstspreload.org checker reads the header's octets as UTF-8. Headers here are written
as a latin-1 decode of those octets, the way the command line reads them, so "\\xc2\\xa0"
is one no-break space to the checker and a lone "\\xa0" is an invalid octet it keeps.
The expected verdicts are the checker's own, run on the same octets (see
test_oracle_hstspreload.py). Every test marked as such failed on 370723f.
"""

from __future__ import annotations

import pytest

from hstsheader import is_preloadable, preload_issues

GOOD = "max-age=31536000; includeSubDomains; preload"
NO_PRELOAD = "max-age=31536000; includeSubDomains"
# Go's unicode.IsSpace, which strings.TrimSpace uses, and the code points around it.
GO_SPACE = [*range(0x09, 0x0E), 0x20, 0x85, 0xA0, 0x1680, *range(0x2000, 0x200B)]
GO_SPACE += [0x2028, 0x2029, 0x202F, 0x205F, 0x3000]
NOT_GO_SPACE = [0x00, 0x08, 0x0E, 0x1F, 0x21, 0x84, 0x86, 0x9F, 0xA1, 0x167F, 0x1681]
NOT_GO_SPACE += [0x1FFF, 0x200B, 0x2027, 0x202A, 0x202E, 0x2030, 0x205E, 0x2060, 0x3001]
NOT_GO_SPACE += [0x180E, 0xFEFF]


def wire(code: int) -> str:
    """The UTF-8 octets of a code point, as a latin-1 decode shows them."""
    return chr(code).encode("utf-8").decode("latin-1")


def misread_at(header: str) -> list[int | None]:
    return [i.offset for i in preload_issues(header) if i.code == "preload.misread"]


def test_a_utf8_space_before_max_age_in_a_quote_is_misread() -> None:  # failed on 370723f
    header = f'{GOOD}; note="x;\xe2\x80\x80max-age=1"'
    assert misread_at(header) == [header.index("max-age=1")]
    assert not is_preloadable(header)


def test_a_utf8_no_break_space_before_max_age_is_misread() -> None:  # failed on 370723f
    header = f'{GOOD}; note="x;\xc2\xa0max-age"'
    assert misread_at(header) == [header.index('max-age"')]
    assert not is_preloadable(header)


def test_preload_between_utf8_ideographic_spaces_is_misread() -> None:  # failed on 370723f
    header = f'{NO_PRELOAD}; note="x;\xe3\x80\x80preload\xe3\x80\x80;y"'
    assert misread_at(header) == [header.index("preload")]
    found = [i for i in preload_issues(header) if i.code == "preload.misread"]
    assert "as preload" in found[0].message


def test_the_long_s_in_utf8_folds_to_s() -> None:  # failed on 370723f
    header = 'max-age=31536000; preload; note="x;include\xc5\xbfubDomain\xc5\xbf;y"'
    assert misread_at(header) == [header.index("include")]
    assert not is_preloadable(header)


def test_a_lone_no_break_space_octet_is_not_trimmed() -> None:  # failed on 370723f
    header = f'{GOOD}; note="x;\xa0max-age=1;y"'
    assert misread_at(header) == []
    assert is_preloadable(header)


def test_a_lone_next_line_octet_is_not_trimmed() -> None:  # failed on 370723f
    header = f'{NO_PRELOAD}; note="x;\x85preload;y"'
    assert [i.code for i in preload_issues(header)] == ["preload.missing"]


@pytest.mark.parametrize("code", GO_SPACE)
def test_every_go_space_in_utf8_is_trimmed(code: int) -> None:
    before = f'{NO_PRELOAD}; note="x;{wire(code)}preload;y"'
    assert misread_at(before) == [before.index("preload")]


# CR, LF, VT and FF break a quoted string, and the RFC reading then resumes at a name.
@pytest.mark.parametrize("code", [c for c in GO_SPACE if not 0x0A <= c <= 0x0D])
def test_every_go_space_in_utf8_is_trimmed_after_the_name(code: int) -> None:
    after = f'{NO_PRELOAD}; note="x;preload{wire(code)};y"'
    assert misread_at(after) == [after.index("preload")]


@pytest.mark.parametrize("code", NOT_GO_SPACE)
def test_a_code_point_next_to_the_go_spaces_is_kept(code: int) -> None:
    assert misread_at(f'{NO_PRELOAD}; note="x;{wire(code)}preload;y"') == []
    assert misread_at(f'{NO_PRELOAD}; note="x;preload{wire(code)};y"') == []


@pytest.mark.parametrize("octet", ["\x85", "\xa0", "\xc2", "\xe3\x80", "\xff"])
def test_an_octet_that_is_not_utf8_is_kept(octet: str) -> None:
    assert misread_at(f'{NO_PRELOAD}; note="x;{octet}preload{octet};y"') == []


@pytest.mark.parametrize("space", [" ", "\t", "  \t "])
def test_space_after_the_name_is_trimmed(space: str) -> None:
    header = f'{NO_PRELOAD}; note="x;preload{space};y"'
    assert misread_at(header) == [header.index("preload")]
    other = f'max-age=31536000; preload; note="x;includeSubDomains{space};y"'
    assert misread_at(other) == [other.index("include")]


@pytest.mark.parametrize("name", ["include\xc5\xbfubdomains", "includeSubDomain\xc5\xbf"])
def test_the_long_s_counts_as_s_outside_a_quote_too(name: str) -> None:
    header = f"max-age=31536000; preload; {name}"
    assert misread_at(header) == [header.index("include")]


def test_a_character_above_latin1_stands_for_its_utf8_octets() -> None:
    long_s = "max-age=31536000; preload; include\u017fubdomains"
    assert misread_at(long_s) == [long_s.index("include")]
    spaced = f'{NO_PRELOAD}; note="\u3000x;\u3000preload\u2000;y"'
    found = [i for i in preload_issues(spaced) if i.code == "preload.misread"]
    assert [i.offset for i in found] == [spaced.index("preload")]
    assert "'preload'" in found[0].message


def test_a_piece_ending_inside_a_run_above_latin1_is_quoted_whole() -> None:
    header = 'max-age=31536000; preload; note="x;includeSubDomain\u017f\u3000;y"'
    found = [i for i in preload_issues(header) if i.code == "preload.misread"]
    assert [i.offset for i in found] == [header.index("include")]
    assert repr("includeSubDomain\u017f") in found[0].message


def test_a_lone_surrogate_is_not_a_space() -> None:
    assert misread_at(f'{NO_PRELOAD}; note="x;\ud800preload;y"') == []


def test_invalid_utf8_after_max_age_still_reads_as_max_age() -> None:
    header = f'{GOOD}; note="x;max-age\xff;y"'
    assert misread_at(header) == [header.index("max-age\xff")]
