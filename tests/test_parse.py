import pytest

from hstsheader import Hsts, HstsError, parse


def test_parse_full_header() -> None:
    result = parse("max-age=31536000; includeSubDomains; preload")
    assert result == Hsts(max_age=31536000, include_subdomains=True, preload=True)


def test_parse_minimal_header() -> None:
    assert parse("max-age=0") == Hsts(max_age=0)


def test_flags_absent_default_to_false() -> None:
    result = parse("max-age=600")
    assert result.include_subdomains is False
    assert result.preload is False


def test_include_subdomains_present_without_preload() -> None:
    result = parse("max-age=600; includeSubDomains")
    assert result.include_subdomains is True
    assert result.preload is False


def test_directive_names_are_case_insensitive() -> None:
    result = parse("MAX-AGE=100; INCLUDESUBDOMAINS; PRELOAD")
    assert result == Hsts(max_age=100, include_subdomains=True, preload=True)


def test_mixed_case_directive_names() -> None:
    assert parse("Max-Age=5; IncludeSubDomains").include_subdomains is True


def test_quoted_max_age_value_is_accepted() -> None:
    assert parse('max-age="31536000"') == Hsts(max_age=31536000)


def test_tolerates_extra_whitespace_and_empty_directives() -> None:
    result = parse("  max-age = 600 ;; includeSubDomains ; ")
    assert result == Hsts(max_age=600, include_subdomains=True)


def test_unknown_directives_are_ignored() -> None:
    result = parse("max-age=600; something=else; preload")
    assert result == Hsts(max_age=600, preload=True)


def test_missing_max_age_raises() -> None:
    with pytest.raises(HstsError):
        parse("includeSubDomains; preload")


def test_non_integer_max_age_raises() -> None:
    with pytest.raises(HstsError):
        parse("max-age=soon")


def test_negative_max_age_raises() -> None:
    with pytest.raises(HstsError):
        parse("max-age=-1")


def test_max_age_without_value_raises() -> None:
    with pytest.raises(HstsError):
        parse("max-age; preload")


def test_the_first_max_age_wins_in_tolerant_mode() -> None:
    assert parse("max-age=600; max-age=5").max_age == 600


def test_a_broken_max_age_is_skipped_for_a_later_valid_one() -> None:
    assert parse("max-age=soon; max-age=5").max_age == 5


def test_only_ascii_digits_count_as_max_age() -> None:
    for value in ("\uff17", "\u0661\u0662", "\u00b2", "1_0", "+7", "0x10", "1.5", "1e3"):
        with pytest.raises(HstsError):
            parse(f"max-age={value}")


def test_a_huge_max_age_is_read_as_two_to_the_31() -> None:
    assert parse("max-age=" + "9" * 5000).max_age == 2**31
    assert parse("max-age=2147483649").max_age == 2**31
    assert parse("max-age=2147483648").max_age == 2**31
    assert parse("max-age=2147483647").max_age == 2**31 - 1


def test_leading_zeros_do_not_count_toward_the_ceiling() -> None:
    assert parse("max-age=" + "0" * 50 + "31536000").max_age == 31536000


def test_quoted_pairs_are_unescaped_before_the_digit_check() -> None:
    assert parse('max-age="\\3\\1"').max_age == 31


def test_a_valueless_directive_with_a_value_is_not_asserted() -> None:
    assert parse("max-age=600; includeSubDomains=no").include_subdomains is False
    assert parse('max-age=600; preload=""').preload is False


def test_a_broken_directive_does_not_hide_the_ones_after_it() -> None:
    result = parse('max-age=600; x=a b; includeSubDomains; y="no end; preload')
    assert result == Hsts(max_age=600, include_subdomains=True, preload=True)


def test_a_semicolon_inside_a_quoted_value_does_not_split() -> None:
    assert parse('max-age=600; x="a;preload"').preload is False


def test_cr_lf_cannot_smuggle_a_second_header() -> None:
    with pytest.raises(HstsError):
        parse("max-age=600\r\nSet-Cookie: a=b")


def test_bytes_are_refused_with_a_type_error() -> None:
    with pytest.raises(TypeError, match="latin-1"):
        parse(b"max-age=1")  # type: ignore[arg-type]


def test_only_the_first_field_line_is_read() -> None:
    assert parse(["max-age=5", "max-age=9; preload"]) == Hsts(max_age=5)


def test_no_field_line_at_all_raises() -> None:
    with pytest.raises(HstsError) as caught:
        parse([])
    assert caught.value.code == "field.missing"


def test_field_lines_must_be_text() -> None:
    with pytest.raises(TypeError):
        parse([b"max-age=1"])  # type: ignore[list-item]


def test_errors_name_the_rule_and_the_offset() -> None:
    with pytest.raises(HstsError) as caught:
        parse("preload; max-age=soon")
    assert caught.value.code == "max-age.not-digits"
    assert caught.value.offset == 17
    assert "offset 17" in str(caught.value)


def test_an_unreadable_max_age_reports_the_syntax_error() -> None:
    with pytest.raises(HstsError) as caught:
        parse("max-age=600 junk")
    assert caught.value.code == "syntax"
    assert caught.value.offset == 12


def test_every_field_line_is_checked_for_text_not_only_the_first() -> None:
    with pytest.raises(TypeError):
        parse(["max-age=1", 5])  # type: ignore[list-item]


def test_a_quoted_superscript_digit_is_not_a_number() -> None:
    with pytest.raises(HstsError) as caught:
        parse('max-age="\u00b2"')
    assert caught.value.code == "max-age.not-digits"


def test_a_quoted_semicolon_inside_a_broken_directive_does_not_start_a_directive() -> None:
    result = parse('max-age=1; x=a "b; preload; c"; includeSubDomains')
    assert result == Hsts(max_age=1, include_subdomains=True)
