# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-21

The public API is now stable: the eleven names in `hstsheader.__all__`, their parameter
names and defaults, the `Issue` codes listed in the README, the `HstsError` attributes
and the command line options, JSON keys and exit statuses. They change only in a new
major version. The GUIDE lists the few places where code written for 0.2.0 needs a
change.

### Changed

- An argument of the wrong type now raises `TypeError` everywhere, as `parse` already
  did for `bytes`: `Hsts` and `build` with a `max_age` that is not an `int` (a `bool`
  included) or a flag that is not a `bool`, and `build` with `extensions` that is not a
  mapping, a name that is not a `str` or a value that is neither `str` nor `None`. In
  0.2.0 these raised `HstsError` with the code `type` (or `build.name` for a name that
  is not a `str`); that code is gone. Values of the right type that a header cannot
  carry still raise `HstsError`.
- `parse` refuses a `strict` argument that is not a `bool` with `TypeError`; 0.2.0 read
  it by truthiness, so `strict="false"` meant strict.
- The parameter of `lint` is named `header`, like the other readers (it was `value`).
  Positional calls are unchanged.
- `Hsts` takes `include_subdomains` and `preload` by keyword only, as `build` does:
  `Hsts(600, True)` raises `TypeError`; write `Hsts(600, include_subdomains=True)`. A
  `match` statement takes only `max_age` by position.
- `lint` gives one `empty-directive` warning for each extra `;`, each at its own
  semicolon: `max-age=1;;` gave two warnings at offset 10, now at 9 and 10, and a lone
  `;` gave two warnings at 0, now one.
- When tolerant reading skips a broken directive, a quoted string in it runs to its
  closing quote even when it holds a character the grammar refuses there (a control
  character, DEL, or any character after a backslash), as Chromium reads it. A `;`
  before that quote no longer starts a directive: the Python string
  `'max-age=600; a="\x01;includeSubDomains;"'` no longer sets `include_subdomains`, and
  `lint` no longer reports a duplicate or a syntax error for text inside such a string.
  A quote that never closes is still given up, at the first `;` after the character
  that broke the directive.
- A `preload` directive with a value (`preload=yes`) is no longer an RFC 6797 error.
  RFC 6797 does not define `preload`, so it is an unknown directive there: strict
  `parse` accepts the header with `preload` false, and `lint` gives the new warning
  `preload-value` instead of the error `value-not-allowed`, which now applies to
  `includeSubDomains` only. `preload_issues` reports it as the new warning
  `preload.invalid`, as the hstspreload.org checker does, and it does not count as
  `preload`, so a header whose only `preload` has a value fails with
  `preload.missing`.
- The command line checks the first final response of a redirect chain
  (`curl -sIL`), not the last: the base domain's own response is the one hstspreload.org
  checks and the one a browser applies to that host. Interim (1xx) responses and a
  proxy's `Connection established` are skipped. When the first final response has no
  Strict-Transport-Security field but a later one has it, the exit status is 1 with
  the single issue `field.missing`; exit status 2 means no response has the field.
- The `max-age.too-large` message names 2^31 as this library's cap; RFC 6797 sets no
  ceiling and the value follows RFC 9111 by analogy.
- Error messages and `Issue` messages quote at most 40 characters of a directive name
  or value, followed by its length; 0.2.0 quoted the whole of it, megabytes included.
- `Hsts`, `Issue` and `HstsError` report `hstsheader` as their module, so `repr`,
  tracebacks and pickles name the public path instead of a private module.
- A `str` subclass passed to `parse`, `lint` or the preload checks is read as a plain
  `str`.
- `preload_issues` no longer warns `preload.max-age-over-ten-years` for a `max-age` the
  hstspreload.org checker cannot read (quoted, spaced around `=` or above 2^64 - 1); the
  error for that spelling is still there. Found by running the checker itself.
- When tolerant `parse` finds no usable `max-age` because the `max-age` directive breaks
  the grammar, the error is that directive's syntax error; 0.2.0 could report an
  unrelated earlier error such as a repeated unknown directive.
- `preload_issues` and `is_preloadable` (and `--preload`) report the new error
  `preload.misread` where the hstspreload.org checker reads a directive the header does
  not have: it cuts the header at every `;`, quoted strings included, and takes any name
  that starts with `max-age` for `max-age`. Headers such as
  `max-age=31536000; includeSubDomains; preload; max-agex=5`, or a `report-uri` whose
  quoted value holds `;max-age=2`, were called preloadable and the checker refuses them.
  Found by running the checker. Like the checker, the check reads the header's octets
  as UTF-8: a character up to U+00FF is the octet a latin-1 decode made of it, so the
  octets `C2 A0` are a no-break space the checker trims and a lone `A0` is an octet it
  keeps, and the long s (`C5 BF`) matches `s`.
