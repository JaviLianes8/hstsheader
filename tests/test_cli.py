from __future__ import annotations

import io
import json
import sys

import pytest

from hstsheader._cli import main


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *argv: str,
    stdin: bytes = b"",
) -> tuple[int, dict[str, object], str]:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin)))
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, (json.loads(out) if out else {}), err


def test_a_good_value_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report, _ = _run(monkeypatch, capsys, "max-age=600; includeSubDomains")
    assert code == 0
    assert report["honoured"] is True and report["issues"] == []
    assert report["policy"] == {"max_age": 600, "include_subdomains": True, "preload": False}
    assert "preloadable" not in report


def test_an_ignored_value_exits_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report, _ = _run(monkeypatch, capsys, "max-age=600; max-age=5")
    assert code == 1
    assert report["honoured"] is False
    assert report["policy"] == {"max_age": 600, "include_subdomains": False, "preload": False}
    assert report["issues"] == [
        {
            "code": "duplicate",
            "severity": "error",
            "offset": 13,
            "message": "max-age appears more than once; every directive must be unique",
        }
    ]


def test_no_usable_max_age_gives_no_policy(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report, _ = _run(monkeypatch, capsys, "preload")
    assert code == 1 and report["policy"] is None


def test_preload_check(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    code, report, _ = _run(monkeypatch, capsys, "--preload", "max-age=600; preload")
    assert code == 1 and report["honoured"] is True and report["preloadable"] is False
    codes = [issue["code"] for issue in report["preload_issues"]]  # type: ignore[attr-defined]
    assert codes == ["preload.subdomains-missing", "preload.max-age-too-short"]
    good = "max-age=31536000; includeSubDomains; preload"
    code, report, _ = _run(monkeypatch, capsys, "--preload", good)
    assert code == 0 and report["preloadable"] is True and report["preload_issues"] == []


def test_preload_check_fails_when_browsers_ignore_the_header(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = "max-age=31536000; includeSubDomains; preload; includeSubDomains"
    code, report, _ = _run(monkeypatch, capsys, "--preload", bad)
    assert code == 1 and report["preloadable"] is False and report["preload_issues"] == []


def test_a_repeated_preload_is_not_honoured_by_the_rfc_but_still_preloadable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    header = "max-age=31536000; includeSubDomains; preload; preload"
    code, report, _ = _run(monkeypatch, capsys, "--preload", header)
    assert code == 0 and report["honoured"] is False and report["preloadable"] is True


def test_a_response_head_on_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = (
        b"HTTP/2 200\r\ncontent-type: text/html\r\n"
        b"strict-transport-security: max-age=63072000; includeSubDomains; preload\r\n"
        b"Strict-Transport-Security: max-age=0\r\n\r\n"
    )
    code, report, _ = _run(monkeypatch, capsys, "--preload", stdin=head)
    assert code == 0 and report["field"] == "max-age=63072000; includeSubDomains; preload"
    assert [issue["code"] for issue in report["issues"]] == ["multiple-fields"]  # type: ignore[attr-defined]


def test_a_head_without_the_field_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report, err = _run(monkeypatch, capsys, stdin=b"HTTP/1.1 200 OK\r\nServer: x\r\n\r\n")
    assert code == 2 and report == {} and "no Strict-Transport-Security" in err


def test_a_bare_value_on_stdin_and_a_value_with_its_field_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report, _ = _run(monkeypatch, capsys, stdin=b"max-age=5\r\n")
    assert code == 0 and report["field"] == "max-age=5"
    code, report, _ = _run(monkeypatch, capsys, "Strict-Transport-Security: max-age=7")
    assert code == 0 and report["field"] == "max-age=7"


def test_obs_text_from_stdin_is_kept_as_latin_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report, _ = _run(monkeypatch, capsys, stdin=b'max-age=5; x="caf\xe9"')
    assert code == 0 and report["field"] == 'max-age=5; x="caf\u00e9"'
