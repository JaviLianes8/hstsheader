"""Hostile input: work grows linearly with the input, messages stay short, nothing escapes."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable

import pytest

from hstsheader import HstsError, build, is_preloadable, lint, parse, preload_issues
from hstsheader._cli import main
from hstsheader._head import field_lines

VALUE_SHAPES: dict[str, Callable[[int], str]] = {
    "folds": lambda n: "max-age=1" + ";\r\n a" * (n // 5),
    "semicolons": lambda n: ";" * n,
    "unterminated-quotes": lambda n: 'a="x;' * (n // 5),
    "quoted-semicolons": lambda n: 'a=";' * (n // 4),
    "duplicates": lambda n: "max-age=1;" * (n // 10),
    "unknown": lambda n: "a;" * (n // 2),
    "equals": lambda n: "a" + "=" * n,
    "backslashes": lambda n: 'a="' + "\\" * n,
    "controls": lambda n: "\r" * n,
    "broken-values": lambda n: 'a=b"c;' * (n // 6),
    "long-token": lambda n: "max-age=1; " + "a" * n,
    "long-digits": lambda n: "max-age=" + "9" * n,
    "spaces": lambda n: "max-age=1" + " " * n + ";",
    # A backslash before a quote outside a quoted string: each skip used to rescan the tail.
    "escaped-quotes": lambda n: 'a=\\";' * (n // 5),
    "bare-escaped-quotes": lambda n: '\\";' * (n // 3),
    "escaped-quotes-max-age": lambda n: "max-age=1; " + 'max-age=\\";' * (n // 11),
    "escaped-quotes-bad-end": lambda n: 'a=\\";' * (n // 5) + "\x01",
}
HEAD_SHAPES: dict[str, Callable[[int], str]] = {
    "blank-lines": lambda n: "\n" * n + "Strict-Transport-Security: max-age=1",
    "folded-field": lambda n: "HTTP/1.1 200\nStrict-Transport-Security: a" + "\n x" * (n // 3),
    "status-lines": lambda n: "HTTP/1.1 200\n" * (n // 13),
    "fields": lambda n: "HTTP/1.1 200\n" + "Strict-Transport-Security: max-age=1\n" * (n // 38),
}


def _seconds(call: Callable[[str], object], text: str) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        call(text)
        best = min(best, time.perf_counter() - start)
    return best


def _assert_linear(call: Callable[[str], object], make: Callable[[int], str]) -> None:
    small, large = _seconds(call, make(50_000)), _seconds(call, make(200_000))
    # Four times the input; a quadratic path would take about sixteen times as long.
    assert large < max(small, 0.002) * 9, (small, large)


def _all_readers(text: str) -> None:
    lint(text)
    preload_issues(text)
    for strict in (False, True):
        with contextlib.suppress(HstsError):
            parse(text, strict=strict)


@pytest.mark.parametrize("shape", sorted(VALUE_SHAPES))
def test_reading_a_value_is_linear(shape: str) -> None:
    _assert_linear(_all_readers, VALUE_SHAPES[shape])


@pytest.mark.parametrize("shape", sorted(HEAD_SHAPES))
def test_reading_a_response_head_is_linear(shape: str) -> None:
    _assert_linear(field_lines, HEAD_SHAPES[shape])


@pytest.mark.parametrize("shape", sorted(VALUE_SHAPES))
def test_messages_stay_short_for_megabyte_input(shape: str) -> None:
    text = VALUE_SHAPES[shape](1_000_000)
    for issue in [*lint(text), *preload_issues(text)]:
        assert len(issue.message) <= 200, (issue.code, len(issue.message))
    try:
        parse(text, strict=True)
    except HstsError as error:
        assert len(str(error)) <= 220


def test_huge_names_and_values_in_build_errors_are_cut() -> None:
    long = "a" * 1_000_000
    calls: list[Callable[[], object]] = [
        lambda: build(1, extensions={long + " ": None}),
        lambda: build(1, extensions={long: "\r"}),
        lambda: build(1, extensions={long: None, long.upper(): None}),
        lambda: parse("max-age=" + long + "x", strict=True),
        lambda: parse(long + "=" + chr(0x7F), strict=True),
    ]
    for call in calls:
        with pytest.raises(HstsError) as caught:
            call()
        assert len(str(caught.value)) <= 220
        assert "1000000 characters" in str(caught.value) or "1000001 characters" in str(
            caught.value
        )


def test_megabyte_heads_through_the_command_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = "HTTP/1.1 200\r\n" + "X: y\r\n" * 150_000 + "Strict-Transport-Security: max-age=1\r\n"
    assert main([head]) == 0
    assert '"max_age": 1' in capsys.readouterr().out
    assert main(["max-age=" + "1" * 1_000_000]) == 0
    assert is_preloadable("max-age=" + "1" * 1_000_000 + "; includeSubDomains; preload") is False
