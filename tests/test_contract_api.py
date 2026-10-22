"""The stable 1.0 surface: signatures, types, error classes and the documented codes."""

from __future__ import annotations

import copy
import dataclasses
import inspect
import pickle
import re
from pathlib import Path

import pytest

import hstsheader
from hstsheader import Hsts, HstsError, Issue, build, is_preloadable, lint, parse, preload_issues

README = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
EMPTY = inspect.Parameter.empty
POS = inspect.Parameter.POSITIONAL_OR_KEYWORD
KW = inspect.Parameter.KEYWORD_ONLY

SIGNATURES = {
    "parse": [("header", POS, EMPTY), ("strict", KW, False)],
    "lint": [("header", POS, EMPTY)],
    "preload_issues": [("header", POS, EMPTY)],
    "is_preloadable": [("header", POS, EMPTY)],
    "build": [
        ("max_age", POS, EMPTY),
        ("include_subdomains", KW, None),
        ("preload", KW, None),
        ("extensions", KW, None),
    ],
    "Hsts": [("max_age", POS, EMPTY), ("include_subdomains", POS, False), ("preload", POS, False)],
    "Issue": [
        ("code", POS, EMPTY),
        ("message", POS, EMPTY),
        ("severity", POS, EMPTY),
        ("offset", POS, None),
    ],
    "HstsError": [("message", POS, EMPTY), ("code", KW, "invalid"), ("offset", KW, None)],
}


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_signatures_are_pinned(name: str) -> None:
    params = inspect.signature(getattr(hstsheader, name)).parameters.values()
    assert [(p.name, p.kind, p.default) for p in params] == SIGNATURES[name]


@pytest.mark.parametrize("cls", [Hsts, Issue, HstsError])
def test_public_classes_report_the_public_module(cls: type) -> None:
    assert cls.__module__ == "hstsheader"
    assert getattr(hstsheader, cls.__qualname__) is cls


def test_hsts_and_issue_fields_are_pinned() -> None:
    assert [f.name for f in dataclasses.fields(Hsts)] == [
        "max_age",
        "include_subdomains",
        "preload",
    ]
    assert [f.name for f in dataclasses.fields(Issue)] == ["code", "message", "severity", "offset"]


def test_values_pickle_copy_hash_and_compare() -> None:
    policy = Hsts(5, True, False)
    issue = Issue("syntax", "m", "error", 3)
    for value in (policy, issue):
        assert pickle.loads(pickle.dumps(value)) == value
        assert copy.deepcopy(value) == value
        assert hash(value) == hash(copy.copy(value))
    assert Hsts(5) != Hsts(6) and {Hsts(5), Hsts(5)} == {Hsts(5)}


def test_hsts_error_keeps_code_and_offset_through_pickle_and_copy() -> None:
    error = HstsError("bad", code="syntax", offset=7)
    for clone in (pickle.loads(pickle.dumps(error)), copy.copy(error), copy.deepcopy(error)):
        assert type(clone) is HstsError
        assert (clone.code, clone.offset, str(clone)) == ("syntax", 7, "bad (at offset 7)")
        assert clone.args == error.args


def test_hsts_error_is_a_value_error_not_a_type_error() -> None:
    assert issubclass(HstsError, ValueError) and not issubclass(HstsError, TypeError)


def test_return_types_are_exact() -> None:
    assert type(parse("max-age=1")) is Hsts
    assert type(parse("max-age=1").max_age) is int
    found = lint("max-age=1; x")
    assert type(found) is tuple and all(type(issue) is Issue for issue in found)
    assert type(preload_issues("max-age=1")) is tuple
    assert is_preloadable("max-age=1") is False
    assert type(build(1)) is str


def _table(heading: str) -> dict[str, str]:
    """Code to severity, from the table under one README heading."""
    section = README.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| `([a-z0-9.-]+)` \| (error|warning) \|", section, re.MULTILINE)
    return dict(rows)


# One input per documented code; together they must produce exactly the README table.
CODE_EXAMPLES = {
    "syntax": "max-age=1; a b",
    "control-character": "max-age=1\r",
    "max-age.missing": "preload",
    "max-age.no-value": "max-age",
    "max-age.not-digits": "max-age=1a",
    "duplicate": "max-age=1; max-age=2",
    "value-not-allowed": "max-age=1; includeSubDomains=1",
    "preload-value": "max-age=1; preload=1",
    "max-age.leading-zero": "max-age=01",
    "max-age.capped": "max-age=2147483649",
    "max-age.quoted": 'max-age="1"',
    "max-age.spaced": "max-age = 1",
    "obs-fold": "max-age=1;\r\n preload",
    "max-age.zero-subdomains": "max-age=0; includeSubDomains",
    "empty-directive": "max-age=1;",
    "unknown-directive": "max-age=1; x",
    "multiple-fields": ["max-age=1", "max-age=2"],
}


def test_every_documented_lint_code_is_produced_with_its_severity() -> None:
    table = _table("Lint a header")
    assert set(CODE_EXAMPLES) | {"field.missing"} == set(table)
    for code, header in CODE_EXAMPLES.items():
        found = [issue for issue in lint(header) if issue.code == code]
        assert found and all(issue.severity == table[code] for issue in found), code
    assert [(i.code, i.severity) for i in lint([])] == [("field.missing", "error")]


def test_every_documented_preload_code_is_produced() -> None:
    table = _table("Check preload eligibility")
    produced: dict[str, str] = {}
    for header in (
        "max-age=0",
        'max-age="31536000"; includeSubDomains; preload',
        "max-age = 31536000; includeSubDomains; preload",
        "max-age=18446744073709551616; includeSubDomains; preload",
        "max-age=400000000; includeSubDomains; preload",
        "max-age=1; preload",
        "max-age=1; includeSubDomains",
        "max-age=31536000; includeSubDomains; preload=1",
        "max-age=31536000; includeSubDomains; preload; max-agex",
    ):
        for issue in preload_issues(header):
            if issue.code.startswith("preload."):
                assert produced.setdefault(issue.code, issue.severity) == issue.severity
    assert produced == table
