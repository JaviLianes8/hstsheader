from __future__ import annotations

import pytest

from hstsheader import DELTA_SECONDS_MAX, Hsts, HstsError, build, parse


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
    with pytest.raises(TypeError, match="max_age must be an int, got str"):
        build("31536000")  # type: ignore[arg-type]


def test_build_rejects_bool_max_age() -> None:
    with pytest.raises(TypeError, match="got bool"):
        build(True)


def test_build_caps_max_age_at_two_to_the_31() -> None:
    assert build(DELTA_SECONDS_MAX) == "max-age=2147483648"
    with pytest.raises(HstsError):
        build(DELTA_SECONDS_MAX + 1)


@pytest.mark.parametrize("flag", ["include_subdomains", "preload"])
def test_build_refuses_flags_that_are_not_bool(flag: str) -> None:
    with pytest.raises(TypeError, match=f"{flag} must be a bool, got str"):
        build(1, **{flag: "no"})  # type: ignore[arg-type]


def test_build_takes_an_hsts_object() -> None:
    assert build(Hsts(5, include_subdomains=True)) == "max-age=5; includeSubDomains"
    assert build(Hsts(5, preload=True)) == "max-age=5; preload"


@pytest.mark.parametrize("flag", ["include_subdomains", "preload"])
def test_build_refuses_flags_next_to_an_hsts_object(flag: str) -> None:
    with pytest.raises(TypeError):
        build(Hsts(5), **{flag: False})  # type: ignore[arg-type]


def test_extensions_follow_the_known_directives_in_order() -> None:
    header = build(5, preload=True, extensions={"a": None, "b": "tok-en", "c": ""})
    assert header == 'max-age=5; preload; a; b=tok-en; c=""'


def test_extension_values_that_are_not_tokens_are_quoted() -> None:
    header = build(5, extensions={"report-uri": 'https://e.com/a;b "q" \\x'})
    assert header == 'max-age=5; report-uri="https://e.com/a;b \\"q\\" \\\\x"'
    assert parse(header, strict=True) == Hsts(5)


@pytest.mark.parametrize(
    "value", ["a\r\nSet-Cookie: x=1", "a\nb", "\x00", "\x7f", "caf\u00e9", "\u2028"]
)
def test_extension_values_cannot_inject(value: str) -> None:
    with pytest.raises(HstsError) as caught:
        build(5, extensions={"x": value})
    assert caught.value.code == "build.value"


@pytest.mark.parametrize("name", ["", "a b", "a=b", "a;b", "a\r\n", "\u00e9", 'a"', "a,b"])
def test_extension_names_must_be_tokens(name: str) -> None:
    with pytest.raises(HstsError) as caught:
        build(5, extensions={name: None})
    assert caught.value.code == "build.name"


@pytest.mark.parametrize("name", ["max-age", "MAX-AGE", "includeSubDomains", "Preload"])
def test_extension_names_cannot_shadow_the_known_directives(name: str) -> None:
    with pytest.raises(HstsError) as caught:
        build(5, extensions={name: None})
    assert caught.value.code == "build.name"


def test_extension_names_must_be_unique_ignoring_case() -> None:
    with pytest.raises(HstsError) as caught:
        build(5, extensions={"Ext": None, "eXT": "1"})
    assert caught.value.code == "duplicate"


def test_extension_arguments_of_the_wrong_type_are_refused() -> None:
    with pytest.raises(TypeError, match="extension x needs a str value or None"):
        build(5, extensions={"x": 1})  # type: ignore[dict-item]
    with pytest.raises(TypeError, match="extension names must be str, got int"):
        build(5, extensions={1: None})  # type: ignore[dict-item]
    with pytest.raises(TypeError, match="mapping"):
        build(5, extensions=[("x", None)])  # type: ignore[arg-type]
