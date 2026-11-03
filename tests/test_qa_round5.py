"""Contracts added after the fifth round of independent QA for 1.0.0.

The library already read these headers as the checker does; these tests pin it, so a
wrong member of Go's space set or a wrong octet for a latin-1 character cannot pass. As in
test_qa_round4.py, "\\xc2\\xa0" is the UTF-8 octets of one no-break space seen through a
latin-1 decode, and a lone "\\xa0" is an invalid octet the checker keeps. The expected
verdicts are the checker's own on the same octets (see test_oracle_octets.py).
"""

from __future__ import annotations

from hstsheader import preload_issues

GOOD = "max-age=31536000; includeSubDomains; preload"
NO_PRELOAD = "max-age=31536000; includeSubDomains"
# Go's unicode.IsSpace, the set strings.TrimSpace removes.
GO_SPACE = {*range(0x09, 0x0E), 0x20, 0x85, 0xA0, 0x1680, *range(0x2000, 0x200B)}
GO_SPACE |= {0x2028, 0x2029, 0x202F, 0x205F, 0x3000}
# Every code point to U+30FF, then the byte order mark, the replacement character and a
# few beyond the basic plane: past U+3000 nothing more is in the set.
SWEEP = [*range(0x3100), 0xFEFF, 0xFFFD, 0x10000, 0x1F600, 0x10FFFF]
WIDE = chr(0x3000)
# A last piece above latin-1, after the quote so that RFC 6797 reads the quote whole.
WIDE_TAIL = f"; {WIDE}"


def wire(code: int) -> str:
    """The UTF-8 octets of a code point, as a latin-1 decode shows them."""
    return chr(code).encode("utf-8", "surrogatepass").decode("latin-1")


def misread(header: str) -> bool:
    return any(issue.code == "preload.misread" for issue in preload_issues(header))


def wrong_reads(form: str, trimmed: bool, suffix: str = "") -> list[str]:
    """The headers, before and after the name, whose misread verdict is not ``trimmed``."""
    wrong = []
    for piece in (f"{form}preload", f"preload{form}"):
        header = f'{NO_PRELOAD}; note="x;{piece};y"{suffix}'
        if piece.startswith("preload") and not quotable(form):
            continue  # it ends the quote, and RFC 6797 reads the name before it
        if misread(header) != (trimmed or form == ";"):
            wrong.append(header)
    return wrong


def quotable(form: str) -> bool:
    """Whether RFC 6797 allows every character of ``form`` in a quoted string."""
    return all(char == "\t" or (" " <= char <= "\xff" and char != "\x7f") for char in form)


def test_exactly_go_spaces_in_utf8_are_trimmed() -> None:
    wrong = [h for c in SWEEP for h in wrong_reads(wire(c), c in GO_SPACE)]
    assert wrong == []


def test_exactly_go_spaces_outside_latin1_are_trimmed_as_characters() -> None:
    # A character up to U+00FF is one octet, so 0x85 and 0xA0 alone are invalid UTF-8.
    trimmed = GO_SPACE - {0x85, 0xA0}
    assert [h for c in SWEEP for h in wrong_reads(chr(c), c in trimmed)] == []


def test_the_mongolian_vowel_separator_and_the_bom_are_kept() -> None:
    for code in (0x180E, 0xFEFF):
        for form in (wire(code), chr(code)):
            assert not misread(f'{NO_PRELOAD}; note="x;{form}preload;y"')
            assert not misread(f'{NO_PRELOAD}; note="x;preload{form};y"')
    header = f'{GOOD}; note="x;\xef\xbb\xbfmax-age=1;y"'
    assert not preload_issues(header)


def test_a_wide_character_keeps_latin1_characters_as_single_octets() -> None:
    codes = range(0x100)
    assert [h for c in codes for h in wrong_reads(wire(c), c in GO_SPACE, WIDE_TAIL)] == []
    trimmed = GO_SPACE - {0x85, 0xA0}
    assert [h for c in codes for h in wrong_reads(chr(c), c in trimmed, WIDE_TAIL)] == []


def test_a_wide_character_and_a_utf8_no_break_space_before_preload_is_misread() -> None:
    header = f'{NO_PRELOAD}; note="{WIDE}x;\xc2\xa0preload;y"'
    found = [i.offset for i in preload_issues(header) if i.code == "preload.misread"]
    assert found == [header.index("preload")]


def test_a_wide_character_and_a_lone_no_break_space_before_max_age_is_kept() -> None:
    header = f'{GOOD}; note="{WIDE}x;\xa0max-age=1;y"'
    assert not misread(header)
