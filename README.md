# hstsheader

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Parse, check and build the HTTP Strict-Transport-Security header, typed and zero-dependency.

- Reads the header the way RFC 6797 says a user agent must, or tolerantly for logs and
  scanners.
- Lists every problem with a stable code and the offset where it starts.
- Checks the hstspreload.org header requirements before you submit a domain.
- Builds header values that cannot carry an injected line.
- Ships a command line that checks the output of `curl -sI`.

## Install

```
pip install hstsheader
```

Python 3.10 or newer, no dependencies.

## Read a header

```python
from hstsheader import parse

policy = parse("max-age=31536000; includeSubDomains; preload")
print(policy)
# Hsts(max_age=31536000, include_subdomains=True, preload=True)
print(parse(' MAX-AGE = "600" ; unknown=1'))
# Hsts(max_age=600, include_subdomains=False, preload=False)
```

Directive names match without regard to ASCII case, whitespace may surround `;` and `=`,
unknown directives are ignored and `max-age` may be quoted, as RFC 6797 section 6.1
allows. A folded line counts as whitespace. Inside a quoted string, a backslash may be
followed by HTAB, SP, a visible ASCII character or obs-text (RFC 9110 section 5.6.4,
stricter on purpose than the RFC 2616 rule, which allowed any ASCII character there).
`max-age` must be ASCII digits. RFC 6797 sets no ceiling on it; this library caps it at
2147483648 (2^31), by analogy with RFC 9111 section 1.2.2, where a cache that cannot
represent a larger delta-seconds value uses 2^31. A larger value is read as 2147483648,
and `Hsts` and `build` refuse one.

## Strict or tolerant

By default `parse` is tolerant: it skips directives it cannot read, keeps the first valid
`max-age`, and raises `HstsError` only when no valid `max-age` is left. With
`strict=True` it accepts only a header that a user agent following RFC 6797 honours, and
the error names the rule and the offset.

```python
from hstsheader import HstsError, parse

header = "max-age=600; max-age=5; includeSubDomains"
print(parse(header).max_age)
# 600
try:
    parse(header, strict=True)
except HstsError as error:
    print(error.code, error.offset)
# duplicate 13
```

Strict mode refuses a missing or non-numeric `max-age`, a directive that appears twice, a
value on `includeSubDomains`, anything outside the token and quoted-string grammar, and
CR, LF or NUL. RFC 6797 does not define `preload`, so `preload=yes` is an unknown
directive there: the header is honoured, `preload` stays `False`, and lint warns. Both modes take the field lines of a response as a list and
read only the first one, as RFC 6797 section 8.1 requires.

## Lint a header

```python
from hstsheader import lint

for issue in lint('max-age="031536000"; includeSubDomains=yes;'):
    print(issue.severity, issue.code, issue.offset)
# warning max-age.leading-zero 8
# warning max-age.quoted 8
# error value-not-allowed 21
# warning empty-directive 42
```

An `error` means a user agent that follows RFC 6797 ignores the whole header. A
`warning` marks something legal that is likely a mistake or that some checkers refuse.
Offsets index the field value; an empty directive points at its semicolon.

| Code | Severity | Meaning |
| --- | --- | --- |
| `syntax` | error | outside the directive grammar (offset of the first bad character) |
| `control-character` | error | CR, LF or NUL in the value |
| `max-age.missing` | error | no `max-age` directive |
| `max-age.no-value` | error | `max-age` without `=` |
| `max-age.not-digits` | error | the value is not ASCII digits |
| `duplicate` | error | a directive appears more than once |
| `value-not-allowed` | error | `includeSubDomains` with a value |
| `field.missing` | error | an empty list of field lines |
| `max-age.leading-zero` | warning | the value starts with 0 |
| `max-age.capped` | warning | the value is above 2147483648 and is read as that |
| `max-age.quoted` | warning | valid, but hstspreload.org refuses it |
| `max-age.spaced` | warning | space around `=` in max-age: valid, but hstspreload.org refuses it |
| `obs-fold` | warning | a folded line, read as whitespace |
| `max-age.zero-subdomains` | warning | `max-age=0` makes `includeSubDomains` pointless |
| `empty-directive` | warning | an extra `;` |
| `unknown-directive` | warning | a directive this library does not know is ignored |
| `preload-value` | warning | `preload` with a value: an unknown directive to RFC 6797, ignored |
| `multiple-fields` | warning | more than one field line; only the first counts |

## Check preload eligibility

```python
from hstsheader import is_preloadable, preload_issues

print(is_preloadable("max-age=63072000; includeSubDomains; preload"))
# True
for issue in preload_issues("max-age=10886400; preload"):
    print(issue.code)
# preload.subdomains-missing
# preload.max-age-too-short
```

The rules are the header requirements on hstspreload.org: `includeSubDomains` and
`preload` present and a `max-age` of at least 31536000 seconds. The site's checker is
stricter than RFC 6797 about how `max-age` is written and treats `max-age=0` as a
removal request. RFC errors are included, except a repeated directive other than
`max-age` and `includeSubDomains`, which the site only warns about and which comes back
as a warning. The site also checks redirects, certificates and subdomains over the
network; that part is out of scope here.

