"""Character classes from RFC 9110 section 5.6 and RFC 2616 section 2.2."""

from __future__ import annotations

import string

# tchar: any visible US-ASCII character except the delimiters.
TCHAR = frozenset(string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~")
DIGITS = frozenset(string.digits)
OWS = " \t"

# Upper-case ASCII only: str.lower() would also fold non-ASCII letters (the Kelvin sign
# becomes "k"), which must never turn into a directive name.
_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def ascii_lower(text: str) -> str:
    return text.translate(_ASCII_LOWER)


def is_token(text: str) -> bool:
    return bool(text) and all(char in TCHAR for char in text)


def is_qdtext(char: str) -> bool:
    code = ord(char)
    return (
        char in OWS
        or code == 0x21
        or 0x23 <= code <= 0x5B
        or 0x5D <= code <= 0x7E
        or 0x80 <= code <= 0xFF
    )


def is_pair_char(char: str) -> bool:
    """The octet allowed after a backslash in a quoted-pair."""
    code = ord(char)
    return char in OWS or 0x21 <= code <= 0x7E or 0x80 <= code <= 0xFF


def is_sendable(text: str) -> bool:
    """True when a sender may put the text in a quoted string: HTAB, SP and VCHAR only."""
    return all(char in OWS or 0x21 <= ord(char) <= 0x7E for char in text)


def quote(text: str) -> str:
    """Write a quoted-string, escaping only the backslash and the double quote."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
