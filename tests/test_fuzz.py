"""Seeded property tests on random and grammar-shaped input.

The strict reader is compared with an independent acceptor written here from the
RFC 6797 section 6.1 grammar and the RFC 9110 section 5.6 token and quoted-string rules
(hand-written from the grammar, not taken from the library).
"""

from __future__ import annotations

import random
import re

import pytest

from hstsheader import Hsts, HstsError, Issue, is_preloadable, lint, parse, preload_issues

TCHAR = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]"
QUOTED = r'"(?:[\t \x21\x23-\x5b\x5d-\x7e\x80-\xff]|\\[\t \x21-\x7e\x80-\xff])*"'
DIRECTIVE = rf"({TCHAR}+)(?:[ \t]*=[ \t]*({TCHAR}+|{QUOTED}))?"
HEADER = re.compile(rf"[ \t]*(?:{DIRECTIVE})?[ \t]*(?:;[ \t]*(?:{DIRECTIVE})?[ \t]*)*")
ELEMENT = re.compile(rf"(?:^|;)[ \t]*(?:{DIRECTIVE})?[ \t]*")

PIECES = ["max-age", "MAX-AGE", "includeSubDomains", "preload", "x", "=", ";", " ", "\t"]
PIECES += ['"', "\\", "0", "1", "31536000", "a b", ",", "\x7f", "\xe9", "\u2028", "\x0b"]
PIECES += ["\r\n ", "\r", "\n", "\0", "=1", '="1"', "; ", "\x85"]


def _unquote(value: str) -> str:
    return re.sub(r"\\(.)", r"\1", value[1:-1]) if value.startswith('"') else value


def _oracle(text: str) -> Hsts | None:
    """The policy a strict RFC 6797 reader takes from ``text``, or None when it must ignore it."""
    if HEADER.fullmatch(text) is None:
        return None
    seen: dict[str, str | None] = {}
    for match in ELEMENT.finditer(text):
        name, value = match.group(1), match.group(2)
        if name is None:
            continue
        key = name.lower()
        if key in seen:
            return None
        seen[key] = None if value is None else _unquote(value)
    age = seen.get("max-age")
    if "max-age" not in seen or age is None or not re.fullmatch(r"[0-9]+", age):
        return None
    # RFC 6797 defines includeSubDomains as valueless; preload is not in it, so a preload
    # with a value is just an unknown directive.
    if "includesubdomains" in seen and seen["includesubdomains"] is not None:
        return None
    subdomains = "includesubdomains" in seen
    preload = "preload" in seen and seen["preload"] is None
    return Hsts(min(int(age), 2**31), include_subdomains=subdomains, preload=preload)


def _strict(text: str | list[str]) -> Hsts | None:
    try:
        return parse(text, strict=True)
    except HstsError:
        return None


def _random(rng: random.Random, pieces: list[str]) -> str:
    return "".join(rng.choice(pieces) for _ in range(rng.randint(0, 12)))


AGES = ["0", "1", "007", "31536000", "99999999999", '"60"', '"6\\0"', '"6 0"', "6a", ""]
OTHERS = ["includeSubDomains", "PRELOAD", "x", "x=1", 'x="a;b\\"c"', "preload=1", ""]


def _shaped(rng: random.Random, pieces: list[str]) -> str:
    """Directive-shaped headers, sometimes with one random piece inserted."""
    elements = [rng.choice(["max-age", "Max-Age"]) + "=" + rng.choice(AGES)]
    elements += rng.sample(OTHERS, rng.randint(0, 3))
    if rng.random() < 0.1:
        elements.append(rng.choice(elements))
    rng.shuffle(elements)
    space = ["", " ", "\t ", ""]
    text = "".join(f"{rng.choice(space)};{rng.choice(space)}{e}" for e in elements)[1:]
    if rng.random() < 0.3:
        at = rng.randrange(len(text) + 1)
        text = text[:at] + rng.choice(pieces) + text[at:]
    return text


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_strict_reading_matches_the_grammar(seed: int) -> None:
    rng = random.Random(seed)
    plain = [p for p in PIECES if not set(p) & set("\r\n\0")]
    accepted = 0
    for _ in range(8000):
        text = _shaped(rng, plain) if rng.random() < 0.7 else _random(rng, plain)
        expected = _oracle(text)
        assert _strict(text) == expected, repr(text)
        accepted += expected is not None
    assert accepted > 1500


@pytest.mark.parametrize("seed", [21, 22, 23])
def test_every_reader_is_total_and_consistent(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(6000):
        text = _shaped(rng, PIECES) if rng.random() < 0.5 else _random(rng, PIECES)
        issues = lint(text)
        assert all(type(issue) is Issue for issue in issues)
        for issue in issues:
            assert issue.severity in ("error", "warning")
            assert issue.offset is None or 0 <= issue.offset <= len(text)
        offsets = [i.offset for i in issues if i.offset is not None]
        assert offsets == sorted(offsets)
        strict = _strict(text)
        assert (strict is not None) == (not any(i.severity == "error" for i in issues))
        try:
            tolerant: Hsts | None = parse(text)
        except HstsError as error:
            assert error.code.startswith(("max-age", "syntax")), error.code
            tolerant = None
        if strict is not None:
            assert tolerant == strict
        found = preload_issues(text)
        assert is_preloadable(text) == (not any(i.severity == "error" for i in found))
        if is_preloadable(text):
            assert tolerant is not None and tolerant.include_subdomains and tolerant.preload
            assert tolerant.max_age >= 31536000


@pytest.mark.parametrize("seed", [31, 32])
def test_field_lists_read_only_the_first_line(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(2000):
        lines = [_random(rng, PIECES) for _ in range(rng.randint(1, 3))]
        first = [i for i in lint(lines) if i.code != "multiple-fields"]
        assert first == list(lint(lines[0]))
        assert _strict(lines[0]) == (_strict(lines[0]) if len(lines) == 1 else _strict(lines))
