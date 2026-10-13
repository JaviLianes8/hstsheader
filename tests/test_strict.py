from __future__ import annotations

import pytest

from hstsheader import Hsts, HstsError, parse


@pytest.mark.parametrize(
    ("header", "code", "offset"),
    [
        ("max-age=600; max-age=600", "duplicate", 13),
        ("max-age=600; preload; PRELOAD", "duplicate", 22),
        ("max-age=1; x; X", "duplicate", 14),
        ("max-age=600; includeSubDomains=1", "value-not-allowed", 13),
        ('max-age=600; preload=""', "value-not-allowed", 13),
        ("max-age=600, preload", "syntax", 11),
        ("max age=600", "syntax", 4),
        ("max-age=", "syntax", 8),
        ('max-age="600', "syntax", 8),
        ('max-age="6"0', "syntax", 11),
        ("max-age=600; x=a b", "syntax", 17),
        ("max-age=600; =x", "syntax", 13),
        ("max-age=600; x=\u00e9", "syntax", 15),
        ('max-age=600; x="\x01"', "syntax", 16),
        ('max-age=600; x="\\\x01"', "syntax", 17),
        ('max-age=600; x="\\', "syntax", 15),
        ('max-age=600; x="€"', "syntax", 16),
        ("max-age=600\x00", "control-character", 11),
        ("max-age=6\n00", "control-character", 9),
        ("includeSubDomains", "max-age.missing", None),
        ("", "max-age.missing", None),
        ("max-age", "max-age.no-value", 0),
        ("max-age=-1", "max-age.not-digits", 8),
        ('max-age=""', "max-age.not-digits", 8),
    ],
)
def test_strict_mode_refuses_what_a_user_agent_ignores(
    header: str, code: str, offset: int | None
) -> None:
    with pytest.raises(HstsError) as caught:
        parse(header, strict=True)
    assert (caught.value.code, caught.value.offset) == (code, offset)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("max-age=31536000", Hsts(31536000)),
        ("  MAX-AGE = 5 ;  includesubdomains ; Preload  ", Hsts(5, True, True)),
        ('max-age = "60"', Hsts(60)),
        ('max-age=60; report-uri="https://example.com/a;b"', Hsts(60)),
        ("max-age=60; ext=token; flag", Hsts(60)),
        (";; max-age=60 ;;", Hsts(60)),
        ("max-age=\t60\t;\tpreload", Hsts(60, preload=True)),
        ('max-age=60; x="caf\u00e9"', Hsts(60)),
        ("max-age=0; includeSubDomains", Hsts(0, True)),
    ],
)
def test_strict_mode_accepts_every_conforming_header(header: str, expected: Hsts) -> None:
    assert parse(header, strict=True) == expected


def test_strict_mode_reports_the_earliest_error() -> None:
    with pytest.raises(HstsError) as caught:
        parse("x y; max-age=1; max-age=1", strict=True)
    assert caught.value.offset == 2


def test_non_ascii_letters_never_form_a_directive_name() -> None:
    with pytest.raises(HstsError):
        parse("max-age=1; \u212aEY", strict=True)
    assert parse("max-age=1; preloa\u212a").preload is False