| Code | Severity | Meaning |
| --- | --- | --- |
| `preload.subdomains-missing` | error | no `includeSubDomains` |
| `preload.missing` | error | no `preload` |
| `preload.max-age-too-short` | error | `max-age` below 31536000 |
| `preload.max-age-zero` | error | `max-age=0`, a removal request |
| `preload.max-age-quoted` | error | a quoted `max-age`, which the site's checker refuses |
| `preload.max-age-spaced` | error | space around the `=` of `max-age` |
| `preload.max-age-unreadable` | error | a `max-age` above 2^64 - 1 |
| `preload.invalid` | error | `preload` with a value, which the site's checker refuses |
| `preload.max-age-over-ten-years` | warning | a `max-age` above ten years |

## Build a header

```python
from hstsheader import Hsts, build

print(build(31536000, include_subdomains=True))
# max-age=31536000; includeSubDomains
print(build(Hsts(600, preload=True), extensions={"report-uri": "https://example.com/r;1"}))
# max-age=600; preload; report-uri="https://example.com/r;1"
```

Flags must be `bool` and `max_age` an `int` (else `TypeError`), from 0 to 2147483648
(else `HstsError`). Extension names must be HTTP tokens and cannot repeat or shadow the
three known directives; values that are not tokens are quoted, and control or non-ASCII
characters raise `HstsError`, so a value cannot smuggle a second header line. For every
valid policy, `parse(build(policy), strict=True) == policy`.

## Command line

```
$ hstsheader "max-age=600; includeSubDomains"
$ curl -sI https://example.com | hstsheader --preload
$ python -m hstsheader "max-age=600"
$ hstsheader --version
```

It prints the policy and the findings as JSON (the keys are listed in the
[guide](https://github.com/JaviLianes8/hstsheader/blob/main/GUIDE.md#command-line)).
The exit status is 0 when a user agent following RFC 6797 honours the header (with
`--preload`: when it meets the preload rules), 1 when it does not, and 2 when the input
has no Strict-Transport-Security field (empty standard input included). A head ends at
its blank line, folded lines are joined and pasted fields without a status line are
accepted. With several responses (`curl -sIL`) the first final one is checked, the
answer for the URL you asked for: a browser applies each response's header to the host
that sent it, and hstspreload.org reads the header on the base domain's own response,
not on the page it redirects to. Interim (1xx) responses and a proxy's `Connection
established` are skipped. To check where a redirect leads, run it on that URL.

## Where Chromium differs

This library follows RFC 6797. Chromium's parser is more lenient in one way and stricter
in one: it accepts a repeated directive other than `max-age` and `includeSubDomains`
(so a repeated `preload` still works there), and it stores at most one year of `max-age`
whatever the header says.

## API

| Name | What it is |
| --- | --- |
| `parse(header, *, strict=False)` | read a value or a list of field lines into an `Hsts` |
| `lint(header)` | every finding as a tuple of `Issue` |
| `preload_issues(header)` | findings against the hstspreload.org rules (value or `Hsts`) |
| `is_preloadable(header)` | `True` when `preload_issues` has no error |
| `build(max_age, *, include_subdomains, preload, extensions)` | write a header value |
| `Hsts` | frozen dataclass: `max_age`, `include_subdomains`, `preload`, checked on creation |
| `Issue` | frozen dataclass: `code`, `message`, `severity`, `offset` |
| `Severity` | the type of `Issue.severity`: `Literal["error", "warning"]` |
| `HstsError` | a `ValueError` with `code` and `offset`; wrong argument types raise `TypeError` |
| `DELTA_SECONDS_MAX` | 2147483648, the cap this library applies to `max-age` |
| `PRELOAD_MIN_MAX_AGE` | 31536000, the shortest `max-age` the preload list takes |

## Sources

RFC 6797 (the header and the user agent processing model), RFC 2616 (the grammar it
builds on), RFC 9110 (token, quoted-string, field values), RFC 9111 (the 2^31 cap), the
hstspreload.org requirements and its header checker, and Chromium's header parser. The
tests check the library against copies of these files; `python scripts/fetch_upstream.py`
fetches them and `tests/upstream/MANIFEST.json` pins each one by URL, revision and sha256.
The tests also run the hstspreload.org checker itself, built from its Go source, on tens
of thousands of generated headers and compare verdicts. The
[guide](https://github.com/JaviLianes8/hstsheader/blob/main/GUIDE.md#how-it-is-checked)
has the details.

## Why

The PyPI packages that handle this header, as checked on 2026-10-21 (latest releases,
source read and run):

- `secure` 2.0.1, `flask-talisman` 1.1.0 and `pyramid_hsts` 1.3.0 write the header for a
  web framework; none of them reads one.
- `hstspreload` 2025.1.1 answers whether a host is on Chromium's preload list; it does
  not look at headers.
- `apifrom` 1.0.0, a REST API framework with ten runtime dependencies, has a
  `get_hsts_directives` helper that splits on `;`, so a quoted `;` breaks it; it reads
  `max-age=abc` as 0 and keeps the last of two `max-age` directives, the opposite of what
  RFC 6797 asks.

hstsheader reads the header as a user agent must, explains every problem with a code and
an offset, checks the preload rules and writes headers that cannot be injected, with no
dependencies.

## Documentation

- [Guide](https://github.com/JaviLianes8/hstsheader/blob/main/GUIDE.md): the reading
  rules, every error, the command line output and the stability promise.
- [Changelog](https://github.com/JaviLianes8/hstsheader/blob/main/CHANGELOG.md)

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/hstsheader/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
