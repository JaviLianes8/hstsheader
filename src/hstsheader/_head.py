"""Find the Strict-Transport-Security field lines in a response head such as curl -sI prints."""

from __future__ import annotations

import re

_FIELD = "strict-transport-security"
_FIELD_LINE = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+:")
# Heads that are not the answer to the request: interim responses (1xx) and the reply of a
# proxy to CONNECT, which curl prints before the real response.
_NOT_FINAL = re.compile(
    r"HTTP/\S*[ \t]+(?:1[0-9]{2}(?![0-9])|200[ \t]+connection established)", re.IGNORECASE
)


def _responses(lines: list[str]) -> list[list[str]]:
    """Split lines into the heads of final responses, each ending at a blank line."""
    heads: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if line.startswith("HTTP/"):
            current = []
            if not _NOT_FINAL.match(line):
                heads.append(current)
        elif not line.strip(" \t"):
            current = None  # the head is over; a body may follow
        elif current is not None:
            current.append(line)
    return heads


def _unfold(lines: list[str]) -> list[str]:
    """Join obsolete folded lines (starting with SP or HTAB) onto the line before."""
    out: list[list[str]] = []
    for line in lines:
        if line[:1] in (" ", "\t") and out:
            out[-1].append(line.strip(" \t"))
        else:
            out.append([line])
    return [" ".join(parts) for parts in out]


def field_lines(text: str) -> list[str] | None:
    """Return the STS values of the first final response in ``text``, or None for a bare value.

    Input counts as a head when its first non-empty line is a status line or a field
    line (``name: value``). With several responses (``curl -sIL`` follows redirects) the
    first final one is used: the answer for the URL that was asked for. A user agent
    applies the header of each response to the host that sent it, and hstspreload.org
    reads it on the base domain's own response, not on the page it redirects to.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    first = next((i for i, line in enumerate(lines) if line.strip(" \t")), len(lines))
    lines = lines[first:]
    if not lines:
        return None
    if not lines[0].startswith("HTTP/"):
        if not _FIELD_LINE.match(lines[0]):
            return None
        lines.insert(0, "HTTP/")  # pasted fields without a status line
    heads = _responses(lines)
    values: list[str] = []
    for line in _unfold(heads[0] if heads else []):
        name, sep, value = line.partition(":")
        if sep and name.lower() == _FIELD:
            values.append(value.strip(" \t"))
    return values
