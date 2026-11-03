"""Command line errors omit synthetic argument values and stay bounded."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = str(Path(__file__).resolve().parents[1] / "src")


@pytest.mark.parametrize("size", [0, 6000])
@pytest.mark.parametrize(
    "arguments",
    [
        ["--preload={marker}", "max-age=1"],
        ["max-age=1", "{marker}"],
        ["--{marker}", "max-age=1"],
        ["--help={marker}"],
        ["--version={marker}"],
    ],
    ids=["flag-value", "extra-value", "unknown-option", "help-value", "version-value"],
)
def test_argument_errors_omit_values_and_stay_bounded(arguments: list[str], size: int) -> None:
    marker = "private_argument_canary_" + "x" * size
    done = subprocess.run(
        [sys.executable, "-m", "hstsheader", *(arg.format(marker=marker) for arg in arguments)],
        input=b"",
        capture_output=True,
        env={**os.environ, "PYTHONPATH": SRC},
        timeout=30,
        check=False,
    )
    assert done.returncode == 2
    assert done.stdout == b""
    assert b"private_argument_canary_" not in done.stderr
    assert 0 < len(done.stderr) < 512
    assert b"usage:" in done.stderr and b"--help" in done.stderr
    assert b"Traceback" not in done.stderr
