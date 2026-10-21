# hstsheader 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to hstsheader. PyPI has 0.2.0 (uploaded
2026-10-19), which is byte for byte the `main` branch at d7e5426 (the wheel's modules
compared with the tree), so every change listed here is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (d7e5426, same code as PyPI 0.2.0)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: fetched sources, the hstspreload checker run live, real headers (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.0, every Python (items 8, 10, 13, 14)
- [x] Gates (item 15)
- [x] PR and trace guard CLEAN
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [ ] Merge and publish (item 17)

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: ten names, signatures and parameter names kept from 0.2.0 and pinned; every behaviour change in CHANGELOG and GUIDE |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: 9 doctests cover every public name; README (13 outputs) runs as a test |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed` shipped, no `Any` in the public API |
| 5 | Typed, documented, bounded errors | PASS: `HstsError` (a `ValueError`) with code and offset, `TypeError` for wrong types, messages quote at most 40 characters |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: 9 pinned sources, the hstspreload.org checker built from its Go source and run live, headers of 22 real sites fetched with curl |
| 8 | Real e2e from the wheel | PASS: wheel installed in a fresh venv and driven from an empty folder, console script and `python -m`, PyPI 0.2.0 upgraded in place |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS: three quadratic paths found and fixed |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t; 3.8.20 and 3.9.25 refused by `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge, verified comparison |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-21 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | see Author mutation round |
| 19 | Five independent QA lenses | pending |

## Baseline on 0.2.0 (before any change)

`ruff format --check .`, `ruff check .` and `mypy --strict src tests` exit 0; `pytest`
216 passed, 1 skipped (the installed-wheel test, which needs `HSTSHEADER_E2E=1`), with
the nine pinned sources fetched and matching the manifest. No public docstring had an
example.

Defects found in 0.2.0 by reading and then reproducing:

- Wrong argument types raised `HstsError` (a `ValueError`) with the code `type` in
  `Hsts` and `build`, but `TypeError` in `parse` and for flags next to an `Hsts`.
- Messages quoted whole directive names and values: a 1 MB unknown directive gave a 1 MB
  message.
- `HstsError` lost `code` and `offset` through `pickle` and `copy`.
- `preload_issues` warned "over ten years" for a quoted, spaced or 2^64-overflowing
  `max-age` that the site's checker cannot read and never warns about (found by running
  the checker).
- Tolerant `parse` could explain a broken `max-age` directive with an unrelated earlier
  error (for `x=1; x=2; Max-Age=` it reported the repeated `x`).
- Quadratic time: many folded lines in a value (each fold rebuilt the string), many
  leading blank lines in a head (`list.pop(0)`) and many folded lines in a head field
  (`+=` on a list item).
- The README linked LICENSE relatively, which breaks on PyPI, and named a GObject class
  as an alternative that was not verified.
- `scripts/release.ps1` refused any upload once the name existed on PyPI.

## API review (item 1)

Kept: the ten public names of 0.2.0 with their signatures, parameter names, kinds and
defaults, pinned by `tests/test_contract_api.py`; the `Issue` codes and severities, now
tied to the README tables by test; the command line JSON keys (pinned in
`tests/test_cli.py`) and exit statuses. Changed, all in the CHANGELOG and the GUIDE:
`TypeError` for every wrong argument type; bounded messages; `__module__` of `Hsts`,
`Issue` and `HstsError` is `hstsheader`; `HstsError` keeps `code` and `offset` through
pickle and copy; `str` subclasses read as plain text; the ten year warning only where
the site warns; the tolerant error names the broken `max-age`; `hstsheader --version`.

## Ground truth (item 7)

- Pinned sources (fetched again on 2026-10-21 by `scripts/fetch_upstream.py`, every
  sha256 matching `tests/upstream/MANIFEST.json`): RFC 6797, 2616, 9110, 9111, the
  hstspreload.org page, chromium/hstspreload `header.go` and `header_test.go` at
  d624d7c, Chromium `http_security_headers.cc` and `.h` at 78ed3b7. `tests/test_sources.py`
  reads the RFC examples, the preload thresholds and the checker's own 46 test vectors from
  them. Nothing fetched is committed or shipped.
- The hstspreload.org checker run live (`tests/test_oracle_hstspreload.py`): Go 1.27.3
  (go.dev, sha256 f26081f4...) built `tests/oracle`, which calls chromium/hstspreload at
  d624d7c (`go.sum` pins it), on eight seeded corpora of up to 15,000 headers. Every
  header `is_preloadable` accepts passes the checker; with no RFC error the verdicts and
  the ten year warning agree; where strict parsing succeeds both read the same `max-age`
  (capped at 2^31) and flags. The first run found the ten year warning difference above.
- Real headers (`tests/test_realworld.py`): the Strict-Transport-Security values that
  `curl -sI` printed for 22 sites on 2026-10-21 (three more sent none), each with the
  checker's verdict the same day. All read cleanly; `is_preloadable` matches the checker
  on all 22. The command line run on the raw curl output of all 25 heads gave exit 0 for
  the 10 preloadable, 1 for the other 12 and 2 for the three without the field.
- The comparison in the README was checked on 2026-10-21 by downloading and reading the
  latest releases of `secure` 2.0.1, `flask-talisman` 1.1.0, `pyramid_hsts` 1.3.0,
  `hstspreload` 2025.1.1 and `apifrom` 1.0.0, and running apifrom's
  `get_hsts_directives` on the inputs quoted there.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: an acceptor written separately from the RFC 6797 and RFC 9110
grammar is compared with strict parsing on 24,000 seeded inputs (no difference); 18,000
seeded inputs through every reader check totality (only `HstsError` or `TypeError`),
offsets inside the input and sorted, strict acceptance equal to "no error", tolerant equal
to strict when strict accepts, and `is_preloadable` consistent with `preload_issues`.
`tests/test_hostile.py`: 13 value shapes and 4 head shapes timed at 50,000 and 200,000
characters (linear), 1 MB inputs in every message path (all under 220 characters), and
1 MB heads through the command line.

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- Full suite on Elena's PC (CPython 3.14) from a fresh clone at c579455 with the fetched
  sources, the checker, `HSTSHEADER_E2E=1` and `HSTSHEADER_E2E_PYPI=1`: 327 passed, 0
  skipped. The e2e tests build the wheel and sdist, inspect both, install the wheel in a
  fresh venv and drive the API, the console script, `python -m hstsheader` and
  `--version` from an empty folder with `-I`; and install 0.2.0 from PyPI, confirm its
  old behaviour, upgrade it in place to the built wheel and run the full program again.
- Every interpreter on this PC from `requires-python` up, at c579455: wheel and sdist
  built from a fresh clone, `twine check --strict` PASSED for both, the wheel installed in
  a fresh venv and the sdist's own suite run with `src` removed (fetched sources and the
  checker present): CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2
  free-threaded, 315 passed and 2 skipped each (the e2e tests, which need the source
  tree), plus 1 failure in the em-dash scan, which called `git ls-files` outside a
  checkout; fixed in 2e08546 and re-run from that sdist tree (9 passed). The 9 doctests
  pass from the installed package on each. 3.8.20 and 3.9.25 refuse the wheel.
- Wheel: the package, `py.typed`, `__main__.py`, the entry point and
  `licenses/LICENSE`; no tests or scripts. Sdist: sources, tests, `tests/oracle`, the
  manifest without fetched files, docs and LICENSE; no planning notes, no report, no
  scratch files.
