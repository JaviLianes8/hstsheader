import pytest

from hstsheader import HstsError, build


def test_build_max_age_only() -> None:
    assert build(31536000) == "max-age=31536000"


def test_build_with_include_subdomains() -> None:
    assert build(600, include_subdomains=True) == "max-age=600; includeSubDomains"


def test_build_with_preload_only() -> None:
    assert build(600, preload=True) == "max-age=600; preload"


def test_build_full_header_keeps_canonical_order() -> None:
    header = build(31536000, include_subdomains=True, preload=True)
    assert header == "max-age=31536000; includeSubDomains; preload"


def test_build_allows_zero_max_age() -> None:
    assert build(0) == "max-age=0"


def test_build_rejects_negative_max_age() -> None:
    with pytest.raises(HstsError):
        build(-1)


def test_build_rejects_non_integer_max_age() -> None:
    with pytest.raises(HstsError):
        build("31536000")  # type: ignore[arg-type]


def test_build_rejects_bool_max_age() -> None:
    with pytest.raises(HstsError):
        build(True)
