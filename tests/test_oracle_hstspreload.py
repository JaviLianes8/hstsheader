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

from hstsheader import HstsError, is_preloadable, lint, parse, preload_issues

ORACLE = os.environ.get("HSTSHEADER_ORACLE", "")
pytestmark = pytest.mark.skipif(not ORACLE, reason="set HSTSHEADER_ORACLE to the built checker")

NAMES = ["max-age", "MAX-AGE", "Max-Age", "includeSubDomains", "includesubdomains"]
NAMES += ["preload", "PRELOAD", "foo", "report-uri", ""]
VALUES = ["31536000", "63072000", "0", "1", "031536000", "315360001", "99999999999"]
VALUES += ["18446744073709551615", "18446744073709551616", "2147483648", '"31536000"']
VALUES += ["abc", "", "1x", "yes", '"a;b"', "1" * 30]
SPACE = ["", " ", "  ", "\t"]
NOISE = [",", "\x0b", "\xa0", "\x85", "a", "=", '"', " ", "\x7f", "\\", "\t"]


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
    parts += rng.sample(["includeSubDomains", "PRELOAD", "foo", "report-uri=x"], rng.randint(0, 4))
    rng.shuffle(parts)
    return rng.choice(SPACE) + (rng.choice(SPACE) + ";" + rng.choice(SPACE)).join(parts)


def _corpus(seed: int, count: int) -> list[str]:
    rng = random.Random(seed)
    return list(dict.fromkeys(_header(rng) for _ in range(count)))


def _run(headers: list[str]) -> list[dict[str, Any]]:
    done = subprocess.run(
        [ORACLE], input=json.dumps(headers).encode(), capture_output=True, check=True
    )
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


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_preloadable_headers_pass_the_site_checker(seed: int) -> None:
    headers = _corpus(seed, 15000)
    for header, verdict in zip(headers, _run(headers), strict=True):
        if is_preloadable(header):
            assert verdict["errors"] == [], header


@pytest.mark.parametrize("seed", [4, 5, 6])
def test_for_rfc_valid_headers_the_verdicts_agree(seed: int) -> None:
    """With no RFC 6797 error, is_preloadable says what the site's checker says."""
    headers = _corpus(seed, 15000)
    compared = 0
    for header, verdict in zip(headers, _run(headers), strict=True):
        if any(issue.severity == "error" for issue in lint(header)):
            continue
        compared += 1
        assert is_preloadable(header) == (verdict["errors"] == []), header
        warned = "header.preloadable.max_age.over_10_years" in verdict["warnings"]
        assert warned == any(
            i.code == "preload.max-age-over-ten-years" for i in preload_issues(header)
        ), header
    assert compared > 2000


@pytest.mark.parametrize("seed", [7, 8])
def test_both_read_the_same_policy(seed: int) -> None:
    """Where strict parsing succeeds, the checker reads the same max-age and flags."""
    headers = _corpus(seed, 15000)
    compared = 0
    for header, verdict in zip(headers, _run(headers), strict=True):
        try:
            policy = parse(header, strict=True)
        except HstsError:
            continue
        if verdict["max_age"] is None:  # the checker refuses a quoted or spaced max-age
            continue
        compared += 1
        assert policy.max_age == min(verdict["max_age"], 2**31), header
        assert policy.include_subdomains == verdict["include_subdomains"], header
        assert policy.preload == verdict["preload"], header
    assert compared > 2000
