"""Regression tests for the findings of the independent review."""

from __future__ import annotations

import io
import json
import sys
from collections.abc import Iterator

import pytest

from hstsheader import Hsts, HstsError, build, is_preloadable, lint, parse, preload_issues
from hstsheader._chars import is_qdtext
from hstsheader._cli import main

GOOD = "max-age=31536000; includeSubDomains; preload"


class _LyingStr(str):
    def __iter__(self) -> Iterator[str]:
        return iter("abc")


class _LyingInt(int):
    def __str__(self) -> str:
        return "5\r\nSet-Cookie: x=1"

    def __format__(self, spec: str) -> str:
        return str(self)


def test_a_str_subclass_cannot_smuggle_a_line_break() -> None:
    with pytest.raises(HstsError):
        build(5, extensions={_LyingStr("x\r\nSet-Cookie: a=b"): None})
    with pytest.raises(HstsError):
        build(5, extensions={"x": _LyingStr("v\r\nSet-Cookie: a=b")})
    assert build(5, extensions={_LyingStr("ok"): _LyingStr("fine")}) == "max-age=5; ok=fine"


def test_an_int_subclass_cannot_smuggle_a_line_break() -> None:
    assert build(_LyingInt(5)) == "max-age=5"
    assert build(Hsts(_LyingInt(5))) == "max-age=5"
    assert type(Hsts(_LyingInt(5)).max_age) is int


def test_space_around_equals_in_max_age_is_refused_by_the_preload_checker() -> None:
    for header in ("max-age = 31536000", "max-age =31536000", "max-age= 31536000"):
        full = header + "; includeSubDomains; preload"
        assert [i.code for i in preload_issues(full)] == ["preload.max-age-spaced"], full
        assert [i.code for i in lint(full)] == ["max-age.spaced"]
    assert is_preloadable("max-age=31536000 ; includeSubDomains ; preload")


def test_a_max_age_the_preload_checker_cannot_read_is_refused() -> None:
    huge = "max-age=18446744073709551616; includeSubDomains; preload"
    assert next(i.code for i in preload_issues(huge)) == "preload.max-age-unreadable"
    assert not is_preloadable(huge)
    assert is_preloadable("max-age=18446744073709551615; includeSubDomains; preload")
    assert is_preloadable("max-age=000000000000000000000031536000; includeSubDomains; preload")


def test_a_folded_line_is_whitespace() -> None:
    header = "max-age=5;\r\n includeSubDomains;\n\tpreload"
    assert parse(header, strict=True) == Hsts(5, True, True)
    assert [(i.code, i.offset) for i in lint(header)] == [("obs-fold", 10), ("obs-fold", 31)]


def test_quoted_pairs_follow_rfc_9110() -> None:
    for char, offset in (("\x7f", 15), ("€", 15), ("\x01", 15), ("\t", None)):
        found = [i.offset for i in lint(f'max-age=5; x="\\{char}"') if i.code == "syntax"]
        assert found == ([] if offset is None else [offset]), repr(char)


def test_qdtext_stops_at_0xff() -> None:
    assert is_qdtext("\xff") and not is_qdtext("Ā") and not is_qdtext("€")


def test_resync_skips_quoted_semicolons() -> None:
    header = 'x y="a;max-age=9"; max-age=5'
    assert [(i.code, i.offset) for i in lint(header)] == [("syntax", 2)]
    assert parse(header).max_age == 5


def test_an_empty_directive_points_at_its_semicolon() -> None:
    assert [i.offset for i in lint("max-age=5;")] == [9]
    assert [i.offset for i in lint("max-age=5;;")] == [10, 10]
    assert [i.offset for i in lint(";max-age=5")] == [0]


def test_a_broken_directive_still_counts_for_repeats() -> None:
    codes = [(i.code, i.offset) for i in lint('max-age="5; max-age=6')]
    assert codes == [("syntax", 8), ("duplicate", 12)]
    codes = [(i.code, i.offset) for i in lint('max-age=6; max-age="5')]
    assert codes == [("duplicate", 11), ("syntax", 19)]
    codes = [(i.code, i.offset) for i in lint("max-age=6 x; max-age=5")]
    assert codes == [("syntax", 10), ("duplicate", 13)]


@pytest.mark.parametrize("value", [None, 5, {"max-age=5": 1}, 1.5])
def test_input_that_is_not_text_is_a_clear_type_error(value: object) -> None:
    with pytest.raises(TypeError, match="str"):
        parse(value)  # type: ignore[arg-type]


def _run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stdin: bytes
) -> tuple[int, dict[str, object]]:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin)))
    code = main(["--preload"])
    out = capsys.readouterr().out
    return code, (json.loads(out) if out else {})


@pytest.mark.parametrize(
    ("stdin", "code", "field"),
    [
        (
            b"HTTP/2 200\r\nStrict-Transport-Security: max-age=31536000;\r\n"
            b" includeSubDomains; preload\r\n\r\n",
            0,
            GOOD,
        ),
        (b"HTTP/2 200\r\nx-foo: a\r\n strict-transport-security: max-age=5\r\n\r\n", 2, None),
        (b"HTTP/2 200\r\nserver: x\r\n\r\nstrict-transport-security: " + GOOD.encode(), 2, None),
        (
            b"HTTP/1.1 301 Moved\r\nStrict-Transport-Security: max-age=0\r\n\r\n"
            b"HTTP/2 200\r\nstrict-transport-security: " + GOOD.encode() + b"\r\n\r\n",
            0,
            GOOD,
        ),
        (b"Date: x\r\nStrict-Transport-Security: " + GOOD.encode() + b"\r\n", 0, GOOD),
        (b"\r\n\r\nHTTP/2 200\r\nstrict-transport-security: " + GOOD.encode(), 0, GOOD),
        (b"HTTP/2 200\rstrict-transport-security: " + GOOD.encode() + b"\r\r", 0, GOOD),
        (b"", 2, None),
        (b"\r\n \n", 2, None),
    ],
)
def test_response_heads_are_read_like_curl_prints_them(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdin: bytes,
    code: int,
    field: str | None,
) -> None:
    exit_code, report = _run(monkeypatch, capsys, stdin)
    assert exit_code == code
    assert report.get("field") == field


def test_a_terminal_without_input_is_a_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Tty(io.StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr(sys, "stdin", _Tty())
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2
