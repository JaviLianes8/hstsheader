"""Command line: check a Strict-Transport-Security value or a response head, print JSON."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from ._head import field_lines
from ._lint import analyse
from ._model import Issue
from ._preload import preload_issues

EXIT_REJECTED = 1
EXIT_USAGE = 2


def _issue(issue: Issue) -> dict[str, object]:
    return {
        "code": issue.code,
        "severity": issue.severity,
        "offset": issue.offset,
        "message": issue.message,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line; returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="hstsheader",
        description="Check a Strict-Transport-Security value, or the response head read from "
        "standard input (for example the output of curl -sI). Prints the policy and the "
        "findings as JSON. Exit status 0 means a user agent that follows RFC 6797 honours "
        "the header (with --preload: that it meets the preload list rules), 1 that it does "
        "not, 2 a usage error such as input without the field.",
    )
    parser.add_argument("value", nargs="?", help="a Strict-Transport-Security field value")
    parser.add_argument(
        "--preload", action="store_true", help="also check the hstspreload.org requirements"
    )
    args = parser.parse_args(argv)
    if args.value is None and sys.stdin.isatty():
        parser.error("give a value, or pipe a response head (curl -sI URL | hstsheader)")
    # Latin-1 keeps every octet of a raw head, obs-text included.
    text = args.value if args.value is not None else sys.stdin.buffer.read().decode("latin-1")
    fields = field_lines(text)
    if fields is None:
        bare = text.strip(" \t\r\n")
        # An empty argument is a value to check; empty standard input is a usage error.
        fields = [bare] if bare or args.value is not None else []
    if not fields:
        print("hstsheader: no Strict-Transport-Security field in the input", file=sys.stderr)
        return EXIT_USAGE
    analysis = analyse(fields)
    policy = None
    if analysis.max_age is not None:
        policy = {
            "max_age": analysis.max_age,
            "include_subdomains": analysis.include_subdomains,
            "preload": analysis.preload,
        }
    report: dict[str, object] = {
        "field": fields[0],
        "honoured": not analysis.errors,
        "policy": policy,
        "issues": [_issue(issue) for issue in analysis.issues],
    }
    ok = not analysis.errors
    if args.preload:
        every = preload_issues(fields)
        found = [i for i in every if i.code.startswith("preload.")]
        preloadable = not any(i.severity == "error" for i in every)
        report["preloadable"] = preloadable
        report["preload_issues"] = [_issue(issue) for issue in found]
        ok = preloadable
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if ok else EXIT_REJECTED
