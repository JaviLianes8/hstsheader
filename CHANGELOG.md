# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-21

The public API is now stable: the ten names in `hstsheader.__all__`, their parameter
names and defaults, the `Issue` codes listed in the README, the `HstsError` attributes
and the command line options, JSON keys and exit statuses. They change only in a new
major version. Upgrading from 0.2.0 needs a change only where code catches `HstsError`
for an argument of the wrong type (see below).

### Changed

- An argument of the wrong type now raises `TypeError` everywhere, as `parse` already
  did for `bytes`: `Hsts` and `build` with a `max_age` that is not an `int` (a `bool`
  included) or a flag that is not a `bool`, and `build` with `extensions` that is not a
  mapping, a name that is not a `str` or a value that is neither `str` nor `None`. In
  0.2.0 these raised `HstsError` with the code `type` (or `build.name` for a name that
  is not a `str`); that code is gone. Values of the right type that a header cannot
  carry still raise `HstsError`.
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

### Added

- `hstsheader --version`.
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
