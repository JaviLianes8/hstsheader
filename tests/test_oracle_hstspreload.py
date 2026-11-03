"""Compare with the hstspreload.org header checker, run live from its own Go source.

`tests/oracle` wraps chromium/hstspreload at commit d624d7c (the same commit as the pinned
`header.go`). Build it with Go and point HSTSHEADER_ORACLE at the program:

    cd tests/oracle && go build -o hstspreload-oracle .

These tests skip while the variable is unset.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
from typing import Any

import pytest

from hstsheader import Hsts, HstsError, is_preloadable, lint, parse, preload_issues

ORACLE = os.environ.get("HSTSHEADER_ORACLE", "")
pytestmark = pytest.mark.skipif(not ORACLE, reason="set HSTSHEADER_ORACLE to the built checker")

NAMES = ["max-age", "MAX-AGE", "Max-Age", "includeSubDomains", "includesubdomains"]
NAMES += ["preload", "PRELOAD", "foo", "report-uri", ""]
# Names the checker matches by prefix, and quoted values it cuts at their semicolons.
NAMES += ["max-agex", "MAX-AGE-v2", "preloadx"]
# Octets as the command line reads them (latin-1): UTF-8 spaces and the long s, which the
# checker reads as UTF-8, and lone octets that are not UTF-8.
NAMES += ["include\xc5\xbfubdomains", "\xe3\x80\x80preload"]
VALUES = ["31536000", "63072000", "0", "1", "031536000", "315360001", "99999999999"]
VALUES += ["18446744073709551615", "18446744073709551616", "2147483648", '"31536000"']
VALUES += ["abc", "", "1x", "yes", '"a;b"', "1" * 30]
VALUES += ['"a;max-age=1"', '"x;preload;includeSubDomains;y"', '"a; MAX-AGE=31536000;b"']
VALUES += ['"a;\xa0preload;b"', '"a;max-age"', '"a;preloadx;b"', '"a;\xc2\xa0preload;b"']
VALUES += ['"a;\xe2\x80\x8amax-age=1"', '"x;include\xc5\xbfubdomains;y"', '"a;\x85preload;b"']
MISREAD = ['note="a;preload;b"', "max-agex=1", 'report-uri="a;b"']
SPACE = ["", " ", "  ", "\t"]
NOISE = [",", "\x0b", "\xa0", "\x85", "a", "=", '"', " ", "\x7f", "\\", "\t", "\xc2\xa0"]
NOISE += ["\xc2\x85", "\xe3\x80\x80", "\xc5\xbf"]


def _header(rng: random.Random) -> str:
    if rng.random() < 0.5:
        return _well_formed(rng)
    parts = []
    for _ in range(rng.randint(0, 5)):
        name = rng.choice(NAMES)
        if (rng.random() < 0.5 and name.lower() == "max-age") or rng.random() < 0.15:
            name += rng.choice(["=", "=", "=", " =", "= "]) + rng.choice(VALUES)
        parts.append(rng.choice(SPACE) + name + rng.choice(SPACE))
    text = ";".join(parts)
    if rng.random() < 0.15:
        at = rng.randrange(len(text) + 1)
        text = text[:at] + rng.choice(NOISE) + text[at:]
    return text


def _well_formed(rng: random.Random) -> str:
    """Unique directives in any order and case, a digit max-age: mostly RFC valid."""
    seconds = rng.choice([*VALUES[:10], str(rng.randrange(10**12))])
    parts = [rng.choice(NAMES[:3]) + "=" + seconds]
    extra = ["includeSubDomains", "PRELOAD", "foo", "report-uri=x", rng.choice(MISREAD)]
    parts += rng.sample(extra, rng.randint(0, 5))
    rng.shuffle(parts)
    return rng.choice(SPACE) + (rng.choice(SPACE) + ";" + rng.choice(SPACE)).join(parts)


def _corpus(seed: int, count: int) -> list[str]:
    rng = random.Random(seed)
    return list(dict.fromkeys(_header(rng) for _ in range(count)))


def _misread(header: str) -> bool:
    return any(issue.code == "preload.misread" for issue in preload_issues(header))


def octets(header: str) -> bytes:
    """What a header stands for: latin-1 up to U+00FF, UTF-8 above, as in the library."""
    return b"".join(
        bytes([ord(c)]) if ord(c) < 0x100 else c.encode("utf-8", "surrogatepass") for c in header
    )


def _run(headers: list[str]) -> list[dict[str, Any]]:
    """The checker's verdicts on the octets of each header, sent in hex as it takes them."""
    payload = json.dumps([octets(header).hex() for header in headers]).encode()
    done = subprocess.run([ORACLE], input=payload, capture_output=True, check=True)
    verdicts: list[dict[str, Any]] = json.loads(done.stdout)
    assert len(verdicts) == len(headers)
    return verdicts


