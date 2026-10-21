"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with HSTSHEADER_E2E=1. With
HSTSHEADER_E2E_PYPI=1 as well, the release on PyPI is installed first and upgraded in place.
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
assert importlib.metadata.version("hstsheader") == hstsheader.__version__ == "1.0.0"
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
for bad in (lambda: Hsts("5"), lambda: build(5, preload=1), lambda: parse(b"max-age=1")):
    try:
        bad()
    except TypeError as error:
        assert not isinstance(error, HstsError)
    else:
        raise AssertionError("expected TypeError")
assert Hsts.__module__ == "hstsheader"
assert len(lint("max-age=" + "x" * 10**6)[0].message) < 200
print("e2e ok")
"""

# 0.2.0 behaviour that 1.0.0 changed (see the CHANGELOG), and what both share.
BEFORE = r"""
import hstsheader
from hstsheader import Hsts, HstsError, parse
assert hstsheader.__version__ == "0.2.0"
try:
    Hsts("5")
except HstsError as error:
    assert error.code == "type"
assert parse("max-age=600; includeSubDomains") == Hsts(600, True)
print("0.2.0 ok")
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
    assert any(name.endswith(".dist-info/licenses/LICENSE") for name in names)
    entry_points = next(name for name in names if name.endswith("entry_points.txt"))
    text = zipfile.ZipFile(wheel).read(entry_points).decode()
    assert "hstsheader = hstsheader._cli:main" in text
    with tarfile.open(sdist) as archive:
        listing = [name.split("/", 1)[1] for name in archive.getnames() if "/" in name]
    assert not any(name.startswith(("IMPROVEMENTS-round", "CERT-1.0")) for name in listing)
    assert not any(name.startswith(".github") for name in listing)
    upstream = [name for name in listing if name.startswith("tests/upstream/")]
    assert upstream == ["tests/upstream/MANIFEST.json"], upstream
    assert "tests/test_sources.py" in listing and "scripts/fetch_upstream.py" in listing
    assert "LICENSE" in listing and "tests/oracle/go.sum" in listing


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dist = tmp_path_factory.mktemp("dist")
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("hstsheader-*.whl")
    (sdist,) = dist.glob("hstsheader-*.tar.gz")
    _check_artifacts(wheel, sdist)
    return wheel


def _venv(where: Path) -> Path:
    venv.create(where, with_pip=True)
    return where / ("Scripts" if sys.platform == "win32" else "bin")


def _program(python: Path, code: str, work: Path, expected: str) -> None:
    # Run from an empty folder with -I so the source tree cannot shadow the install.
    result = _run(python, "-I", "-c", code, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == expected


@pytest.mark.skipif(os.environ.get("HSTSHEADER_E2E_PYPI") != "1", reason="needs PyPI access")
def test_upgrade_in_place_from_the_pypi_release(wheel: Path, tmp_path: Path) -> None:
    python = _venv(tmp_path / "venv") / "python"
    work = tmp_path / "work"
    work.mkdir()
    old = _run(python, "-m", "pip", "install", "-q", "hstsheader==0.2.0")
    assert old.returncode == 0, old.stderr
    _program(python, BEFORE, work, "0.2.0 ok")
    new = _run(python, "-m", "pip", "install", "-q", "--upgrade", wheel)
    assert new.returncode == 0, new.stderr
    _program(python, PROGRAM, work, "e2e ok")


def test_installed_wheel_end_to_end(wheel: Path, tmp_path: Path) -> None:
    bindir = _venv(tmp_path / "venv")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr
    work = tmp_path / "work"
    work.mkdir()
    _program(python, PROGRAM, work, "e2e ok")

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
    version = _run(script, "--version", cwd=work)
    assert version.returncode == 0 and version.stdout.decode().split() == ["hstsheader", "1.0.0"]
