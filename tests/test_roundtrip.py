import pytest

from hstsheader import Hsts, build, parse

CASES = [
    Hsts(max_age=0),
    Hsts(max_age=600),
    Hsts(max_age=31536000, include_subdomains=True),
    Hsts(max_age=31536000, preload=True),
    Hsts(max_age=31536000, include_subdomains=True, preload=True),
]


@pytest.mark.parametrize("policy", CASES)
def test_build_then_parse_restores_the_policy(policy: Hsts) -> None:
    header = build(
        policy.max_age,
        include_subdomains=policy.include_subdomains,
        preload=policy.preload,
    )
    assert parse(header) == policy


def test_parse_then_build_is_stable() -> None:
    header = "max-age=31536000; includeSubDomains; preload"
    policy = parse(header)
    assert (
        build(policy.max_age, include_subdomains=policy.include_subdomains, preload=policy.preload)
        == header
    )
