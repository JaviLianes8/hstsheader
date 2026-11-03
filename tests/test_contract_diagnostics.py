"""Hand-written privacy contracts for library-generated diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest

from hstsheader import Hsts, HstsError, build, is_preloadable, lint, parse, preload_issues

MARKER = "private-token-0123456789"


@pytest.mark.parametrize("padding", [0, 100_000])
@pytest.mark.parametrize("position", ["start", "middle", "end"])
def test_invalid_max_age_diagnostics_omit_values(padding: int, position: str) -> None:
    parts = {"start": (0, padding), "middle": (padding // 2, padding // 2), "end": (padding, 0)}
    before, after = parts[position]
    value = "x" * before + MARKER + "x" * after
    header = "max-age=" + value
    for strict in (False, True):
        with pytest.raises(HstsError) as caught:
            parse(header, strict=strict)
        assert (caught.value.code, caught.value.offset) == ("max-age.not-digits", 8)
        assert str(caught.value) == "max-age must be ASCII digits (at offset 8)"
    for reader in (lint, preload_issues):
        issue = next(i for i in reader(header) if i.code == "max-age.not-digits")
        assert (issue.severity, issue.offset) == ("error", 8)
        assert issue.message == "max-age must be ASCII digits"


@pytest.mark.parametrize("size", [0, 100_000])
@pytest.mark.parametrize(
    "template, code",
    [
        ("max-age=1; {name}", "unknown-directive"),
        ("max-age=1; {name}; {name}", "duplicate"),
        ("max-age=1; {name}=", "syntax"),
        ("max-age=1; {name}=ok junk", "syntax"),
        ("max-age=1; max-age{name}=2", "preload.misread"),
    ],
)
def test_reader_diagnostics_omit_arbitrary_names(size: int, template: str, code: str) -> None:
    header = template.format(name=MARKER + "x" * size)
    for reader in (lint, preload_issues):
        issues = reader(header)
        if (code != "preload.misread" or reader is preload_issues) and (
            code != "unknown-directive" or reader is lint
        ):
            assert any(i.code == code for i in issues)
        assert all(MARKER not in i.message and len(i.message) < 220 for i in issues)
    if code in {"duplicate", "syntax"}:
        with pytest.raises(HstsError) as caught:
            parse(header, strict=True)
        assert MARKER not in str(caught.value)
        assert caught.value.code == code


@pytest.mark.parametrize("size", [0, 100_000])
@pytest.mark.parametrize("kind", ["name", "duplicate", "value", "value-type"])
def test_builder_diagnostics_omit_extension_input(size: int, kind: str) -> None:
    name = MARKER + "x" * size
    cases: dict[str, dict[str, str | None]] = {
        "name": {name + " ": None},
        "duplicate": {name: None, name.upper(): None},
        "value": {name: MARKER + "\r"},
        "value-type": {name: cast(str, 1)},
    }
    with pytest.raises((HstsError, TypeError)) as caught:
        build(1, extensions=cases[kind])
    assert MARKER.lower() not in str(caught.value).lower()
    assert len(str(caught.value)) < 220
    if isinstance(caught.value, HstsError):
        assert (
            caught.value.code
            == {"name": "build.name", "duplicate": "duplicate", "value": "build.value"}[kind]
        )


TYPE_CALLS: list[Callable[[object], object]] = [
    lambda value: parse(cast(str, value)),
    lambda value: lint(cast(str, value)),
    lambda value: preload_issues(cast(str, value)),
    lambda value: is_preloadable(cast(str, value)),
    lambda value: lint([cast(str, value)]),
    lambda value: lint(["max-age=1", cast(str, value)]),
    lambda value: Hsts(cast(int, value)),
    lambda value: Hsts(1, include_subdomains=cast(bool, value)),
    lambda value: Hsts(1, preload=cast(bool, value)),
    lambda value: build(cast(int, value)),
    lambda value: build(1, include_subdomains=cast(bool, value)),
    lambda value: build(1, preload=cast(bool, value)),
    lambda value: parse("max-age=1", strict=cast(bool, value)),
    lambda value: build(1, extensions={cast(str, value): None}),
]


@pytest.mark.parametrize("call", TYPE_CALLS)
@pytest.mark.parametrize("size", [0, 100_000])
def test_wrong_type_messages_omit_class_names(call: Callable[[object], object], size: int) -> None:
    value = type(MARKER + "x" * size, (), {})()
    with pytest.raises(TypeError) as caught:
        call(value)
    assert MARKER not in str(caught.value)
    assert len(str(caught.value)) < 220


@pytest.mark.parametrize("base", [dict, set])
def test_wrong_field_containers_omit_class_names(base: type) -> None:
    value = type(MARKER + "x" * 100_000, (base,), {})()
    with pytest.raises(TypeError) as caught:
        parse(cast(str, value))
    assert MARKER not in str(caught.value)
    assert len(str(caught.value)) < 220
