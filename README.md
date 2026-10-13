# hstsheader

Parse, check and build the HTTP Strict-Transport-Security header, typed and zero-dependency.

- Reads the header the way RFC 6797 says a browser must, or tolerantly for logs and scanners.
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
allows. `max-age` must be ASCII digits; a value above 2147483648 (2^31, the ceiling RFC
9111 section 1.2.2 sets for delta-seconds) is read as 2147483648.

## Strict or tolerant

By default `parse` is tolerant: it skips directives it cannot read, keeps the first valid
`max-age`, and raises `HstsError` only when no valid `max-age` is left. With
`strict=True` it accepts only a header that a conforming browser honours, and the error
names the rule and the offset.

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
value on `includeSubDomains` or `preload`, anything outside the token and quoted-string
grammar, and CR, LF or NUL. Both modes take the field lines of a response as a list and
read only the first one, as RFC 6797 section 8.1 requires.

## Lint a header

```python
from hstsheader import lint

for issue in lint('max-age="031536000"; includeSubDomains=yes; ;'):
    print(issue.severity, issue.code, issue.offset)
# warning max-age.leading-zero 8
# warning max-age.quoted 8
# error value-not-allowed 21
# warning empty-directive 44
# warning empty-directive 45
```

An `error` means a browser ignores the whole header. A `warning` marks something legal
that is likely a mistake or that some checkers refuse.

| Code | Severity | Meaning |
| --- | --- | --- |
| `syntax` | error | outside the directive grammar (offset of the first bad character) |
| `control-character` | error | CR, LF or NUL in the value |
| `max-age.missing` | error | no `max-age` directive |
| `max-age.no-value` | error | `max-age` without `=` |
| `max-age.not-digits` | error | the value is not ASCII digits |
| `duplicate` | error | a directive appears more than once |
| `value-not-allowed` | error | `includeSubDomains` or `preload` with a value |
| `field.missing` | error | an empty list of field lines |
| `max-age.leading-zero` | warning | the value starts with 0 |
| `max-age.capped` | warning | the value is above 2147483648 and is read as that |
| `max-age.quoted` | warning | valid, but hstspreload.org refuses it |
| `max-age.zero-subdomains` | warning | `max-age=0` makes `includeSubDomains` pointless |
| `empty-directive` | warning | an extra `;` |
| `unknown-directive` | warning | a directive this library does not know is ignored |
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
`preload` present and a `max-age` of at least 31536000 seconds. The site's checker also
refuses a quoted `max-age`, treats `max-age=0` as a removal request and warns above ten
years; the same findings come back as `preload.max-age-quoted`, `preload.max-age-zero`
and the warning `preload.max-age-over-ten-years`. RFC errors are included, since a header
browsers ignore cannot be preloaded. The site also checks redirects, certificates and
subdomains over the network; that part is out of scope here.

## Build a header

```python
from hstsheader import Hsts, build

print(build(31536000, include_subdomains=True))
# max-age=31536000; includeSubDomains
print(build(Hsts(600, preload=True), extensions={"report-uri": "https://example.com/r;1"}))
# max-age=600; preload; report-uri="https://example.com/r;1"
```

Flags must be `bool`, `max_age` an `int` from 0 to 2147483648. Extension names must be
HTTP tokens and cannot repeat or shadow the three known directives; values that are not
tokens are quoted, and control or non-ASCII characters raise `HstsError`, so a value
cannot smuggle a second header line. For every valid policy,
`parse(build(policy), strict=True) == policy`.

## Command line

```
$ hstsheader "max-age=600; includeSubDomains"
$ curl -sI https://example.com | hstsheader --preload
$ python -m hstsheader "max-age=600"
```

It prints the policy and the findings as JSON. The exit status is 0 when browsers honour
the header (and, with `--preload`, when it meets the preload rules), 1 when they do not,
and 2 when the input has no Strict-Transport-Security field.

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
| `HstsError` | a `ValueError` with `code` and `offset` |
| `DELTA_SECONDS_MAX` | 2147483648, the ceiling for `max-age` |
| `PRELOAD_MIN_MAX_AGE` | 31536000, the shortest `max-age` the preload list takes |

## Sources

RFC 6797 (the header and the browser processing model), RFC 2616 (the grammar it builds
on), RFC 9110 (token, quoted-string, field values), RFC 9111 (delta-seconds), the
hstspreload.org requirements and its header checker, and Chromium's header parser. The
tests check the library against copies of these files; `python scripts/fetch_upstream.py`
fetches them and `tests/upstream/MANIFEST.json` pins each one by URL, revision and sha256.
Those tests skip until the files are fetched.

## Why

RFC 6797 defines a tiny header, yet Python has no standalone, typed, zero-dependency
codec for it. The existing options are all tied to something larger: `apifrom` buries
the logic in a framework utility, `pyramid_hsts` only writes the header, and
PyGObject's `Soup.HSTSPolicy` pulls in the libsoup and GObject stack. This library is a
single-purpose reader, checker and writer with full type hints and nothing to install
alongside it.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
