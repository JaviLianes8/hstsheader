# hstsheader guide

The README shows what the library does. This guide holds the exact rules: how a value is
read, what every error means, what the command line prints and what stays stable.

## Stability

From 1.0.0 these change only in a new major version:

- the eleven names in `hstsheader.__all__`, their parameter names, kinds and defaults;
- the fields of `Hsts` (`max_age`, `include_subdomains`, `preload`) and `Issue`
  (`code`, `message`, `severity`, `offset`), and the `code` and `offset` attributes of
  `HstsError`;
- every `Issue` code in the README tables and its severity, and the `HstsError` codes
  listed below;
- the command line options, the JSON keys and the exit statuses.

Messages are for people and may be reworded in any release; match on codes. A new
finding may be added in a minor release, with a new code.

## Reading a value

The grammar is RFC 6797 section 6.1:

```
Strict-Transport-Security = [ directive ] *( ";" [ directive ] )
directive                 = directive-name [ "=" directive-value ]
directive-name            = token
directive-value           = token | quoted-string
```

- Whitespace (SP and HTAB) may stand between any two words and separators, as RFC 2616
  "implied LWS" allows. A folded line (CR LF, or a bare LF, followed by SP or HTAB) counts
  as whitespace and is reported as `obs-fold`. Any other CR, LF or NUL is a
  `control-character` error and is read as a space so the rest can still be checked.
- Names compare with ASCII case folding only: the Kelvin sign is not a `k`.
- A quoted string follows RFC 9110 section 5.6.4: a backslash may be followed by HTAB,
  SP, a visible ASCII character or obs-text, and stands for that character.
- `max-age` must be ASCII digits, quoted or not. Leading zeros are allowed (with a
  warning). RFC 6797 sets no ceiling; this library caps `max-age` at 2147483648 (2^31)
  by analogy with RFC 9111 section 1.2.2, where a cache that cannot represent a larger
  delta-seconds value uses 2^31. A larger value is read as 2147483648 without converting
  the digits, so a value of a million digits is cheap.
- `parse`, `lint` and `preload_issues` take one field value, or the field lines of a
  response in order; only the first line counts (RFC 6797 section 8.1), and more than one
  line adds a `multiple-fields` warning. An empty list is a `field.missing` error.
- `bytes` raises `TypeError`: decode a raw head with latin-1 first, which keeps every
  octet.

**Strict reading** (`parse(value, strict=True)`) raises `HstsError` for the first finding
of severity `error`, with its code and offset. Strict acceptance is exactly what a user
agent following RFC 6797 honours: the grammar above, every directive at most once, a
`max-age` with digits, no value on `includeSubDomains`, no CR, LF or NUL. RFC 6797 does
not define `preload`, so `preload=yes` is an unknown directive to it: strict reading
accepts the header with `preload` false, and lint warns `preload-value`.

**Tolerant reading** (the default) skips a directive that breaks the grammar up to the
next `;` outside a quoted string, keeps the first `max-age` that reads, and sets a flag
when a valueless `includeSubDomains` or `preload` appears anywhere. It raises
`HstsError` only when no `max-age` is usable: the error is the `max-age` finding, or the
syntax error of a `max-age` directive that broke the grammar. Whenever strict reading
succeeds, tolerant reading returns the same policy.

## Errors

`HstsError` is a `ValueError`. Its `offset` indexes the field value (the first field
line), or is `None`. Besides the lint codes, `Hsts` and `build` use:

| Code | Raised when |
| --- | --- |
| `max-age.negative` | `max_age` is below 0 |
| `max-age.too-large` | `max_age` is above 2147483648, the cap this library applies |
| `build.name` | an extension name is not a token, or is one of the three known names |
| `build.value` | an extension value has a control or non-ASCII character |
| `duplicate` | two extension names are equal without regard to case |

An argument of the wrong type raises `TypeError`, never `HstsError`: a `max_age` that is
not an `int` (a `bool` included), a flag that is not a `bool` (the `strict` argument of
`parse` included), `extensions` that is not a mapping, a name that is not a `str`, a
value that is neither `str` nor `None`, flags passed next to an `Hsts`, and input to the
readers that is not text (`bytes`, `bytearray` and `memoryview` included). `str` and
`int` subclasses are copied to plain values before they are checked, so they cannot
change what is written.

Messages quote at most 40 characters of a name or value, then its length.

## Preload rules

`preload_issues` applies the header requirements of hstspreload.org. Its checker (the Go
package chromium/hstspreload) reads headers more loosely than RFC 6797 in places and more
strictly in others, so the result combines both:

