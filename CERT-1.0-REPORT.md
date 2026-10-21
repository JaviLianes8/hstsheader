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
| 18 | Contracts bite (mutations) | PASS: 50 author mutants, 46 killed at once, 2 survivors killed by new contracts, 2 argued equivalent |
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

## Author mutation round (item 18)

50 mutants over every module, each applied alone to a fresh clone of the pushed branch at
c579455 on Elena's PC (CPython 3.14), the full suite (fetched sources and the
hstspreload checker present, e2e off) run with `-x` and a 300 s per-test limit; the
first failing test is listed. 46 were killed at once. M16 and M49 survived and are now
killed by the two contracts added in `tests/test_cert_regressions.py` (checked by
re-running each mutant against them). M04 and M32 are equivalent, for the reasons given.

| Id | Module | Mutation | Result | Caught by |
| --- | --- | --- | --- | --- |
| M01 | _chars.py | tchar drops the vertical bar | killed | tests/test_roundtrip.py::test_random_policies_survive_a_strict_round_trip |
| M02 | _chars.py | qdtext accepts DEL | killed | tests/test_fuzz.py::test_strict_reading_matches_the_grammar[12] |
| M03 | _chars.py | quoted-pair accepts DEL | killed | tests/test_review_fixes.py::test_quoted_pairs_follow_rfc_9110 |
| M04 | _chars.py | Unicode case folding for names | equivalent | equivalent: every text lowered is already ASCII (a token checked first), so str.lower gives the same |
| M05 | _chars.py | message cut off by one | killed | tests/test_cert_regressions.py::test_messages_quote_at_most_forty_characters |
| M06 | _chars.py | builder lets DEL through | killed | tests/test_build.py::test_extension_values_cannot_inject[\x7f] |
| M07 | _chars.py | quote does not escape backslash | killed | tests/test_build.py::test_extension_values_that_are_not_tokens_are_quoted |
| M08 | _model.py | sender ceiling off by one | killed | killed: tests/test_roundtrip.py fails to collect (module level Hsts(DELTA_SECONDS_MAX)) |
| M09 | _model.py | bool accepted as max_age | killed | tests/test_build.py::test_build_rejects_bool_max_age |
| M10 | _model.py | pickle drops offset | killed | tests/test_contract_api.py::test_hsts_error_keeps_code_and_offset_through_pickle_and_copy |
| M11 | _model.py | preload flag unchecked | killed | tests/test_build.py::test_build_refuses_flags_that_are_not_bool[preload] |
| M12 | _scan.py | NUL not reported | killed | tests/test_strict.py::test_strict_mode_refuses_what_a_user_agent_ignores[max-age=600\x00-control-character-11] |
| M13 | _scan.py | bare LF fold not unfolded | killed | tests/test_review_fixes.py::test_a_folded_line_is_whitespace |
| M14 | _scan.py | trailing backslash closes the string | killed | tests/test_strict.py::test_strict_mode_refuses_what_a_user_agent_ignores[max-age=600; |
| M15 | _scan.py | space after '=' not flagged | killed | tests/test_oracle_hstspreload.py::test_preloadable_headers_pass_the_site_checker[1] |
| M16 | _scan.py | empty directive points at the end | survived, then killed | survived; killed after adding test_a_trailing_empty_directive_points_at_the_last_semicolon |
| M17 | _scan.py | no recovery after an unterminated quote | killed | tests/test_parse.py::test_a_broken_directive_does_not_hide_the_ones_after_it |
| M18 | _scan.py | no whitespace after a value | killed | tests/test_docs.py::test_every_readme_example_runs_and_prints_its_comment |
| M19 | _scan.py | broken names keep case | killed | tests/test_cert_regressions.py::test_the_tolerant_error_names_the_broken_max_age |
| M20 | _lint.py | ten digit values capped | killed | tests/test_lint.py::test_exactly_two_to_the_31_is_not_capped |
| M21 | _lint.py | 2^31 itself flagged as capped | killed | tests/test_lint.py::test_exactly_two_to_the_31_is_not_capped |
| M22 | _lint.py | max-age=0 warned as leading zero | killed | tests/test_lint.py::test_a_single_zero_is_not_a_leading_zero |
| M23 | _lint.py | 2^64-1 unreadable | killed | tests/test_oracle_hstspreload.py::test_for_rfc_valid_headers_the_verdicts_agree[4] |
| M24 | _lint.py | repeated includeSubDomains soft | killed | tests/test_cli.py::test_preload_check_fails_when_browsers_ignore_the_header |
| M25 | _lint.py | last max-age wins | killed | tests/test_cli.py::test_an_ignored_value_exits_one |
| M26 | _lint.py | zero warning on the wrong flag | killed | tests/test_contract_api.py::test_every_documented_lint_code_is_produced_with_its_severity |
| M27 | _lint.py | two field lines not warned | killed | tests/test_cli.py::test_a_response_head_on_stdin |
| M28 | _lint.py | findings not sorted | killed | src/hstsheader/_lint.py::hstsheader._lint.lint |
| M29 | _lint.py | broken directives skip repeat check | killed | tests/test_cert_regressions.py::test_the_tolerant_error_names_the_broken_max_age |
| M30 | _lint.py | last field line read | killed | src/hstsheader/_parse.py::hstsheader._parse.parse |
| M31 | _parse.py | strict reports the last error | killed | tests/test_hostile.py::test_huge_names_and_values_in_build_errors_are_cut |
| M32 | _parse.py | broken max-age error search off by one | equivalent | equivalent: a max-age directive always has its name before its syntax error, so the error offset is never its start |
| M33 | _preload.py | soft repeats stay errors | killed | tests/test_cli.py::test_a_repeated_preload_is_not_honoured_by_the_rfc_but_still_preloadable |
| M34 | _preload.py | one year exactly refused | killed | tests/test_cli.py::test_preload_check |
| M35 | _preload.py | ten years counted with leap days | killed | tests/test_cert_regressions.py::test_the_ten_year_warning_stays_for_a_plain_max_age |
| M36 | _preload.py | spaced max-age still warned | killed | tests/test_cert_regressions.py::test_no_ten_year_warning_where_the_site_cannot_read_max_age[max-age |
| M37 | _preload.py | is_preloadable inverted on mixes | killed | src/hstsheader/_preload.py::hstsheader._preload.is_preloadable |
| M38 | _preload.py | spaced max-age accepted for preload | killed | tests/test_cert_regressions.py::test_no_ten_year_warning_where_the_site_cannot_read_max_age[max-age |
| M39 | _build.py | preload accepted as extension | killed | tests/test_build.py::test_extension_names_cannot_shadow_the_known_directives[Preload] |
| M40 | _build.py | duplicate check case sensitive | killed | tests/test_build.py::test_extension_names_must_be_unique_ignoring_case |
| M41 | _build.py | token values quoted | killed | src/hstsheader/_build.py::hstsheader._build.build |
| M42 | _build.py | flags written in the other order | killed | src/hstsheader/_build.py::hstsheader._build.build |
| M43 | _head.py | first response checked | killed | tests/test_review_fixes.py::test_response_heads_are_read_like_curl_prints_them[HTTP/1.1 |
| M44 | _head.py | field name case sensitive | killed | tests/test_cli.py::test_a_response_head_on_stdin |
| M45 | _head.py | fold joined without space | killed | tests/test_review_fixes.py::test_response_heads_are_read_like_curl_prints_them[HTTP/2 |
| M46 | _head.py | head does not end at blank line | killed | tests/test_review_fixes.py::test_response_heads_are_read_like_curl_prints_them[HTTP/2 |
| M47 | _cli.py | --preload does not set exit status | killed | tests/test_cli.py::test_preload_check |
| M48 | _cli.py | usage exit status 1 | killed | tests/test_cli.py::test_a_head_without_the_field_is_a_usage_error |
| M49 | _cli.py | empty argument is a usage error | survived, then killed | survived; killed after adding test_an_empty_argument_is_checked_as_a_value |
| M50 | _cli.py | honoured means a max-age was read | killed | tests/test_cli.py::test_an_ignored_value_exits_one |

## Gates (item 15)

At 6b6075e on Elena's PC (CPython 3.14) from a fresh clone, each command on its own, with
the fetched sources, the hstspreload checker, `HSTSHEADER_E2E=1` and
`HSTSHEADER_E2E_PYPI=1`: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` (329 passed, 0 skipped) all exit 0. Since then
only this report changed.
