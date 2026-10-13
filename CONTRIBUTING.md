# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Reference files

Some tests check the library against the RFCs, hstspreload.org and Chromium's parser.
Those files are not in the repository; fetch them once with
`python scripts/fetch_upstream.py` (each is checked against `tests/upstream/MANIFEST.json`).
Without them the tests that need them are skipped.

The installed-wheel test builds and installs the package; run it with
`HSTSHEADER_E2E=1 pytest tests/test_e2e_wheel.py`.

## Before you open a pull request

- Keep public API in `src/hstsheader/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