- RFC errors are included, so `is_preloadable` is never true for a header a user agent
  ignores. A repeated directive other than `max-age` and `includeSubDomains` is a warning
  here, because the site and Chromium accept it.
- The site's own rules come next. A quoted `max-age`, space around its `=` or a value
  above 2^64 - 1 is an error, because the site cannot read it; the ten year warning
  appears only for a `max-age` the site can read. A `preload` with a value is the
  warning `preload.invalid`, as on the site, and it does not count as `preload`, so
  without a bare `preload` the header fails with `preload.missing`.

The tests run the site's checker on generated headers and hold two properties: every
header `is_preloadable` accepts passes the checker, and for a header with no RFC error the
two verdicts and the ten year warning agree.

## Command line

```
hstsheader [--preload] [VALUE]
hstsheader --version
```

With `VALUE`, that text is checked: a response head when its first non-empty line is a
status line or a `name: value` field line, else a bare field value. Without it, standard
input is read as latin-1 the same way. In a head, folded lines are joined, and every
Strict-Transport-Security line of the first final response is passed on, the first one
counting. Interim responses (1xx) and a proxy's `200 Connection established` are not
final. With several responses (`curl -sIL` follows redirects) the first is the answer
for the URL that was asked for: RFC 6797 section 8.1 has a browser apply the header of
each response, redirects included, to the host that sent it, and hstspreload.org reads
the header on the base domain's own response rather than on the page it redirects to.
When the first final response has no field but a later one has it, the base domain
sends no header: the report has `field` and `policy` null, `honoured` (and
`preloadable`) false, and the single issue `field.missing`, an error with a null
offset, in `issues` (and `preload_issues`).

The JSON object has these keys, in this order:

| Key | Value |
| --- | --- |
| `field` | the first field value checked, or `null` with `field.missing` |
| `honoured` | `true` when there is no RFC error |
| `policy` | `{"max_age", "include_subdomains", "preload"}` from the tolerant reading, or `null` |
| `issues` | every lint finding: `{"code", "severity", "offset", "message"}` |
| `preloadable` | with `--preload` only: `true` when there is no preload error |
| `preload_issues` | with `--preload` only: the `preload.*` findings, or `field.missing` |

Exit status: 0 when the header is honoured (with `--preload`: preloadable), 1 when it is
not (`field.missing` above included), 2 for usage errors, including input where no
response has the field and an empty standard input.
An empty `VALUE` argument is a value to check, so it exits 1. When the reader of the
output stops early (`| head`), the rest is discarded quietly and the exit status still
gives the verdict.

## Upgrading from 0.2.0

Code may need a change in these places:

- Catching `HstsError` for an argument of the wrong type: catch `TypeError` there. This
  includes a `strict` argument that is not a `bool`, which 0.2.0 read by truthiness.
- Calling `lint(value=...)` by keyword: the parameter is `header` now, like the other
  readers. Positional calls are unchanged.
- Relying on `preload=<value>` being an error: it is the warning `preload-value` now,
  and the preload check reports it as the warning `preload.invalid`.
- Piping `curl -sIL` into the command line: the first final response is checked, not
  the last, and when only a later response has the field the exit status is 1.

The other changes in the
[changelog](https://github.com/JaviLianes8/hstsheader/blob/main/CHANGELOG.md) make
results more precise and do not change any signature.

## How it is checked

- Sources: RFC 6797, 2616, 9110 and 9111, the hstspreload.org page, the checker's
  `header.go` and `header_test.go`, and Chromium's `http_security_headers.cc` and `.h`,
  pinned by URL, revision and sha256 in `tests/upstream/MANIFEST.json` and fetched by
  `scripts/fetch_upstream.py`. The RFC examples, thresholds and the checker's own test
  vectors are read from those files.
- The checker itself, built from its Go source (`tests/oracle`), runs on eight seeded
  corpora of up to 15,000 generated headers each (`tests/test_oracle_hstspreload.py`).
- Real headers served by 22 well known sites, with the checker's verdict on each
  (`tests/test_realworld.py`).
- An acceptor written separately from the grammar is compared with strict reading on
  random input, and seeded fuzzing checks that every reader is total and consistent
  (`tests/test_fuzz.py`); hostile shapes are timed for linear growth
  (`tests/test_hostile.py`).
- The installed wheel and its command line are driven from an empty folder, and the PyPI
  release is upgraded in place (`tests/test_e2e_wheel.py`).