- `parse`, `lint` and the preload checks refuse field lines given as a set, a frozenset
  or a dict's keys or items view with `TypeError`: without an order, the line read first
  depended on the hash seed.
- They take at most two items from an iterable of field lines, the second only to know
  that there is more than one, so a generator is no longer read to its end (an endless
  one never returned). The `multiple-fields` message no longer gives the number of lines,
  and items after the second are no longer checked for type.
- In a response head on the command line, a line of only spaces or tabs no longer ends
  the head: as RFC 9112 reads it, it is obsolete line folding that continues the field
  line before it, so a Strict-Transport-Security field after it is found.

### Fixed

- The first `syntax` finding, and so the error of strict `parse` and the first issue on
  the command line, could be an error that skipping a broken directive made up, ahead of
  the real first bad character: the Python string `'a=";=\x01"; max-age=1'` reported
  `'='` at offset 4 instead of U+0001 at offset 5. The first `syntax` finding is now
  always at the first character that breaks the grammar.
- `build`, `preload_issues` and `is_preloadable` check an `Hsts` again. A subclass that
  skips the checks, an instance changed with `object.__setattr__` or an object that only
  claims to be an `Hsts` could put any `max_age`, CR LF included, into the built header,
  or make the preload checks fail with an unrelated `TypeError`. Such a policy now raises
  as `Hsts` would.
- Reading a value with many folded lines, and a response head with many leading blank
  lines or folded lines, took time quadratic in the input; it is linear now.
- Skipping broken directives took time quadratic in the input when a backslash came
  before a double quote outside a quoted string (`a=\";` repeated): an 80 KB value took
  two minutes. It is linear now.
- The command line printed a traceback and exited 1 when the reader of its output
  stopped early (`| head`); it now stops quietly and the exit status still gives the
  verdict. Started with standard output closed, it no longer fails with a traceback
  and exit status 1 either.
- Started with standard input closed and no value, the command line printed a traceback
  and exited 1, the status that means "not honoured"; it is a usage error now (exit
  status 2), as for a terminal. So is standard input that is open but cannot be read,
  such as a file opened for writing only, which also gave a traceback and exit status 1.

### Added

- `hstsheader --version`.
- `Severity`, the type of `Issue.severity` (`Literal["error", "warning"]`).
- Typing overloads for `build`, so a type checker reports flags passed next to an
  `Hsts`, a call that always raises `TypeError`. The runtime signature is unchanged; a
  flag left as `None` means not given, as documented now.
- The `HstsError` constructor and its default code `invalid`, which this library never
  raises, are documented.
- The README says where each finding points: a `syntax` offset equal to the length of
  the value means it ended where more was needed, and an unterminated quoted string
  points at its opening quote.
- Every public name has a docstring with an example that runs as a test.

## [0.2.0] - 2026-10-19

### Added

- `parse(header, strict=True)` accepts only a header that a conforming browser honours
  (RFC 6797 sections 6.1 and 8.1) and raises `HstsError` with a `code` and an `offset`.
- `lint` lists every finding as an `Issue` with a code, a severity and an offset.
- `preload_issues` and `is_preloadable` check the hstspreload.org header requirements.
- `build` takes an `Hsts` object and an `extensions` mapping for further directives.
- `parse`, `lint` and the preload checks accept the field lines of a response and read the
  first one only.
- The `hstsheader` command line (also `python -m hstsheader`) checks a value or the output
  of `curl -sI` and prints JSON.
- `DELTA_SECONDS_MAX` and `PRELOAD_MIN_MAX_AGE` constants.
- Folded lines (obsolete line folding) are read as whitespace, with a warning.

### Changed

- The reader follows the directive grammar: token names, token or quoted-string values,
  whitespace around `;` and `=`. A broken directive is skipped up to the next `;` instead
  of failing the whole header in tolerant mode.
- The first `max-age` wins when it repeats (it used to be the last one); strict mode
  refuses any repeated directive.
- `includeSubDomains` or `preload` with a value is no longer read as asserted.
- `max-age` takes ASCII digits only (fullwidth and other Unicode digits used to pass) and
  values above 2147483648 are read as 2147483648 instead of failing on very long input.
- A quoted value is unescaped per RFC 9110: any quoted-pair stands for its octet.
- `Hsts` checks its fields on creation, and `build` refuses non-bool flags and a `max_age`
  above 2147483648.
- `bytes` input raises a `TypeError` that says to decode it first.

## [0.1.0] - 2026-10-12

Not published on PyPI.

- Add `parse` to read a Strict-Transport-Security header into a typed `Hsts` object.
- Add `build` to render a header value from a max-age and optional flags.
- Add the `Hsts` dataclass and the `HstsError` exception.
