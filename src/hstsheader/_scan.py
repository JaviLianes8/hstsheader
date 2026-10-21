"""Split a field value into directives following the RFC 6797 section 6.1 grammar.

    Strict-Transport-Security = [ directive ] *( ";" [ directive ] )
    directive                 = directive-name [ "=" directive-value ]
    directive-name            = token
    directive-value           = token | quoted-string

Whitespace may appear between any two words and separators (RFC 2616 section 2.2,
"implied *LWS"), and a folded line (CRLF followed by SP or HTAB) counts as whitespace, as
RFC 2616 LWS and RFC 9112 section 5.2 allow. A quoted-pair follows RFC 9110 section 5.6.4
(HTAB, SP, VCHAR or obs-text after the backslash), stricter on purpose than RFC 2616, which
let any US-ASCII character follow. A directive that breaks the grammar is reported and
skipped up to the next semicolon that is not inside a quoted string, so the rest can still
be read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ._chars import OWS, TCHAR, ascii_lower, is_pair_char, is_qdtext, shorten
from ._model import Issue

# RFC 9110 section 5.5: CR, LF and NUL are invalid; a recipient may replace them with SP.
_REPLACED = str.maketrans({"\r": " ", "\n": " ", "\0": " "})
_FOLD = re.compile(r"\r?\n(?=[ \t])")


@dataclass(frozen=True, slots=True)
class Directive:
    name: str
    key: str
    value: str | None
    quoted: bool
    offset: int
    value_offset: int
    # Whitespace around "=": legal, but the hstspreload.org checker refuses it for max-age.
    spaced: bool = False


@dataclass(slots=True)
class Scan:
    directives: list[Directive] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    # (offset, lower-cased name) of directives skipped because they broke the grammar.
    broken: list[tuple[int, str]] = field(default_factory=list)


class _Broken(Exception):
    def __init__(self, message: str, offset: int, name: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.offset = offset
        self.name = name


def _skip_ows(text: str, i: int) -> int:
    while i < len(text) and text[i] in OWS:
        i += 1
    return i


def _quoted(text: str, start: int) -> tuple[str, int]:
    """Read the quoted-string opening at ``start``; return its value and the end index."""
    out: list[str] = []
    i = start + 1
    while i < len(text):
        char = text[i]
        if char == '"':
            return "".join(out), i + 1
        if char == "\\":
            if i + 1 >= len(text):
                break
            if not is_pair_char(text[i + 1]):
                raise _Broken(f"{_show(text[i + 1])} cannot follow a backslash", i + 1)
            out.append(text[i + 1])
            i += 2
            continue
        if not is_qdtext(char):
            raise _Broken(f"{_show(char)} is not allowed in a quoted string", i)
        out.append(char)
        i += 1
    raise _Broken("unterminated quoted string", start)


def _show(char: str) -> str:
    return f"U+{ord(char):04X}" if not char.isprintable() or not char.isascii() else repr(char)


def _token(text: str, i: int) -> int:
    while i < len(text) and text[i] in TCHAR:
        i += 1
    return i


def _directive(text: str, i: int) -> tuple[Directive, int]:
    start, end = i, _token(text, i)
    if end == i:
        raise _Broken(f"{_show(text[i])} cannot start a directive name", i)
    name, i = text[i:end], _skip_ows(text, end)
    try:
        return _rest(text, i, name, start)
    except _Broken as broken:
        broken.name = name
        raise


def _rest(text: str, i: int, name: str, start: int) -> tuple[Directive, int]:
    value: str | None = None
    quoted = spaced = False
    value_offset = i
    if i < len(text) and text[i] == "=":
        i = value_offset = _skip_ows(text, i + 1)
        spaced = text[start + len(name)] != "=" or text[i - 1] != "="
        if i < len(text) and text[i] == '"':
            value, i = _quoted(text, i)
            quoted = True
        else:
            end = _token(text, i)
            if end == i:
                found = "the end" if i == len(text) else _show(text[i])
                raise _Broken(f"expected a value for {shorten(name)}, found {found}", i)
            value, i = text[i:end], end
        i = _skip_ows(text, i)
    if i < len(text) and text[i] != ";":
        message = f"unexpected {_show(text[i])} after {shorten(name)}; directives end at ';'"
        raise _Broken(message, i)
    key = ascii_lower(name)
    return Directive(name, key, value, quoted, start, value_offset, spaced), i


def _resync(text: str, i: int) -> int:
    """Index of the next ';' outside a quoted string, or the end of the text."""
    while i < len(text) and text[i] != ";":
        if text[i] == '"':
            try:
                i = _quoted(text, i)[1]
                continue
            except _Broken:
                # A quote that never closes would swallow everything after it; give up on
                # it and resume at the next plain semicolon instead.
                nxt = text.find(";", i)
                return len(text) if nxt < 0 else nxt
        i += 1
    return i


def scan(text: str) -> Scan:
    """Split ``text`` into directives, recording every syntax problem as an :class:`Issue`."""
    result = Scan()

    def unfold(fold: re.Match[str]) -> str:
        message = "folded line (obsolete line folding), read as whitespace"
        result.issues.append(Issue("obs-fold", message, "warning", fold.start()))
        return " " * len(fold.group())  # same length, so offsets keep pointing at the input

    text = _FOLD.sub(unfold, text)
    for index, char in enumerate(text):
        if char in "\r\n\0":
            message = f"{_show(char)} is not allowed in a field value"
            result.issues.append(Issue("control-character", message, "error", index))
    text = text.translate(_REPLACED)
    if not text.strip(OWS):
        return result
    i = 0
    while True:
        start = i = _skip_ows(text, i)
        if i == len(text) or text[i] == ";":
            # Point at a semicolon: the one closing this empty element, or the last one.
            where = i if i < len(text) else text.rindex(";")
            message = "empty directive (an extra ';')"
            result.issues.append(Issue("empty-directive", message, "warning", where))
        else:
            try:
                directive, i = _directive(text, i)
                result.directives.append(directive)
            except _Broken as broken:
                result.issues.append(Issue("syntax", broken.message, "error", broken.offset))
                result.broken.append((start, ascii_lower(broken.name)))
                i = _resync(text, start)
        if i >= len(text):
            return result
        i += 1
