"""The README examples run and print what their comments say; docs and versions agree."""

from __future__ import annotations

import contextlib
import io
import itertools
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import hstsheader

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _python_blocks() -> list[str]:
    return re.findall(r"```python\n(.*?)```", README, flags=re.DOTALL)


def _expected_output(block: str) -> list[str]:
    """Each print line is followed by the comment lines that hold what it prints."""
    expected: list[str] = []
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if not line.strip().startswith("print("):
            continue
        for following in itertools.takewhile(
            lambda text: text.strip().startswith("# "), lines[index + 1 :]
        ):
            expected.append(following.strip()[2:])
    return expected


def test_every_readme_example_runs_and_prints_its_comment() -> None:
    checked = 0
    for block in _python_blocks():
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(compile(block, "README.md", "exec"), {"__name__": "readme"})
        expected = _expected_output(block)
        assert expected, block
        assert out.getvalue().splitlines() == expected
        checked += len(expected)
    assert len(_python_blocks()) == 5
    assert checked == 13


def test_every_print_in_the_readme_shows_its_output() -> None:
    for block in _python_blocks():
        lines = block.splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith("print("):
                assert lines[index + 1].strip().startswith("# "), line


def test_the_api_table_lists_every_public_name() -> None:
    table = README.split("## API", 1)[1].split("\n## ", 1)[0]
    for name in hstsheader.__all__:
        assert f"`{name}" in table, name


def test_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == hstsheader.__version__


def test_changelog_has_an_entry_for_this_version() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{hstsheader.__version__}]" in text


def _tracked_files() -> list[Path]:
    """Files under version control; local venvs and build folders are never scanned."""
    listing = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [ROOT / name for name in listing.split("\0") if name]


def test_no_em_dash_anywhere_in_the_tree() -> None:
    files = _tracked_files()
    assert ROOT / "README.md" in files
    for path in files:
        if path.suffix in {".py", ".md", ".toml", ".ps1", ".txt", ".yml", ".json"}:
            assert chr(0x2014) not in path.read_text(encoding="utf-8"), path


def test_source_files_stay_under_two_hundred_lines() -> None:
    for path in [*ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("tests").rglob("*.py")]:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200, path


GUIDE = (ROOT / "GUIDE.md").read_text(encoding="utf-8")


def test_every_build_error_code_in_the_guide_is_raised() -> None:
    section = GUIDE.split("## Errors\n", 1)[1].split("\n## ", 1)[0]
    documented = set(re.findall(r"^\| `([a-z.-]+)` \|", section, flags=re.MULTILINE))
    calls: dict[str, Callable[[], object]] = {
        "max-age.negative": lambda: hstsheader.Hsts(-1),
        "max-age.too-large": lambda: hstsheader.build(2**31 + 1),
        "build.name": lambda: hstsheader.build(1, extensions={"preload": None}),
        "build.value": lambda: hstsheader.build(1, extensions={"x": "\t\x7f"}),
        "duplicate": lambda: hstsheader.build(1, extensions={"a": None, "A": None}),
    }
    assert documented == set(calls)
    for code, call in calls.items():
        try:
            call()
        except hstsheader.HstsError as error:
            assert error.code == code
        else:
            raise AssertionError(code)


def test_the_guide_lists_the_command_line_keys_in_order() -> None:
    section = GUIDE.split("## Command line\n", 1)[1].split("\n## ", 1)[0]
    keys = re.findall(r"^\| `([a-z_]+)` \|", section, flags=re.MULTILINE)
    assert keys == ["field", "honoured", "policy", "issues", "preloadable", "preload_issues"]
