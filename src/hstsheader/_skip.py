"""Skip a directive that breaks the grammar, in time linear in the whole field value."""

from __future__ import annotations

from array import array

from ._chars import is_pair_char, is_qdtext

_UNKNOWN = -2
_UNCLOSED = -1


class Skipper:
    """Find the next ';' outside a quoted string, remembering every quoted scan.

    A skip that meets a '"' reads a quoted string from there. Without memory, a field such
    as ``a=\\";`` repeated makes every skip read to the end of the field and fail, which
    is quadratic. A quoted-string reader is a small automaton: from a given index, where
    it is between characters, the outcome (the closing index, or no closing quote) is
    always the same, so each index is read at most once per field value.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self._ends: array[int] | None = None

    def _close(self, start: int) -> int | None:
        """End index of the quoted string opening at ``start``, or None when it never closes."""
        text = self.text
        if self._ends is None:
            self._ends = array("q", [_UNKNOWN]) * (len(text) + 1)
        ends = self._ends
        visited: list[int] = []
        i = start + 1
        while True:
            if ends[i] != _UNKNOWN:
                result = ends[i]
                break
            if i == len(text):
                result = _UNCLOSED
                break
            visited.append(i)
            char = text[i]
            if char == '"':
                result = i + 1
                break
            if char == "\\" and i + 1 < len(text) and is_pair_char(text[i + 1]):
                i += 2
                continue
            if char == "\\" or not is_qdtext(char):
                result = _UNCLOSED
                break
            i += 1
        for index in visited:
            ends[index] = result
        return None if result == _UNCLOSED else result

    def resync(self, i: int) -> int:
        """Index of the next ';' outside a quoted string, or the end of the text."""
        text = self.text
        while i < len(text) and text[i] != ";":
            if text[i] == '"':
                end = self._close(i)
                if end is None:
                    # A quote that never closes would swallow everything after it; give up
                    # on it and resume at the next plain semicolon instead.
                    nxt = text.find(";", i)
                    return len(text) if nxt < 0 else nxt
                i = end
                continue
            i += 1
        return i
