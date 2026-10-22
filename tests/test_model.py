from __future__ import annotations

import dataclasses

import pytest

from hstsheader import DELTA_SECONDS_MAX, Hsts, HstsError, Issue


def test_hsts_is_frozen() -> None:
    policy = Hsts(1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.max_age = 2  # type: ignore[misc]


@pytest.mark.parametrize("value", [-1, DELTA_SECONDS_MAX + 1])
def test_hsts_refuses_a_max_age_out_of_range(value: int) -> None:
    with pytest.raises(HstsError):
        Hsts(value)


@pytest.mark.parametrize("value", [True, 1.0, "1", None])
def test_hsts_refuses_a_max_age_that_is_not_an_int(value: object) -> None:
    with pytest.raises(TypeError, match="max_age must be an int"):
        Hsts(value)  # type: ignore[arg-type]


def test_hsts_accepts_the_whole_range() -> None:
    assert Hsts(0).max_age == 0
    assert Hsts(DELTA_SECONDS_MAX).max_age == DELTA_SECONDS_MAX


@pytest.mark.parametrize("field", ["include_subdomains", "preload"])
@pytest.mark.parametrize("value", [1, "yes", None])
def test_hsts_flags_must_be_bool(field: str, value: object) -> None:
    with pytest.raises(TypeError) as caught:
        Hsts(1, **{field: value})  # type: ignore[arg-type]
    assert not isinstance(caught.value, HstsError)
    assert str(caught.value) == f"{field} must be a bool, got {type(value).__name__}"


def test_hsts_error_is_a_value_error_with_code_and_offset() -> None:
    error = HstsError("bad", code="syntax", offset=3)
    assert isinstance(error, ValueError)
    assert (error.code, error.offset, str(error)) == ("syntax", 3, "bad (at offset 3)")
    plain = HstsError("bad")
    assert (plain.code, plain.offset, str(plain)) == ("invalid", None, "bad")


def test_negative_and_too_large_have_their_own_codes() -> None:
    with pytest.raises(HstsError) as low:
        Hsts(-5)
    with pytest.raises(HstsError) as high:
        Hsts(DELTA_SECONDS_MAX + 1)
    assert (low.value.code, high.value.code) == ("max-age.negative", "max-age.too-large")


def test_issue_is_frozen_and_offset_defaults_to_none() -> None:
    issue = Issue("c", "m", "warning")
    assert issue.offset is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        issue.code = "d"  # type: ignore[misc]
