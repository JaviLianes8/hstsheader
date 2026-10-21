"""Find where the hstspreload.org checker reads a header differently from RFC 6797.

The checker (chromium/hstspreload ``header.go``) cuts the value at every ';', inside
quoted strings too, trims each piece with Go's ``strings.TrimSpace``, and takes a piece
for max-age when it starts with ``max-age``, and for preload or includeSubDomains when it
equals that name, ignoring case. A piece it takes for one of these where RFC 6797 reads
no such directive makes it check something the header does not say.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping

from ._chars import ascii_lower, shorten
from ._model import Issue

# Go's unicode.IsSpace, the set strings.TrimSpace removes: more than SP and HTAB.
_LATIN1_SPACE = [*range(0x09, 0x0E), 0x20, 0x85, 0xA0]
_OTHER_SPACE = [0x1680, *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F, 0x3000]
_GO_SPACE = "".join(map(chr, _LATIN1_SPACE + _OTHER_SPACE))
# Go's strings.EqualFold also matches the long s with s and the Kelvin sign with k.
_FOLD = str.maketrans({chr(0x17F): "s", chr(0x212A): "k"})
_EXACT = {"preload": "preload", "includesubdomains": "includeSubDomains"}


def _pieces(text: str) -> Iterator[tuple[int, str]]:
    """Each piece the checker reads, trimmed, with the offset where it starts."""
    start = 0
    for piece in text.split(";"):
        kept = piece.lstrip(_GO_SPACE)
        yield start + len(piece) - len(kept), kept.rstrip(_GO_SPACE)
        start += len(piece) + 1


def _taken_for(piece: str) -> str | None:
    lowered = ascii_lower(piece)
    if lowered.startswith("max-age"):  # max-age= is read as a value, the rest as no value
        return "max-age"
    folded = lowered.translate(_FOLD)
    return folded if folded in _EXACT else None


def misreads(text: str, names: Mapping[int, str]) -> list[Issue]:
    """A ``preload.misread`` error for each piece the checker takes for another directive.

    ``names`` maps the offset of every directive RFC 6797 reads to its lower-cased name.
    """
    issues: list[Issue] = []
    for offset, piece in _pieces(text):
        key = _taken_for(piece)
        if key is not None and names.get(offset) != key:
            message = (
                f"the hstspreload.org checker cuts the header at every ';' and reads "
                f"{shorten(piece)!r} as {_EXACT.get(key, key)}"
            )
            issues.append(Issue("preload.misread", message, "error", offset))
    return issues
