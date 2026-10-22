"""Command line contracts added after the third round of independent QA for 1.0.0.

Every test here failed on 2fd8202, the commit the reviewers checked, except the one that
passes a value with no standard input, which pins the path that already worked.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hstsheader._cli import main

SRC = str(Path(__file__).resolve().parents[1] / "src")


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *argv: str,
    stdin: bytes,
) -> tuple[int, dict[str, object]]:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin)))
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_no_stdin_and_no_value_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", None)
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2
    assert "give a value" in capsys.readouterr().err


def test_no_stdin_with_a_value_still_checks_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", None)
    assert main(["max-age=600"]) == 0
    assert json.loads(capsys.readouterr().out)["honoured"] is True


def test_a_process_started_without_stdin_exits_with_a_usage_error(tmp_path: Path) -> None:
    code = (
        "import sys; sys.stdin = None; from hstsheader._cli import main; raise SystemExit(main())"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": SRC},
        cwd=tmp_path,
        timeout=120,
    )
    assert done.returncode == 2
    assert b"Traceback" not in done.stderr and b"give a value" in done.stderr


def test_a_line_of_spaces_does_not_end_the_head(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = b"HTTP/1.1 200 OK\r\nX-A: b\r\n \r\nStrict-Transport-Security: max-age=1\r\n\r\n"
    code, report = _run(monkeypatch, capsys, stdin=head)
    assert (code, report["field"], report["honoured"]) == (0, "max-age=1", True)


def test_a_misread_header_is_not_preloadable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = (
        b"HTTP/2 200\r\nstrict-transport-security: "
        b"max-age=31536000; includeSubDomains; preload; max-agex=5\r\n\r\n"
    )
    code, report = _run(monkeypatch, capsys, "--preload", stdin=head)
    assert (code, report["honoured"], report["preloadable"]) == (1, True, False)
    found = report["preload_issues"]
    assert [(i["code"], i["severity"], i["offset"]) for i in found] == [  # type: ignore[attr-defined]
        ("preload.misread", "error", 46)
    ]
