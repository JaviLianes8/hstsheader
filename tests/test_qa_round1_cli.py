"""Command line contracts added after the first round of independent QA for 1.0.0.

Each test failed on c8a317c, the commit the reviewers checked, except the one for a header
with warnings only, which pins behaviour a mutant changed there without any test noticing.
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
from hstsheader._head import field_lines

GOOD = "max-age=63072000; includeSubDomains; preload"
SRC = str(Path(__file__).resolve().parents[1] / "src")


def _run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *argv: str, stdin: bytes
) -> tuple[int, dict[str, object]]:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin)))
    code = main(list(argv))
    out = capsys.readouterr().out
    return code, (json.loads(out) if out else {})


def test_the_first_response_of_a_redirect_chain_is_checked(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = (
        b"HTTP/1.1 301 Moved Permanently\r\nLocation: https://www.example.com/\r\n"
        b"Strict-Transport-Security: max-age=300\r\n\r\n"
        b"HTTP/1.1 200 OK\r\nStrict-Transport-Security: " + GOOD.encode() + b"\r\n\r\n"
    )
    code, report = _run(monkeypatch, capsys, "--preload", stdin=head)
    assert code == 1 and report["field"] == "max-age=300" and report["preloadable"] is False


def test_a_redirect_without_the_field_is_reported_as_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = b"HTTP/1.1 301 Moved\r\nLocation: /x\r\n\r\nHTTP/2 200\r\nstrict-transport-security: "
    code, report = _run(monkeypatch, capsys, "--preload", stdin=head + GOOD.encode())
    assert code == 2 and report == {}


def test_a_good_base_domain_is_preloadable_whatever_it_redirects_to(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = (
        b"HTTP/2 301\r\nstrict-transport-security: " + GOOD.encode() + b"\r\nlocation: /w\r\n\r\n"
        b"HTTP/2 200\r\nserver: x\r\n\r\n"
    )
    code, report = _run(monkeypatch, capsys, "--preload", stdin=head)
    assert code == 0 and report["field"] == GOOD and report["preloadable"] is True


@pytest.mark.parametrize(
    "interim",
    [
        "HTTP/1.1 100 Continue\r\n\r\n",
        "HTTP/1.1 103 Early Hints\r\nLink: </s.css>; rel=preload\r\n\r\n",
        "HTTP/1.1 200 Connection established\r\n\r\n",
    ],
)
def test_interim_and_proxy_heads_are_skipped(interim: str) -> None:
    head = interim + "HTTP/1.1 301 Moved\r\nStrict-Transport-Security: max-age=1\r\n\r\n"
    assert field_lines(head + "HTTP/2 200\r\nStrict-Transport-Security: max-age=2\r\n") == [
        "max-age=1"
    ]


def test_a_header_with_only_warnings_is_honoured(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report = _run(monkeypatch, capsys, "max-age=600; foo", stdin=b"")
    assert code == 0 and report["honoured"] is True
    assert report["issues"] == [
        {
            "code": "unknown-directive",
            "severity": "warning",
            "offset": 13,
            "message": "unknown directive foo is ignored",
        }
    ]


def test_a_value_on_preload_is_honoured_but_not_preloadable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report = _run(monkeypatch, capsys, "--preload", "max-age=600; preload=yes", stdin=b"")
    assert code == 1 and report["honoured"] is True and report["preloadable"] is False
    code, report = _run(monkeypatch, capsys, "max-age=600; preload=yes", stdin=b"")
    assert code == 0 and report["honoured"] is True


class _ClosedPipe(io.StringIO):
    def write(self, text: str) -> int:
        raise BrokenPipeError(32, "Broken pipe")


def test_a_closed_output_pipe_keeps_the_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", _ClosedPipe())
    assert main(["max-age=600; foo"]) == 0
    monkeypatch.setattr(sys, "stdout", _ClosedPipe())
    assert main(["max-age=600; max-age=5"]) == 1


def test_a_reader_that_stops_early_gets_no_traceback(tmp_path: Path) -> None:
    names = "; ".join(f"x{i}" for i in range(6000))
    head = tmp_path / "head.txt"
    head.write_bytes(b"HTTP/2 200\r\nstrict-transport-security: max-age=1; " + names.encode())
    err = tmp_path / "err.txt"
    command = [sys.executable, "-c", "from hstsheader._cli import main; raise SystemExit(main())"]
    with head.open("rb") as stdin, err.open("wb") as stderr:
        child = subprocess.Popen(
            command,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=stderr,
            env={**os.environ, "PYTHONPATH": SRC},
        )
        assert child.stdout is not None
        assert child.stdout.read(16)
        child.stdout.close()
        status = child.wait(timeout=120)
    assert status == 0
    assert "Traceback" not in err.read_text(encoding="utf-8", errors="replace")
