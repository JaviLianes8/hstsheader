from __future__ import annotations

import random
import string

import pytest

from hstsheader import DELTA_SECONDS_MAX, Hsts, HstsError, build, lint, parse, preload_issues

CASES = [
    Hsts(max_age=0),
    Hsts(max_age=600),
    Hsts(max_age=31536000, include_subdomains=True),
    Hsts(max_age=31536000, preload=True),
    Hsts(max_age=31536000, include_subdomains=True, preload=True),
    Hsts(max_age=DELTA_SECONDS_MAX, include_subdomains=True, preload=True),
]


@pytest.mark.parametrize("policy", CASES)
def test_build_then_parse_restores_the_policy(policy: Hsts) -> None:
    assert parse(build(policy), strict=True) == policy


def test_parse_then_build_is_stable() -> None:
    header = "max-age=31536000; includeSubDomains; preload"
    assert build(parse(header)) == header


_NAME = string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~"
_TEXT = "".join(chr(c) for c in range(0x20, 0x7F)) + "\t"


def _extensions(rng: random.Random) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for _ in range(rng.randrange(4)):
        name = "x" + "".join(rng.choice(_NAME) for _ in range(rng.randrange(6)))
        value = "".join(rng.choice(_TEXT) for _ in range(rng.randrange(8)))
        out.setdefault(name.lower(), rng.choice([None, value]))
    return out


def test_random_policies_survive_a_strict_round_trip() -> None:
    rng = random.Random(6797)
    for _ in range(3000):
        policy = Hsts(
            rng.randrange(DELTA_SECONDS_MAX + 1),
            include_subdomains=rng.random() < 0.5,
            preload=rng.random() < 0.5,
        )
        extensions = _extensions(rng)
        header = build(policy, extensions=extensions)
        assert parse(header, strict=True) == policy, header
        codes = {issue.code for issue in lint(header)}
        assert codes <= {"unknown-directive", "max-age.zero-subdomains"}, header


_FUZZ = 'max-ageincludeSubDomainspreload=;" \t\\,0123456789\r\n\x00\x7f\u00e9\uff17'


def test_random_text_only_ever_raises_hsts_error() -> None:
    rng = random.Random(2616)
    for _ in range(3000):
        header = "".join(rng.choice(_FUZZ) for _ in range(rng.randrange(40)))
        lint(header)
        preload_issues(header)
        try:
            strict = parse(header, strict=True)
        except HstsError:
            strict = None
        try:
            tolerant = parse(header)
        except HstsError:
            assert strict is None, header
            continue
        assert strict is None or strict == tolerant, header
