"""Contracts added after the seventh round of independent QA for 1.0.0.

The semicolon, keyword-only, recovery and rebuilt policy tests failed on 14e6168, the
commit the reviewers checked. The others pin behaviour that was already right there but
that a mutant could change without any test noticing.
"""

from __future__ import annotations

import random

import pytest

from hstsheader import Hsts, HstsError, is_preloadable, lint, parse, preload_issues
from hstsheader._chars import TCHAR, is_pair_char, is_qdtext


def _found(value: str) -> list[tuple[str, int | None]]:
    return [(issue.code, issue.offset) for issue in lint(value)]


def _empties(value: str) -> list[int | None]:
    return [issue.offset for issue in lint(value) if issue.code == "empty-directive"]


@pytest.mark.parametrize(
    ("value", "offsets"),
    [
        ("max-age=1;", [9]),
        ("max-age=1;;", [9, 10]),
        ("max-age=1;;;", [9, 10, 11]),
        ("max-age=1; ;", [9, 11]),
        (";;max-age=1", [0, 1]),
        (" ; max-age=1 ; ", [1, 13]),
        ("max-age=1;;x;;", [10, 12, 13]),
        (";", [0]),
        (";;", [0, 1]),
        (" ; ; ", [1, 3]),
    ],
)
def test_each_extra_semicolon_gets_one_warning_at_itself(value: str, offsets: list[int]) -> None:
    assert _empties(value) == offsets


def test_empty_directive_warnings_match_the_extra_semicolons_on_random_values() -> None:
    rng = random.Random(20261022)
    for _ in range(3000):
        elements = [
            rng.choice(["", " ", "a", "max-age=1", " b=2 "]) for _ in range(rng.randint(1, 7))
        ]
        value = ";".join(elements)
        if not value.strip(" "):
            continue
        found = _empties(value)
        filled = sum(1 for element in elements if element.strip(" "))
        assert len(found) == len(set(found)) == value.count(";") - max(filled - 1, 0), value
        assert all(offset is not None and value[offset] == ";" for offset in found), value


def test_hsts_flags_are_keyword_only() -> None:
    with pytest.raises(TypeError):
        Hsts(600, True)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Hsts(600, False, True)  # type: ignore[call-arg]
    assert Hsts(600, include_subdomains=True, preload=True).include_subdomains
    assert Hsts.__match_args__ == ("max_age",)


# An acceptor for prefixes of the RFC 6797 grammar, written apart from the scanner: the
# first character it cannot take is the first bad character.
_PRE, _NAME, _AFTER, _VAL, _TOK, _QUOTE, _PAIR, _END = range(8)


def _step(state: int, char: str) -> int | None:
    blank = char in " \t"
    if state == _PRE:
        return _PRE if blank or char == ";" else _NAME if char in TCHAR else None
    if state in (_NAME, _AFTER):
        if char == "=":
            return _VAL
        if char == ";":
            return _PRE
        return _AFTER if blank else _NAME if state == _NAME and char in TCHAR else None
    if state == _VAL:
        return _VAL if blank else _QUOTE if char == '"' else _TOK if char in TCHAR else None
    if state in (_TOK, _END):
        if char == ";":
            return _PRE
        return _END if blank else _TOK if state == _TOK and char in TCHAR else None
    if state == _QUOTE:
        if char == '"':
            return _END
        return _PAIR if char == "\\" else _QUOTE if is_qdtext(char) else None
    return _QUOTE if is_pair_char(char) else None


def _first_bad(value: str) -> int | None:
    state, opened = _PRE, 0
    for index, char in enumerate(value):
        nxt = _step(state, char)
        if nxt is None:
            return index
        if state == _VAL and nxt == _QUOTE:
            opened = index
        state = nxt
    if state in (_QUOTE, _PAIR):
        return opened  # an unterminated quoted string points at its opening quote
    return len(value) if state == _VAL else None


def _first_syntax(value: str) -> int | None:
    return next((i.offset for i in lint(value) if i.code == "syntax"), None)


@pytest.mark.parametrize(
    ("value", "offset"),
    [
        ('a=";=\x01"; max-age=1', 5),
        ('max-age=1; a=";=\x7f"', 16),
        ('max-age=31536000; x="; (\x01)"', 24),
        ('a="x;(\x01', 6),  # a quote that never closes, with a bad character in it
        ('a="x;(\x01;max-age=1', 6),
        ('a="\\\\;(\x01', 7),
    ],
)
def test_the_first_syntax_error_is_the_first_bad_character(value: str, offset: int) -> None:
    assert [o for code, o in _found(value) if code == "syntax"] == [offset]
    with pytest.raises(HstsError) as caught:
        parse(value, strict=True)
    assert (caught.value.code, caught.value.offset) == ("syntax", offset)


def test_the_first_syntax_error_matches_an_independent_acceptor() -> None:
    rng = random.Random(6797)
    alphabet = 'a1=;" \\\x01\x7f(\xa0'
    for _ in range(20000):
        value = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 14)))
        assert _first_syntax(value) == _first_bad(value), repr(value)


def test_a_closed_quoted_string_hides_its_directives_even_when_it_holds_a_bad_character() -> None:
    assert parse('max-age=600; a="\x01;includeSubDomains;"') == Hsts(600)
    assert parse('max-age=600; a="\\\x01;preload;"') == Hsts(600)
    assert _found('a="\x01; max-age=5"; max-age=10') == [("syntax", 3)]
    assert parse('a="\x01; max-age=5"; max-age=10').max_age == 10


def test_a_quote_that_never_closes_is_skipped_to_the_next_semicolon() -> None:
    assert _found('a="\x01; max-age=5') == [("syntax", 3)]
    assert parse('a="\x01; max-age=5').max_age == 5
    # The skip resumes after the bad character, not at a ';' before it.
    assert _found('a="x;(\x01;max-age=1') == [("syntax", 6)]
    assert parse('a="x;(\x01;max-age=1').max_age == 1
    assert _found('a="x"y; b="x;(\x01') == [
        ("syntax", 5),
        ("syntax", 14),
        ("max-age.missing", None),
    ]


ESCAPED = 'x=1 "\\";max-age=1;"; max-age=2'
ESCAPED_PRELOAD = 'x=1 "\\";preload;"; max-age=31536000; includeSubDomains'


def test_an_escaped_quote_does_not_end_a_skipped_string() -> None:
    assert parse(ESCAPED) == Hsts(2)
    assert _found(ESCAPED) == [("syntax", 4)]
    policy = parse(ESCAPED_PRELOAD)
    assert policy == Hsts(31536000, include_subdomains=True)
    assert _found(ESCAPED_PRELOAD) == [("syntax", 4)]
    codes = [issue.code for issue in preload_issues(ESCAPED_PRELOAD)]
    assert codes == ["syntax", "preload.misread", "preload.missing"]
    assert not is_preloadable(ESCAPED_PRELOAD)


@pytest.mark.parametrize(
    ("value", "offset"),
    [
        ("max-age=; max-age=", 8),
        ("max-age=1 2; max-age=x y", 10),
        ('max-age="1; max-age= ;x', 8),
    ],
)
def test_tolerant_parse_reports_the_first_broken_max_age(value: str, offset: int) -> None:
    with pytest.raises(HstsError) as caught:
        parse(value)
    assert (caught.value.code, caught.value.offset) == ("syntax", offset)
