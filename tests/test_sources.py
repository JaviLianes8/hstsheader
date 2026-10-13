"""Check the library against RFC 6797, 2616, 9110, 9111, hstspreload.org and Chromium.

The files are read from tests/upstream (URL, revision, size and sha256 in MANIFEST.json);
the tests that read them skip until `python scripts/fetch_upstream.py` has fetched them.
"""

from __future__ import annotations

import json
import re

from hstsheader import (
    DELTA_SECONDS_MAX,
    PRELOAD_MIN_MAX_AGE,
    Hsts,
    HstsError,
    is_preloadable,
    lint,
    parse,
    preload_issues,
)
from hstsheader._chars import TCHAR, is_qdtext
from hstsheader._preload import _TEN_YEARS


def _section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_every_rfc_6797_example_is_honoured(rfc6797: str) -> None:
    examples = _section(rfc6797, "\n6.2.  Examples", "\n7.  Server Processing Model")
    values = re.findall(r"^ +Strict-Transport-Security: (.+)$", examples, flags=re.MULTILINE)
    assert len(values) == 5
    expected = [Hsts(31536000), Hsts(15768000, True), Hsts(31536000), Hsts(0), Hsts(0, True)]
    assert [parse(value, strict=True) for value in values] == expected


def test_the_grammar_and_rules_this_library_applies_are_in_rfc_6797(rfc6797: str) -> None:
    grammar = _section(rfc6797, "\n6.1.  Strict", "\n6.1.1.")
    flat = " ".join(grammar.split())
    assert '[ directive ] *( ";" [ directive ] )' in flat
    assert "directive-value = token | quoted-string" in flat
    assert "All directives MUST appear only once" in flat
    assert "Directive names are case-insensitive" in flat
    assert "max-age-value = delta-seconds" in " ".join(rfc6797.split())
    assert "only the first such header field" in rfc6797


def test_implied_whitespace_comes_from_rfc_2616(rfc2616: str) -> None:
    rule = " ".join(_section(rfc2616, "implied *LWS\n", "\n\n").split())
    assert "between adjacent words and separators" in rule
    assert parse("max-age = 5 ; preload", strict=True) == Hsts(5, preload=True)


def test_tchar_matches_rfc_9110_and_the_rfc_2616_separators(rfc9110: str, rfc2616: str) -> None:
    rule = _section(rfc9110, "     tchar          =", "; any VCHAR")
    symbols = set(re.findall(r'"(.)"', rule))
    letters = {chr(c) for c in range(0x41, 0x5B)} | {chr(c) for c in range(0x61, 0x7B)}
    assert symbols | letters | set("0123456789") == TCHAR
    separators = _section(rfc2616, "separators     =", "\n\n")
    old = set(re.findall(r'"(.)"', separators)) | {" ", "\t", '"'}
    assert {chr(c) for c in range(0x21, 0x7F)} - old == TCHAR


def test_qdtext_matches_rfc_9110(rfc9110: str) -> None:
    line = _section(rfc9110, "     qdtext         =", "\n")
    parts = ["HTAB", "SP", "%x21", "%x23-5B", "%x5D-7E", "obs-text"]
    assert line.split()[::2] == parts
    allowed = {0x09, 0x20, 0x21, *range(0x23, 0x5C), *range(0x5D, 0x7F), *range(0x80, 0x100)}
    assert {c for c in range(0x100) if is_qdtext(chr(c))} == allowed


def test_the_delta_seconds_ceiling_is_the_one_rfc_9111_names(rfc9111: str) -> None:
    rule = " ".join(_section(rfc9111, "1.2.2.  Delta Seconds", "Note:").split())
    assert "MUST consider the value to be 2147483648 (2^31)" in rule
    assert DELTA_SECONDS_MAX == 2147483648
    assert parse("max-age=2147483649").max_age == DELTA_SECONDS_MAX


