"""Command line contracts added after the second round of independent QA for 1.0.0.

The redirect and closed-stdout tests failed on 98e3f77, the commit the reviewers checked.
The others pin behaviour that was already right there but that a mutant could change
without any test noticing.
"""

from __future__ import annotations

import errno
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hstsheader._cli import main

GOOD = b"max-age=63072000; includeSubDomains; preload"
SRC = str(Path(__file__).resolve().parents[1] / "src")
REDIRECT = b"HTTP/1.1 301 Moved\r\nLocation: https://www.example.com/\r\n\r\n"
MISSING = {
    "code": "field.missing",
    "severity": "error",
    "offset": None,
    "message": "the first final response has no Strict-Transport-Security field; "
    "a later response in the input has one",
}


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *argv: str,
    stdin: bytes,
) -> tuple[int, dict[str, object], str]:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin)))
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, (json.loads(out) if out else {}), err


def test_a_later_field_after_a_redirect_without_one_is_a_rejection(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = REDIRECT + b"HTTP/1.1 200 OK\r\nStrict-Transport-Security: " + GOOD + b"\r\n\r\n"
    code, report, err = _run(monkeypatch, capsys, stdin=head)
    assert (code, err) == (1, "")
    assert report == {"field": None, "honoured": False, "policy": None, "issues": [MISSING]}
    code, report, err = _run(monkeypatch, capsys, "--preload", stdin=head)
    assert (code, err) == (1, "")
    assert report["preloadable"] is False and report["preload_issues"] == [MISSING]


def test_a_chain_without_the_field_anywhere_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = REDIRECT + b"HTTP/1.1 200 OK\r\nServer: x\r\n\r\n"
    code, report, err = _run(monkeypatch, capsys, "--preload", stdin=head)
    assert (code, report) == (2, {})
    assert err == "hstsheader: no Strict-Transport-Security field in the input\n"


@pytest.mark.parametrize(
    "head", [b"HTTP/1.1 200 Connection established\r\n\r\n", b"HTTP/1.1 100 Continue\r\n\r\n"]
)
def test_a_head_of_interim_responses_only_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], head: bytes
) -> None:
    code, report, err = _run(monkeypatch, capsys, stdin=head)
    assert (code, report) == (2, {})
    assert err == "hstsheader: no Strict-Transport-Security field in the input\n"


def test_no_stdout_at_all_keeps_the_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    assert main(["max-age=600"]) == 0
    assert main(["max-age=600; max-age=5"]) == 1


class _FullDisk(io.StringIO):
    def write(self, text: str) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")


def test_a_write_error_other_than_a_closed_pipe_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stdout", _FullDisk())
    with pytest.raises(OSError) as caught:
        main(["max-age=600"])
    assert caught.value.errno == errno.ENOSPC


def _child(code: str, tmp_path: Path, *, close_reader: bool) -> tuple[int, str]:
    err = tmp_path / "err.txt"
    with err.open("wb") as stderr:
        child = subprocess.Popen(
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr,
            env={**os.environ, "PYTHONPATH": SRC},
        )
        assert child.stdout is not None
        if close_reader:
            child.stdout.close()
        else:
            child.stdout.read()
        status = child.wait(timeout=120)
    return status, err.read_text(encoding="utf-8", errors="replace")


def test_a_small_report_to_a_reader_gone_before_any_write_is_quiet(tmp_path: Path) -> None:
    code = (
        "import time; time.sleep(1.5); from hstsheader._cli import main; "
        "raise SystemExit(main(['max-age=600']))"
    )
    assert _child(code, tmp_path, close_reader=True) == (0, "")


def test_a_process_started_without_stdout_keeps_the_verdict(tmp_path: Path) -> None:
    code = (
        "import sys; sys.stdout = None; from hstsheader._cli import main; "
        "raise SystemExit(main(['max-age=1']))"
    )
    assert _child(code, tmp_path, close_reader=False) == (0, "")
