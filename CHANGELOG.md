# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- Add `parse` to read a Strict-Transport-Security header into a typed `Hsts` object.
- Add `build` to render a header value from a max-age and optional flags.
- Add the `Hsts` dataclass and the `HstsError` exception.
