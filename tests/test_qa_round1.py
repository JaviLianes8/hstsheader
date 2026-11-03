"""Library contracts added after the first round of independent QA for 1.0.0.

The tests up to the sender ceiling failed on c8a317c, the commit the reviewers checked.
The rest pin behaviour that mutants changed there without any test noticing.
"""

from __future__ import annotations

import inspect
import typing

import pytest

import hstsheader
from hstsheader import Hsts, HstsError, Issue, lint, parse, preload_issues


def _public_classes_and_functions() -> list[object]:
    names = [getattr(hstsheader, name) for name in hstsheader.__all__]
    return [obj for obj in names if inspect.isclass(obj) or inspect.isfunction(obj)]


@pytest.mark.parametrize("obj", _public_classes_and_functions(), ids=repr)
def test_type_hints_resolve_on_every_public_class_and_function(obj: object) -> None:
    typing.get_type_hints(obj)
    if inspect.isclass(obj):
        typing.get_type_hints(obj.__init__)


def test_the_severity_type_is_public() -> None:
    assert "Severity" in hstsheader.__all__
    assert hstsheader.Severity == typing.Literal["error", "warning"]
    assert typing.get_type_hints(Issue)["severity"] == hstsheader.Severity


def test_lint_takes_its_argument_as_header() -> None:
    assert list(inspect.signature(lint).parameters) == ["header"]
    assert lint(header="max-age=1") == ()


@pytest.mark.parametrize("strict", ["false", "no", 0, 1, None, [], 1.0])
def test_strict_must_be_a_bool(strict: object) -> None:
    with pytest.raises(TypeError, match="strict must be a bool"):
        parse("max-age=5; max-age=6", strict=strict)  # type: ignore[arg-type]


def test_a_value_on_preload_is_an_unknown_directive_to_rfc_6797() -> None:
    (issue,) = lint("max-age=600; preload=yes")
    assert (issue.code, issue.severity, issue.offset) == ("preload-value", "warning", 13)
    assert parse("max-age=600; preload=yes", strict=True) == Hsts(600)
    assert parse('max-age=600; preload=""', strict=True) == Hsts(600)
    # includeSubDomains is defined by RFC 6797 as valueless: a value there stays an error.
    assert [i.code for i in lint("max-age=600; includeSubDomains=1")] == ["value-not-allowed"]


def test_a_value_on_preload_is_refused_by_the_preload_rules() -> None:
    codes = [
        (i.code, i.severity)
        for i in preload_issues("max-age=63072000; includeSubDomains; preload=1")
    ]
    assert codes == [("preload.invalid", "warning"), ("preload.missing", "error")]
    # A valueless preload next to one with a value: the site's checker only warns (round 2).
    both = preload_issues("max-age=63072000; includeSubDomains; preload; preload=1")
    assert ("preload.invalid", "warning") in [(i.code, i.severity) for i in both]
    assert hstsheader.is_preloadable("max-age=63072000; includeSubDomains; preload; preload=1")


def test_the_sender_ceiling_is_presented_as_this_library_choice() -> None:
    with pytest.raises(HstsError) as caught:
        Hsts(2**31 + 1)
    assert caught.value.code == "max-age.too-large"
    assert "recipients" not in str(caught.value)
    assert str(caught.value) == "max_age must not exceed 2147483648, the cap this library applies"


@pytest.mark.parametrize("code", [0x80, 0xA0, 0xE9, 0xFF])
def test_obs_text_may_follow_a_backslash_in_a_quoted_string(code: int) -> None:
    header = f'max-age=600; ext="a\\{chr(code)}"'
    assert parse(header, strict=True) == Hsts(600)
    assert [i.code for i in lint(header)] == ["unknown-directive"]


@pytest.mark.parametrize(("code", "shown"), [(0x7F, "U+007F"), (0x100, "U+0100")])
def test_del_and_non_latin_1_cannot_follow_a_backslash(code: int, shown: str) -> None:
    with pytest.raises(HstsError) as caught:
        parse(f'max-age=600; ext="a\\{chr(code)}"', strict=True)
    assert (caught.value.code, caught.value.offset) == ("syntax", 20)
    assert str(caught.value) == f"{shown} cannot follow a backslash (at offset 20)"


@pytest.mark.parametrize(("fold", "offset"), [("\r\n ", 15), ("\n ", 14), ("\r\n\t\t", 16)])
def test_offsets_after_a_folded_line_point_at_the_input(fold: str, offset: int) -> None:
    found = [(i.code, i.offset) for i in lint(f"max-age=600;{fold}foo")]
    assert found == [("obs-fold", 12), ("unknown-directive", offset)]


def test_a_nul_is_reported_once_and_read_as_whitespace() -> None:
    header = "max-age=600;\x00includeSubDomains"
    assert [(i.code, i.severity, i.offset) for i in lint(header)] == [
        ("control-character", "error", 12)
    ]
    assert parse(header) == Hsts(600, include_subdomains=True)


@pytest.mark.parametrize(
    ("header", "codes"),
    [
        ("includeSubDomains", ["max-age.missing"]),
        ("max-age=x; includeSubDomains", ["max-age.not-digits"]),
        ("max-age; includeSubDomains", ["max-age.no-value"]),
        ("max-age=0; includeSubDomains", ["max-age.zero-subdomains"]),
        ("max-age=00; includeSubDomains", ["max-age.leading-zero", "max-age.zero-subdomains"]),
    ],
)
def test_the_zero_max_age_warning_needs_a_max_age_of_zero(header: str, codes: list[str]) -> None:
    assert [i.code for i in lint(header)] == codes


@pytest.mark.parametrize(
    "value",
    [b"", bytearray(), memoryview(b""), b"max-age=1", bytearray(b"max-age=1"), memoryview(b"m")],
    ids=["bytes", "bytearray", "memoryview", "bytes-1", "bytearray-1", "memoryview-1"],
)
def test_binary_input_is_a_type_error_with_the_decode_hint(value: object) -> None:
    hint = "pass the header as str; decode bytes with latin-1 first"
    for call in (parse, lint, preload_issues, hstsheader.is_preloadable):
        with pytest.raises(TypeError) as caught:
            call(value)  # type: ignore[arg-type]
        assert str(caught.value) == hint
