"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with HSTSHEADER_E2E=1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("HSTSHEADER_E2E") != "1", reason="set HSTSHEADER_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources
import hstsheader
from hstsheader import (
    DELTA_SECONDS_MAX, PRELOAD_MIN_MAX_AGE, Hsts, HstsError, Issue, build, is_preloadable,
    lint, parse, preload_issues,
)

assert "site-packages" in hstsheader.__file__, hstsheader.__file__
assert importlib.metadata.version("hstsheader") == hstsheader.__version__
assert importlib.resources.files("hstsheader").joinpath("py.typed").is_file()

policy = parse(["max-age=63072000; includeSubDomains; preload", "max-age=0"])
assert policy == Hsts(63072000, True, True) and is_preloadable(policy)
assert parse('max-age="1"; max-age=2').max_age == 1
assert parse("max-age=" + "9" * 6000).max_age == DELTA_SECONDS_MAX == 2**31
assert [i.code for i in lint("max-age=1; x;")] == ["unknown-directive", "empty-directive"]
assert isinstance(lint("")[0], Issue)
assert [i.code for i in preload_issues("max-age=1; preload")] == [
    "preload.subdomains-missing", "preload.max-age-too-short",
]
assert PRELOAD_MIN_MAX_AGE == 31536000
header = build(Hsts(5, preload=True), extensions={"report-uri": "https://e.com/;x"})
assert header == 'max-age=5; preload; report-uri="https://e.com/;x"'
assert parse(header, strict=True) == Hsts(5, preload=True)
for call in (
    lambda: parse("max-age=1; max-age=1", strict=True),
    lambda: build(5, extensions={"x": "a\r\nSet-Cookie: b"}),
    lambda: Hsts(-1),
):
    try:
        call()
    except HstsError as error:
        assert isinstance(error, ValueError) and error.code
    else:
        raise AssertionError("expected HstsError")
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )


def _check_artifacts(wheel: Path, sdist: Path) -> None:
    names = zipfile.ZipFile(wheel).namelist()
    assert "hstsheader/py.typed" in names and "hstsheader/__main__.py" in names
    assert not any(name.startswith(("tests/", "scripts/")) for name in names)
    entry_points = next(name for name in names if name.endswith("entry_points.txt"))
    text = zipfile.ZipFile(wheel).read(entry_points).decode()
    assert "hstsheader = hstsheader._cli:main" in text
    with tarfile.open(sdist) as archive:
        listing = [name.split("/", 1)[1] for name in archive.getnames() if "/" in name]
    assert not any(name.startswith("IMPROVEMENTS-round") for name in listing)
    assert not any(name.startswith(".github") for name in listing)
    upstream = [name for name in listing if name.startswith("tests/upstream/")]
    assert upstream == ["tests/upstream/MANIFEST.json"], upstream
    assert "tests/test_sources.py" in listing and "scripts/fetch_upstream.py" in listing


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("hstsheader-*.whl")
    (sdist,) = dist.glob("hstsheader-*.tar.gz")
    _check_artifacts(wheel, sdist)

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == "e2e ok"

    head = b"HTTP/2 200\r\nStrict-Transport-Security: max-age=63072000; includeSubDomains\r\n\r\n"
    script = bindir / ("hstsheader.exe" if sys.platform == "win32" else "hstsheader")
    for command in ([script], [python, "-m", "hstsheader"]):
        shown = _run(*command, "--preload", cwd=work, stdin=head)
        assert shown.returncode == 1, shown.stderr
        report = json.loads(shown.stdout)
        assert report["honoured"] is True and report["preloadable"] is False
        assert report["policy"]["max_age"] == 63072000
    good = _run(script, "max-age=600", cwd=work)
    assert good.returncode == 0 and json.loads(good.stdout)["honoured"] is True
    usage = _run(script, cwd=work, stdin=b"HTTP/1.1 200 OK\r\n\r\n")
    assert usage.returncode == 2 and b"no Strict-Transport-Security" in usage.stderr
