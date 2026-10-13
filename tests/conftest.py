from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"


def read_upstream(name: str) -> str:
    """Return a third-party reference file as text.

    The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their
    tests skip while a file is absent and fail if it differs from the manifest.
    """
    path = UPSTREAM / name
    if not path.is_file():
        pytest.skip(f"{name} is not fetched; run python scripts/fetch_upstream.py")
    entry = json.loads((UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8"))[name]
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == entry["sha256"], f"{name} differs from MANIFEST"
    return body.decode("utf-8")


@pytest.fixture(scope="session")
def rfc6797() -> str:
    """RFC 6797, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc6797.txt")


@pytest.fixture(scope="session")
def rfc2616() -> str:
    """RFC 2616, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc2616.txt")


@pytest.fixture(scope="session")
def rfc9110() -> str:
    """RFC 9110, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc9110.txt")


@pytest.fixture(scope="session")
def rfc9111() -> str:
    """RFC 9111, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc9111.txt")


@pytest.fixture(scope="session")
def preload_page() -> str:
    """The hstspreload.org front page, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("hstspreload.html")


@pytest.fixture(scope="session")
def preload_checker_tests() -> str:
    """chromium/hstspreload header_test.go, see tests/upstream/MANIFEST.json."""
    return read_upstream("hstspreload-header_test.go")


@pytest.fixture(scope="session")
def chromium_parser() -> str:
    """Chromium's HSTS header parser, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("chromium-http_security_headers.cc")


@pytest.fixture(scope="session")
def chromium_limits() -> str:
    """Chromium's HSTS constants, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("chromium-http_security_headers.h")


@pytest.fixture(scope="session")
def preload_checker() -> str:
    """chromium/hstspreload header.go, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("hstspreload-header.go")
