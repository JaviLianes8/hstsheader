from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from hstsheader._checker import misreads

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


NO_PRELOAD = "max-age=31536000; includeSubDomains"
# The directives RFC 6797 reads in NO_PRELOAD, by offset, as the misread check takes them.
NO_PRELOAD_NAMES = {0: "max-age", NO_PRELOAD.index("include"): "includesubdomains"}
# Probes per header: one header holds thousands of pieces, as the checker reads each piece
# on its own, so a sweep of every code point takes a few hundred headers.
SWEEP_BATCH = 4096


def wire(code: int) -> str:
    """The UTF-8 octets of a code point, as a latin-1 decode shows them."""
    return chr(code).encode("utf-8", "surrogatepass").decode("latin-1")


# Each sweep over every code point outside ASCII: the code points, how one is written, and
# whether it stands before the name or after it. A character above U+00FF cannot stand
# after the name in a quoted string, which it ends, so RFC 6797 reads the name itself.
SWEEPS: dict[str, tuple[range, Callable[[int], str], bool]] = {
    "octets before": (range(0x80, 0x110000), wire, True),
    "octets after": (range(0x80, 0x110000), wire, False),
    "character before": (range(0x100, 0x110000), chr, True),
}


def sweep_headers(kind: str) -> Iterator[tuple[str, dict[int, int]]]:
    """Each header of a sweep, with the code point probed at each offset of ``preload``.

    Every probe is a piece ``x;<form>preload`` or ``x;preload<form>`` of one quoted value,
    so the checker misreads a piece exactly when it trims the code point from it.
    """
    codes, write, before = SWEEPS[kind]
    for first in range(codes.start, codes.stop, SWEEP_BATCH):
        parts = [f'{NO_PRELOAD}; note="x']
        size = len(parts[0])
        where: dict[int, int] = {}
        for code in range(first, min(first + SWEEP_BATCH, codes.stop)):
            form = write(code)
            where[size + 1 + (len(form) if before else 0)] = code
            parts.append(f";{form}preload" if before else f";preload{form}")
            size += len(parts[-1])
        parts.append(';y"')
        yield "".join(parts), where


def misread_codes(kind: str) -> tuple[set[int], list[str]]:
    """The code points of a sweep the misread check misreads, and any other misread.

    It calls the check ``preload_issues`` ends with directly, with the directives RFC 6797
    reads in these headers (those of NO_PRELOAD), as the RFC reading of millions of
    characters would take most of the time. test_qa_round6.py shows ``preload_issues``
    reports the same misreads on the headers that hold Go's spaces.
    """
    trimmed: set[int] = set()
    stray: list[str] = []
    for header, where in sweep_headers(kind):
        for issue in misreads(header, NO_PRELOAD_NAMES):
            exact = issue.message.endswith("reads 'preload' as preload")
            if issue.offset in where and exact:
                trimmed.add(where[issue.offset])
            else:
                stray.append(f"{issue.offset}: {issue.message}")
    return trimmed, stray


@pytest.fixture(scope="session")
def misread_sweep() -> dict[str, tuple[set[int], list[str]]]:
    """For each sweep, the code points the misread check misreads and any stray misread."""
    return {kind: misread_codes(kind) for kind in SWEEPS}
