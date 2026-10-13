# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - not released yet

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