def test_the_oracle_answers_its_own_vectors() -> None:
    good, quoted, zero = _run(
        ["max-age=31536000; includeSubDomains; preload", 'max-age="1"', "max-age=0"]
    )
    assert good["errors"] == [] and good["max_age"] == 31536000
    assert "header.parse.max_age.non_digit_characters" in quoted["errors"]
    assert "header.preloadable.max_age.zero" in zero["errors"]


def test_a_value_on_preload_is_only_a_warning_on_both_sides() -> None:
    headers = [
        "max-age=31536000; includeSubDomains; preload; preload=yes",
        "max-age=315360001;;INCLUDESUBDOMAINS;;preload=1 ;preload;",
        '\tmax-age=31536000; ; preload ;preload="";includeSubDomains ',
    ]
    for header, verdict in zip(headers, _run(headers), strict=True):
        assert verdict["errors"] == [], header
        assert "header.parse.invalid.preload" in verdict["warnings"], header
        assert is_preloadable(header), header
        assert "preload.invalid" in [i.code for i in preload_issues(header)], header


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_preloadable_headers_pass_the_site_checker(seed: int) -> None:
    headers = _corpus(seed, 15000)
    for header, verdict in zip(headers, _run(headers), strict=True):
        if is_preloadable(header):
            assert verdict["errors"] == [], header


@pytest.mark.parametrize("seed", [4, 5, 6])
def test_for_rfc_valid_headers_the_verdicts_agree(seed: int) -> None:
    """With no RFC 6797 error, is_preloadable says what the site's checker says.

    The exception is preload.misread: a header the checker reads as other directives is
    refused here, even where the checker would still take it.
    """
    headers = _corpus(seed, 15000)
    compared = misread = 0
    for header, verdict in zip(headers, _run(headers), strict=True):
        if any(issue.severity == "error" for issue in lint(header)):
            continue
        if _misread(header):
            assert not is_preloadable(header), header
            misread += 1
            continue
        compared += 1
        assert is_preloadable(header) == (verdict["errors"] == []), header
        warned = "header.preloadable.max_age.over_10_years" in verdict["warnings"]
        assert warned == any(
            i.code == "preload.max-age-over-ten-years" for i in preload_issues(header)
        ), header
    assert compared > 2000 and misread > 100


@pytest.mark.parametrize("seed", [7, 8])
def test_both_read_the_same_policy(seed: int) -> None:
    """Where strict parsing succeeds and nothing is misread, both read the same policy."""
    headers = _corpus(seed, 15000)
    compared = 0
    for header, verdict in zip(headers, _run(headers), strict=True):
        try:
            policy = parse(header, strict=True)
        except HstsError:
            continue
        if verdict["max_age"] is None or _misread(
            header
        ):  # the checker refuses a quoted or spaced max-age
            continue
        compared += 1
        assert policy.max_age == min(verdict["max_age"], 2**31), header
        assert policy.include_subdomains == verdict["include_subdomains"], header
        assert policy.preload == verdict["preload"], header
    assert compared > 2000


def test_the_checker_reads_a_misread_header_as_other_directives() -> None:
    good = "max-age=31536000; includeSubDomains; preload"
    prefix, cut, inside = _run(
        [
            f"{good}; max-agex=5",
            f'{good}; report-uri="https://r.example/c?a=1;max-age=2"',
            'note="x;preload;includeSubDomains;y"; max-age=31536000',
        ]
    )
    assert prefix["errors"] == ["header.parse.invalid.max_age.no_value"]
    assert cut["errors"] == ["header.parse.max_age.non_digit_characters"]
    # Accepted by the checker, which sees two directives RFC 6797 reads as a quoted value.
    assert (inside["errors"], inside["preload"], inside["include_subdomains"]) == ([], True, True)
    assert parse('note="x;preload;includeSubDomains;y"; max-age=31536000', strict=True) == (
        Hsts(31536000)
    )
