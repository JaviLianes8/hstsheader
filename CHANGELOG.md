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
- `HstsError` keeps `code` and `offset` through `pickle` and `copy` (0.2.0 reset them
  to `invalid` and `None`).
- A `str` subclass passed to `parse`, `lint` or the preload checks is read as a plain
  `str`.
- `preload_issues` no longer warns `preload.max-age-over-ten-years` for a `max-age` the
  hstspreload.org checker cannot read (quoted, spaced around `=` or above 2^64 - 1); the
  error for that spelling is still there. Found by running the checker itself.
- When tolerant `parse` finds no usable `max-age` because the `max-age` directive breaks
  the grammar, the error is that directive's syntax error; 0.2.0 could report an
  unrelated earlier error such as a repeated unknown directive.

### Fixed

- Reading a value with many folded lines, and a response head with many leading blank
  lines or folded lines, took time quadratic in the input; it is linear now.
- Skipping broken directives took time quadratic in the input when a backslash came
  before a double quote outside a quoted string (`a=\";` repeated): an 80 KB value took
  two minutes. It is linear now.
- `typing.get_type_hints(Issue)` raised `NameError`, so tools that resolve dataclass
  hints failed on it.
- The command line printed a traceback and exited 1 when the reader of its output
  stopped early (`| head`); it now stops quietly and the exit status still gives the
  verdict. Started with standard output closed, it no longer fails with a traceback
  and exit status 1 either.

### Added

- `hstsheader --version`.
- `Severity`, the type of `Issue.severity` (`Literal["error", "warning"]`).
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

## [0.1.0]

- Add `parse` to read a Strict-Transport-Security header into a typed `Hsts` object.
- Add `build` to render a header value from a max-age and optional flags.
- Add the `Hsts` dataclass and the `HstsError` exception.
