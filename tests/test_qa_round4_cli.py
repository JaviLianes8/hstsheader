"""Command line contracts added after the fourth round of independent QA for 1.0.0.

Every test here failed on 370723f, the commit the reviewers checked.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SRC = str(Path(__file__).resolve().parents[1] / "src")
HEAD = b"HTTP/1.1 200 OK\r\nStrict-Transport-Security: %s\r\n\r\n"
GOOD = b"max-age=31536000; includeSubDomains; preload"


def _cli(*argv: str, stdin: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "hstsheader", *argv],
        input=stdin,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": SRC},
        check=False,
    )


def test_a_utf8_space_cut_out_of_a_quote_is_not_preloadable() -> None:
    value = GOOD + b'; note="x;\xe2\x80\x80max-age=1"'
    done = _cli("--preload", stdin=HEAD % value)
    report = json.loads(done.stdout)
    assert (done.returncode, report["honoured"], report["preloadable"]) == (1, True, False)
    found = [(i["code"], i["offset"]) for i in report["preload_issues"]]
    assert found == [("preload.misread", value.index(b"max-age=1"))]


def test_a_lone_no_break_space_octet_is_preloadable() -> None:
    done = _cli("--preload", stdin=HEAD % (GOOD + b'; note="x;\xa0max-age=1;y"'))
    report = json.loads(done.stdout)
    assert (done.returncode, report["preloadable"], report["preload_issues"]) == (0, True, [])


def test_standard_input_that_cannot_be_read_is_a_usage_error(tmp_path: Path) -> None:
    target = tmp_path / "write-only"
    with target.open("wb") as write_only:
        done = subprocess.run(
            [sys.executable, "-m", "hstsheader", "--preload"],
            stdin=write_only,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": SRC},
            check=False,
        )
    assert done.returncode == 2
    assert done.stdout == b""
    assert b"Traceback" not in done.stderr
    assert b"standard input cannot be read" in done.stderr
