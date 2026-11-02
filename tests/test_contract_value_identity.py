"""Value identity and error round-trip contracts, using hand-written examples."""

from __future__ import annotations

import copy
import pickle

import pytest

from hstsheader import Hsts, HstsError, Issue, lint, preload_issues


@pytest.mark.parametrize(
    "offset, message", [(None, "bad"), (0, "bad (at offset 0)"), (7, "bad (at offset 7)")]
)
def test_error_offset_message_survives_copy_and_pickle(offset: int | None, message: str) -> None:
    error = HstsError("bad", code="syntax", offset=offset)
    for value in (error, copy.copy(error), copy.deepcopy(error), pickle.loads(pickle.dumps(error))):
        assert type(value) is HstsError
        assert (value.code, value.offset, str(value), value.args) == (
            "syntax",
            offset,
            message,
            (message,),
        )


@pytest.mark.parametrize("offset", [None, 0, 4])
def test_issue_offsets_distinguish_values(offset: int | None) -> None:
    first = Issue("syntax", "bad", "error", 3)
    second = Issue("syntax", "bad", "error", offset)
    assert first != second
    assert len({first, second}) == 2


def test_issue_severity_distinguishes_values() -> None:
    error = Issue("duplicate", "repeated", "error", 3)
    warning = Issue("duplicate", "repeated", "warning", 3)
    assert error != warning
    assert len({error, warning}) == 2


def test_findings_at_distinct_positions_remain_distinct() -> None:
    found = [i for i in lint("max-age=1; x; x; x") if i.code == "unknown-directive"]
    assert len(set(found)) == 3


def test_duplicate_severity_distinguishes_lint_and_preload_findings() -> None:
    header = "max-age=31536000; includeSubDomains; preload; preload"
    error = next(i for i in lint(header) if i.code == "duplicate")
    warning = next(i for i in preload_issues(header) if i.code == "duplicate")
    assert (error.code, error.message, error.offset) == (
        warning.code,
        warning.message,
        warning.offset,
    )
    assert (error.severity, warning.severity) == ("error", "warning")
    assert error != warning
    assert len({error, warning}) == 2


@pytest.mark.parametrize("flag", ["include_subdomains", "preload"])
def test_policy_flags_distinguish_values(flag: str) -> None:
    first = Hsts(1)
    second = Hsts(1, **{flag: True})
    assert first != second
    assert len({first, second}) == 2
