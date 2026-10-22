"""More contracts from the seventh round of independent QA for 1.0.0: where each finding
points, the preload checks on a policy that skipped its checks, and the head reader."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hstsheader import Hsts, HstsError, build, is_preloadable, lint, parse, preload_issues
from hstsheader._cli import main
from hstsheader._head import field_lines, response_fields

SRC = str(Path(__file__).resolve().parents[1] / "src")

# (value, code, offset): the README says where each code points.
WHERE = [
    ("max-age=", "syntax", 8),  # the value ended too early: the length of the value
    ("max-age=1; a=", "syntax", 13),
    ("max-age=1; a  =  ", "syntax", 17),
    ('max-age=1; a="x', "syntax", 13),  # an unterminated quoted string: its opening quote
    ('max-age=1; a="x\\', "syntax", 13),
    ("max-age=1; a b", "syntax", 13),  # else the first bad character
    ("max-age =31536000", "max-age.spaced", 0),  # max-age.spaced: the directive
    ("  max-age= 31536000", "max-age.spaced", 2),
    ("x; max-age", "max-age.no-value", 3),
    ("max-age= x1", "max-age.not-digits", 9),  # a max-age value finding: the value
    ('max-age="x"', "max-age.not-digits", 8),  # its opening quote when quoted
    ("max-age=01", "max-age.leading-zero", 8),
    ('max-age = "1"', "max-age.quoted", 10),
    ("max-age=" + "9" * 11, "max-age.capped", 8),
    ("max-age=1; max-age=2", "duplicate", 11),  # a directive finding: its name
    ("max-age=1;  includeSubDomains=1", "value-not-allowed", 12),
    ("max-age=1; preload=1", "preload-value", 11),
    ("max-age=1;  foo", "unknown-directive", 12),
    ("max-age=1;", "empty-directive", 9),  # an extra semicolon
    ("max-age=1\r", "control-character", 9),
    ("max-age=1;\r\n a", "obs-fold", 10),
    ("", "max-age.missing", None),  # about the header as a whole: no offset
    ("max-age=0; includeSubDomains", "max-age.zero-subdomains", None),
]


@pytest.mark.parametrize(("value", "code", "offset"), WHERE)
def test_each_code_points_where_the_readme_says(value: str, code: str, offset: int | None) -> None:
    assert [i.offset for i in lint(value) if i.code == code] == [offset]


def test_an_offset_may_be_the_length_of_the_value() -> None:
    value = "max-age="
    with pytest.raises(HstsError) as caught:
        parse(value, strict=True)
    assert caught.value.offset == len(value)
    assert str(caught.value).endswith("found the end (at offset 8)")


class Unchecked(Hsts):
    def __post_init__(self) -> None:
        pass


def test_build_checks_a_policy_again() -> None:
    with pytest.raises(TypeError):
        build(Unchecked("600\r\nSet-Cookie: session=evil"))  # type: ignore[arg-type]
    policy = Hsts(600)
    object.__setattr__(policy, "max_age", "1\r\nX-Injected: 1")
    with pytest.raises(TypeError):
        build(policy)
    with pytest.raises(HstsError) as caught:
        build(Unchecked(-5))
    assert caught.value.code == "max-age.negative"
    with pytest.raises(HstsError) as caught:
        build(Unchecked(10**30))
    assert caught.value.code == "max-age.too-large"
    with pytest.raises(TypeError):
        build(Unchecked(1.5))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        build(Unchecked(600, include_subdomains="yes"))  # type: ignore[arg-type]
    assert build(Unchecked(600, preload=True)) == "max-age=600; preload"


class Liar:
    max_age = "600"
    include_subdomains = True
    preload = True

    @property  # type: ignore[misc]
    def __class__(self) -> type:
        return Hsts


@pytest.mark.parametrize("check", [preload_issues, is_preloadable])
def test_the_preload_checks_check_a_policy_again(check: object) -> None:
    assert callable(check)
    for bad, error in [
        (Unchecked("600"), TypeError),  # type: ignore[arg-type]
        (Unchecked(31536000, include_subdomains=1), TypeError),  # type: ignore[arg-type]
        (Liar(), TypeError),
        (Unchecked(-5), HstsError),
        (Unchecked(10**30), HstsError),
    ]:
        assert isinstance(bad, Hsts)
        with pytest.raises(error):
            check(bad)
    good = Unchecked(31536000, include_subdomains=True, preload=True)
    assert check(good) in ((), True)


FIELD_ONLY = (
    "HTTP/1.1 200 OK\r\nstrict-transport-security\r\n"
    "Strict-Transport-Security: max-age=31536000\r\n\r\n"
)


def test_a_line_named_like_the_field_without_a_colon_is_ignored() -> None:
    assert response_fields(FIELD_ONLY) == [["max-age=31536000"]]
    assert field_lines(FIELD_ONLY) == ["max-age=31536000"]
    assert field_lines(FIELD_ONLY.replace("\r\nStrict", "\r\nX: 1\r\nStrict")) == [
        "max-age=31536000"
    ]


def test_the_command_line_ignores_a_field_name_without_a_colon() -> None:
    done = subprocess.run(
        [sys.executable, "-m", "hstsheader"],
        input=FIELD_ONLY.encode("latin-1"),
        capture_output=True,
        env={**os.environ, "PYTHONPATH": SRC},
        check=False,
    )
    report = json.loads(done.stdout)
    assert (done.returncode, report["field"], report["honoured"]) == (0, "max-age=31536000", True)
    assert report["issues"] == []


def test_the_command_line_does_not_read_flags_inside_a_closed_quoted_string(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(['max-age=600; a="\x01;includeSubDomains;"']) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["policy"] == {"max_age": 600, "include_subdomains": False, "preload": False}
    assert [(i["code"], i["offset"]) for i in report["issues"]] == [("syntax", 16)]