def test_preload_requirements_match_hstspreload_org(preload_page: str) -> None:
    text = re.sub(r"<[^>]+>", "", preload_page)
    flat = " ".join(text.split())
    minimum = re.search(r"The max-age must be at least (\d+) seconds", flat)
    assert minimum is not None and int(minimum.group(1)) == PRELOAD_MIN_MAX_AGE
    assert "The includeSubDomains directive must be specified" in flat
    assert "The preload directive must be specified" in flat
    example = re.search(r"Strict-Transport-Security: (max-age=[^\n<]+?) You can check", flat)
    assert example is not None
    assert is_preloadable(example.group(1)) and preload_issues(example.group(1)) == ()


def test_the_checker_constants_match_hstspreload(preload_checker: str) -> None:
    assert re.search(r"oneYear\s+= 86400 \* 365\n", preload_checker)
    assert re.search(r"tenYears\s+= 10 \* oneYear\n", preload_checker)
    assert "we don't support quoted values" in preload_checker
    assert _TEN_YEARS == 10 * 365 * 86400 == 10 * PRELOAD_MIN_MAX_AGE


_ENTRY = re.compile(
    r'^\t\{\n\t\t"((?:[^"\\]|\\.)*)",[^\n]*\n\t\t"((?:[^"\\]|\\.)*)",[^\n]*\n(.*?)^\t\},',
    flags=re.MULTILINE | re.DOTALL,
)


def _table(go: str, name: str) -> list[tuple[str, bool, str]]:
    body = _section(go, f"var {name} = ", "\nfunc ")
    rows = [(json.loads(f'"{h}"'), "Errors:" in rest, rest) for _, h, rest in _ENTRY.findall(body)]
    assert rows, name
    return rows


# Where RFC 6797 is stricter than the site's parser, which reports a missing max-age only
# in its preload step and tolerates a repeated preload directive.
_STRICTER = {
    "": {"max-age.missing"},
    ";": {"max-age.missing"},
    "preload; includeSubDomains": {"max-age.missing"},
    "preload; includeSubDomains; preload; max-age=12345678; preload": {"duplicate"},
}


def test_the_checker_parse_vectors_agree(preload_checker_tests: str) -> None:
    rows = _table(preload_checker_tests, "parseHeaderStringTests")
    rows += _table(preload_checker_tests, "parseHeaderStringWithErrorsTests")
    assert len(rows) == 24
    for header, has_errors, rest in rows:
        errors = {issue.code for issue in lint(header) if issue.severity == "error"}
        assert errors == _STRICTER.get(header, errors if has_errors else set()), header
        assert bool(errors) or not has_errors, header
        seconds = re.search(r"MaxAge: &MaxAge\{Seconds: (\d+)\}", rest)
        if seconds:
            assert parse(header).max_age == int(seconds.group(1)), header
        elif not has_errors:
            try:
                parse(header)
            except HstsError as error:
                assert error.code == "max-age.missing"


def test_the_checker_preload_vectors_agree(preload_checker_tests: str) -> None:
    rows = _table(preload_checker_tests, "preloadableHeaderStringTests")
    rows += [
        r
        for r in _table(preload_checker_tests, "eligibleHeaderStringTests")
        if "Bulk18Weeks" not in r[2]
    ]
    assert len(rows) == 22
    for header, has_errors, _ in rows:
        assert is_preloadable(header) is not has_errors, header


def test_the_chromium_rules_mirrored_in_strict_mode(chromium_parser: str) -> None:
    assert "Reject the header if `max-age` is specified more than once." in chromium_parser
    assert "Reject the header if `includeSubDomains` has a value specified" in chromium_parser
    assert "Reject the header if no `max-age` was set." in chromium_parser
    for header in ("max-age=1; max-age=1", "max-age=1; includeSubDomains=x", "preload"):
        assert any(issue.severity == "error" for issue in lint(header)), header


def test_chromium_clamps_to_a_year_which_this_library_does_not(chromium_limits: str) -> None:
    assert "const uint32_t kMaxHSTSAgeSecs = 86400 * 365;" in chromium_limits
    assert parse("max-age=63072000").max_age == 63072000
