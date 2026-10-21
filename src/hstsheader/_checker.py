"""Find where the hstspreload.org checker reads a header differently from RFC 6797.

The checker (chromium/hstspreload ``header.go``) cuts the value at every ';', inside
quoted strings too, trims each piece with Go's ``strings.TrimSpace``, and takes a piece
for max-age when it starts with ``max-age``, and for preload or includeSubDomains when it
equals that name, ignoring case. A piece it takes for one of these where RFC 6797 reads
no such directive makes it check something the header does not say.

Go reads the octets as UTF-8, so this module works on octets too: a character up to
U+00FF is the octet a latin-1 decode made of it, and one above (already an RFC error)
stands for its UTF-8 octets.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Iterator, Mapping

from ._chars import ascii_lower, shorten
from ._model import Issue

# Go's unicode.IsSpace, the set strings.TrimSpace removes. Only the UTF-8 form of each is
# a space to it: a lone 0x85 or 0xA0 octet is invalid UTF-8, which it keeps.
_GO_SPACE = [*range(0x09, 0x0E), 0x20, 0x85, 0xA0, 0x1680, *range(0x2000, 0x200B)]
_GO_SPACE += [0x2028, 0x2029, 0x202F, 0x205F, 0x3000]
_FORMS = [chr(code).encode("utf-8") for code in _GO_SPACE]
# UTF-8 is prefix free, so a run of these forms from a character boundary is exactly the
# run of space characters Go decodes there; the end is matched on the reversed octets.
_LEAD = re.compile(b"(?:" + b"|".join(map(re.escape, _FORMS)) + b")*")
_TAIL = re.compile(b"(?:" + b"|".join(re.escape(form[::-1]) for form in _FORMS) + b")*")
_WIDE_RUN = re.compile("([^" + chr(0) + "-" + chr(0xFF) + "]+)")
_LONG_S = chr(0x17F)
_EXACT = {"preload": "preload", "includesubdomains": "includeSubDomains"}


class _Octets:
    """The octets a header stands for, and the way back from an octet to a character."""

    def __init__(self, text: str) -> None:
        # Each run of characters above U+00FF: its first octet and character, its octets
        # and its length in characters.
        self.wide: list[tuple[int, int, bytes, int]] = []
        self.starts: list[int] = []
        try:
            self.data = text.encode("latin-1")
            return
        except UnicodeEncodeError:
            pass
        data = bytearray()
        char = 0
        for index, part in enumerate(_WIDE_RUN.split(text)):
            if index % 2:
                octets = part.encode("utf-8", "surrogatepass")
                self.wide.append((len(data), char, octets, len(part)))
                data += octets
            else:
                data += part.encode("latin-1")
            char += len(part)
        self.data = bytes(data)
        self.starts = [run[0] for run in self.wide]

    def char(self, octet: int) -> int:
        """The character at an octet offset, which always falls between characters."""
        at = bisect_right(self.starts, octet) - 1
        if at < 0:
            return octet
        start, char, octets, length = self.wide[at]
        if octet >= start + len(octets):
            return char + length + octet - start - len(octets)
        # Runs hold no ';', so at most a piece's two ends fall inside one: decoding is linear.
        return char + len(octets[: octet - start].decode("utf-8", "surrogatepass"))


def _pieces(data: bytes) -> Iterator[tuple[int, bytes]]:
    """Each piece the checker reads, after TrimSpace, with the octet where it starts."""
    start = 0
    for piece in data.split(b";"):
        lead = _LEAD.match(piece).end()  # type: ignore[union-attr]  # always matches
        kept = piece[lead:]
        tail = _TAIL.match(kept[::-1]).end()  # type: ignore[union-attr]
        yield start + lead, kept[: len(kept) - tail]
        start += len(piece) + 1


def _taken_for(piece: bytes) -> str | None:
    if piece[:7].lower() == b"max-age":  # max-age= is read as a value, the rest as no value
        return "max-age"
    try:
        name = piece.decode("utf-8")
    except UnicodeDecodeError:  # Go reads an invalid octet as U+FFFD, matching no name
        return None
    # Go's strings.EqualFold also matches the long s with s; no other non-ASCII character
    # folds to a letter of either name, and none lowers to one of max-age.
    folded = ascii_lower(name.replace(_LONG_S, "s"))
    return folded if folded in _EXACT else None


def misreads(text: str, names: Mapping[int, str]) -> list[Issue]:
    """A ``preload.misread`` error for each piece the checker takes for another directive.

    ``names`` maps the offset of every directive RFC 6797 reads to its lower-cased name.
    """
    octets = _Octets(text)
    issues: list[Issue] = []
    for start, piece in _pieces(octets.data):
        key = _taken_for(piece)
        if key is None:
            continue
        offset = octets.char(start)
        if names.get(offset) != key:
            shown = text[offset : octets.char(start + len(piece))]
            message = (
                f"the hstspreload.org checker cuts the header at every ';' and reads "
                f"{shorten(shown)!r} as {_EXACT.get(key, key)}"
            )
            issues.append(Issue("preload.misread", message, "error", offset))
    return issues
