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
| 9 | Seeded fuzz, no crash, hang or blowup | PASS: three quadratic paths found and fixed, a fourth found by QA lens c and fixed in f22e655; an iterable of field lines read to its end (lens c, round 3) fixed in 7633c28; a traceback on unreadable standard input (lens c, round 4) fixed in 103a25a |
| 10 | Supported Pythons | PASS (last run at 7633c28): CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t; 3.8.20 and 3.9.25 refused by `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge, verified comparison |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-21 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: 50 author mutants, 46 killed at once, 2 survivors killed by new contracts, 2 argued equivalent; every lens e survivor of rounds 1 to 5 killed by a new contract |
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
`Issue` and `HstsError` is `hstsheader` (with a `__reduce__` that keeps `code` and
`offset` through pickle and copy, as 0.2.0 already did); `str` subclasses read as plain
text; the ten year warning only where the site warns; the tolerant error names the broken
`max-age`; `hstsheader --version`. After the third QA round: `preload.misread`, sets
refused as field lines, at most two field lines taken from an iterable, a line of spaces
in a head read as a fold, and typing overloads for `build` (see Round 3).

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
`mypy --strict src tests` and `pytest` (329 passed, 0 skipped) all exit 0. After the
QA rounds the gates were run again at f22e655, 0687e52, 7633c28 and 589a944; see Rounds
1 to 4 below.

## QA lenses (item 19)

### Round 1

Five independent lenses checked c8a317c. Lens d found only F1 below, lens a four findings,
lens b three, lens c one and lens e six surviving mutants. Every finding is fixed in
f22e655; no finding is disputed.

| Lens | Id | Severity | Finding | Fix | Contract |
| --- | --- | --- | --- | --- | --- |
| a | A1 | medium | `typing.get_type_hints(Issue)` raised `NameError`: `Severity` was private and the class reports `hstsheader` as its module | `Severity` exported and listed in `__all__` (eleven names), documented with an example in the package docstring | `test_type_hints_resolve_on_every_public_class_and_function`, `test_the_severity_type_is_public` |
| a | A2 | low | README documented `lint(header)`, the parameter was `value` | parameter renamed to `header`, like the other readers; in the CHANGELOG and the GUIDE upgrade note | `test_lint_takes_its_argument_as_header`, signature pin |
| a | A3 | low | `parse(strict=...)` read any value by truthiness | `TypeError` for a `strict` that is not a `bool` | `test_strict_must_be_a_bool` |
| a | A4 | low | README said empty input exits 2; an empty argument exits 1 | README says "empty standard input"; the GUIDE states both cases | doc only |
| b | F1 | medium | the command line checked the last response of a redirect chain | the first final response is checked (1xx and a proxy's `Connection established` skipped); README, GUIDE and docstring reasons corrected | `test_the_first_response_of_a_redirect_chain_is_checked` and three more in `tests/test_qa_round1_cli.py` |
| b | F2 | medium | `preload=yes` was an RFC 6797 error, but RFC 6797 does not define `preload` | a value on `preload` is the warning `preload-value` (strict parsing accepts it, `preload` false); `preload_issues` reports the error `preload.invalid`, as the hstspreload.org checker does; `value-not-allowed` is for `includeSubDomains` only | `test_a_value_on_preload_is_an_unknown_directive_to_rfc_6797`, `test_a_value_on_preload_is_refused_by_the_preload_rules`, the fuzz acceptor updated |
| b | F3 | low | the 2^31 cap was credited to RFC 9111 more strongly than it says | README, GUIDE, package docstring and the `max-age.too-large` message present it as this library's cap, by analogy with RFC 9111 | `test_the_sender_ceiling_is_presented_as_this_library_choice` |
| c | F1 | high | skipping broken directives was quadratic for a backslash before a quote outside a quoted string (`a=\";` repeated) | new `_skip.py`: the skip remembers the outcome of the quoted-string reader per index, so each index is read once; differential check against the old skip on 280,602 calls over 60,000 random strings gave no difference; `a=\";` x 80,000 (400 KB) lints in 0.6 s | four new shapes in `tests/test_hostile.py` |
| d | F1 | low | a reader closing the pipe early gave a traceback and exit 1 | the write catches `BrokenPipeError` and Windows `EINVAL`, sends the rest to the null device, and the exit status keeps the verdict | `test_a_closed_output_pipe_keeps_the_verdict`, `test_a_reader_that_stops_early_gets_no_traceback` (subprocess) |
| e | F1-M14 | medium | obs-text after a backslash not pinned | | `test_obs_text_may_follow_a_backslash_in_a_quoted_string`, `test_del_and_non_latin_1_cannot_follow_a_backslash` |
| e | F2-M19 | medium | offsets after a fold not pinned | | `test_offsets_after_a_folded_line_point_at_the_input` |
| e | F3-M21 | medium | NUL read as SP not pinned | | `test_a_nul_is_reported_once_and_read_as_whitespace` |
| e | F6-M75 | medium | `honoured` for a header with warnings only not pinned | | `test_a_header_with_only_warnings_is_honoured` |
| e | F4-M38 | low | `max-age.zero-subdomains` condition not pinned | | `test_the_zero_max_age_warning_needs_a_max_age_of_zero` |
| e | F5-M45 | low | `bytearray` and `memoryview` refusal not pinned | | `test_binary_input_is_a_type_error_with_the_decode_hint` |

Every behaviour test in `tests/test_qa_round1.py` and `tests/test_qa_round1_cli.py` was
run against c8a317c first and failed there (22 failures); the lens e contracts pin
behaviour that was already right and passed there, as a contract against a mutant should.
The new hostile shapes were timed on c8a317c instead of run to their 300 s limit:
`a=\";` x 1,000 took 0.49 s and x 2,000 took 2.0 s.

Behaviour changes are in the CHANGELOG under 1.0.0 (Changed, Fixed, Added) and the GUIDE
upgrade note.

Verification at f22e655:

- On Elena's PC (CPython 3.14.2) from a fresh clone with the fetched sources and the
  hstspreload checker: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
  `mypy --strict src tests` and `pytest` exit 0 (386 passed, 2 skipped: the two e2e
  tests, run next). Then with `HSTSHEADER_E2E=1` and `HSTSHEADER_E2E_PYPI=1`:
  `tests/test_e2e_wheel.py` and `tests/test_qa_round1_cli.py`, 12 passed.
- On this PC, wheel and sdist built from a fresh clone, `twine check --strict` PASSED, the
  wheel holds `_skip.py`; the sdist's suite with `src` removed, against the installed
  wheel and with the checker: 377 passed and 2 skipped (e2e) on CPython 3.10.19, 3.11.5,
  3.12.12, 3.13.2, 3.14.2 and 3.14.2t, 9 doctests each; 3.8.20 and 3.9.25 refuse the wheel.
- The reviewers' command line repros: the redirect head exits 1 with field
  `max-age=300`; `| head -n 1` on a large report gives statuses `0 0 0` and an empty
  stderr; `hstsheader ""` exits 1 and empty standard input exits 2.

### Round 2

Five independent lenses checked 98e3f77. Every round 1 finding was confirmed fixed. The
new findings are all fixed in 0687e52; none is disputed.

| Lens | Id | Severity | Finding | Fix | Contract |
| --- | --- | --- | --- | --- | --- |
| a, b | A5, N1 | low | with `curl -sIL`, a first final response without the field and a later one with it gave "no Strict-Transport-Security field in the input" and exit 2 (live for apple.com, amazon.com, google.com, paypal.com) | exit 1 with the single issue `field.missing`, `field` and `policy` null; exit 2 only when no response has the field; README, GUIDE and CHANGELOG updated | `test_a_later_field_after_a_redirect_without_one_is_a_rejection`, `test_a_chain_without_the_field_anywhere_is_a_usage_error` |
| b | N2 | low | `preload.invalid` was an error, but `header.go` raises `header.parse.invalid.preload` as a warning and the site blocks on errors only: 3 of about 61,000 differential headers were refused here and accepted by the checker | `preload.invalid` is a warning; a header whose only `preload` has a value still fails with `preload.missing` | `test_a_value_on_preload_next_to_a_bare_preload_is_only_a_warning`, `test_a_value_on_preload_is_only_a_warning_on_both_sides` (run against the checker) |
| d | N1 | low | started with standard output closed (`>&-`), the command line printed a traceback and exited 1 | `_write` returns quietly when `sys.stdout` is `None`; the exit status keeps the verdict | `test_no_stdout_at_all_keeps_the_verdict`, `test_a_process_started_without_stdout_keeps_the_verdict` (subprocess) |
| e | N01, N06, N07, N08, N18, N27, N29, N32, N34, N36, N40 | medium | eleven surviving mutants in `_head` (interim status match, interim-only heads), `_cli` (write error handling), `_skip` (quoted-pair and control characters in a skipped string) and `_scan` (skip over the raw text) | | `tests/test_qa_round2.py`, `tests/test_qa_round2_cli.py` |

The redirect, preload and closed-stdout tests failed on 98e3f77. Each lens e mutant and
the two fix sites (A5, N1d) were applied alone to a fresh clone of 0687e52 on Elena's PC
(CPython 3.14.2) and run against the round 2 contracts: all 13 killed.

Verification at 0687e52:

- On this PC: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
  `mypy --strict src tests` exit 0.
- On Elena's PC (CPython 3.14.2) from a fresh clone with the fetched sources and the
  hstspreload checker: the same four commands and `pytest` exit 0 (419 passed, 2
  skipped: the e2e tests, run next). Then with `HSTSHEADER_E2E=1` and
  `HSTSHEADER_E2E_PYPI=1`: `tests/test_e2e_wheel.py`, `tests/test_qa_round1_cli.py` and
  `tests/test_qa_round2_cli.py`, 20 passed.
- On this PC, wheel and sdist built from a fresh clone of the pushed 0687e52,
  `twine check --strict` PASSED for both, the wheel holds only the package, `py.typed`,
  the entry point and the license; the sdist's suite with `src` removed, against the
  installed wheel and with the checker: 410 passed and 2 skipped (e2e) on CPython
  3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t, 9 doctests each; 3.8.20 and
  3.9.25 refuse the wheel.

### Round 3

Five independent lenses checked 2fd8202. Lens a found four issues, lens b two, lens c
three, lens d two (the same as A1 in lens a) and lens e four surviving mutants. Every
finding is fixed in 7633c28; none is disputed.

| Lens | Id | Severity | Finding | Fix | Contract |
| --- | --- | --- | --- | --- | --- |
| a, d | A1, F1, F2 | medium | the 1.0.0 CHANGELOG credited two fixes to 0.2.0 behaviour that the PyPI 0.2.0 never had: `HstsError` already kept `code` and `offset` through pickle and copy (its attributes travel in `__dict__`), and `get_type_hints(Issue)` resolved there (the `NameError` existed only on the release branch, after `__module__` became `hstsheader`) | both entries removed; the same false claim removed from this report's baseline list and API review | reproduced first on the 0.2.0 sources (`main`) with CPython 3.13.2: four copies give `duplicate 12`, and the hints resolve; the 1.0 pickle and hints tests stay as contracts |
| a | A2 | low | `build(Hsts(...), include_subdomains=True)` type-checked but always raises; `None` flags were undocumented | two `@overload` signatures (an `int` with flags that are `bool` or `None`, an `Hsts` with `None` only); runtime signature unchanged; `None` as "not given" documented in the docstring, README and GUIDE | `test_flags_next_to_an_hsts_are_a_type_error_for_type_checkers` (runs mypy on a consumer), `test_none_flags_mean_not_given` |
| a | A3 | low | the `HstsError` constructor and its default code `invalid` were documented nowhere | documented in the `HstsError` docstring and the GUIDE error table (`invalid`: never raised by the library) | `test_a_caller_made_error_has_the_documented_default_code`; the GUIDE table test now raises it |
| a | A4 | low | `## [0.1.0]` had no date and was never on PyPI | dated 2026-10-12 (commit 6bd47ec) with "Not published on PyPI" (PyPI lists only 0.2.0; no tags) | doc only |
| b | F1 | medium | `is_preloadable` accepted RFC-valid headers that the hstspreload.org checker refuses: it cuts at every `;` (quoted strings included) and takes any name starting with `max-age` for `max-age` | new private `_checker.py` mirrors that reading (split, Go `strings.TrimSpace` set, prefix and `EqualFold` matches); each piece the checker takes for `max-age`, `includeSubDomains` or `preload` where RFC 6797 reads no such directive is the new error `preload.misread`. The second GUIDE property now excludes misread headers, which are refused even where the checker would still take them (documented) | ten tests in `tests/test_qa_round3.py`, `test_a_misread_header_is_not_preloadable` (CLI); the oracle corpus now has both classes and `test_the_checker_reads_a_misread_header_as_other_directives` |
| b | F2 | low | README "Where Chromium differs" missed Chromium's quoted-string leniency; GUIDE said strict acceptance is "exactly" RFC 6797 | README lists the second leniency (any character inside quotes and after a backslash, from Chromium's `UnquoteImpl`); GUIDE, `Issue` and `lint` docstrings say quoted strings are read by RFC 9110 and where RFC 2616 differs | doc only |
| c | C1 | medium | with standard input closed and no value, the command line crashed with `AttributeError` and exit 1 (the "not honoured" status) | `sys.stdin is None` takes the usage error path (exit 2) | `test_no_stdin_and_no_value_is_a_usage_error`, `test_a_process_started_without_stdin_exits_with_a_usage_error` (subprocess), `test_no_stdin_with_a_value_still_checks_it` |
| c | C2 | low | a set of field lines gave answers depending on `PYTHONHASHSEED` | `collections.abc.Set` (sets, frozensets, dict keys and items views) raises `TypeError` | `test_unordered_collections_are_refused`, `test_dict_values_and_tuples_keep_their_order` |
| c | C3 | low | an iterable of field lines was read to its end; an endless one never returned | at most two items are taken (`islice`); the `multiple-fields` message says "more than one" | `test_only_the_first_two_field_lines_are_read` (a generator that fails on a third pull) |
| e | F4-M110 | medium | a head line of only spaces or tabs ended the head, untested | decided by RFC 9112 (`HTTP-message` ends at an empty line; `obs-fold = OWS CRLF RWS`): such a line continues the field above, so the head goes on; CHANGELOG, README, GUIDE | `test_a_line_of_spaces_in_a_head_continues_the_field_line`, `test_a_line_of_spaces_does_not_end_the_head` (CLI) |
| e | F1-M97 | low | `preload.max-age-quoted` describing only the used `max-age` was not pinned | | `test_quoted_applies_only_to_the_max_age_that_was_used` |
| e | F2-M96 | low | the same for `preload.max-age-spaced` | | `test_spaced_applies_only_to_the_max_age_that_was_used` |
| e | F3-M99 | low | the null offset of `field.missing` was not pinned | | `test_field_missing_is_about_the_header_as_a_whole` |

Every test in `tests/test_qa_round3.py` and `tests/test_qa_round3_cli.py` was run on
2fd8202 first: 21 failed there (the misread, unordered, lazy, blank line, overload and
stdin tests); the rest pin behaviour that was already right. The four lens e mutants,
applied alone to 7633c28, are all killed by these contracts (M110 restored as the old
blank line rule), and so are four mutants of the new `_checker.py` (prefix `max-age=`
only, trimming SP and HTAB only, any directive at the offset matching, the untrimmed
offset).

The new rule was checked against the checker binary (built from `tests/oracle`) on
30,632 headers from two seeded runs of a separate generator with both classes, Go
whitespace and folds: no header `is_preloadable` accepts is refused by the checker, and
with no RFC error and no `preload.misread` the verdicts and the ten year warning agree
in every case; 169 RFC-valid misread headers are refused here though the checker takes
them (a piece repeating a directive the header has), the documented exception.

Verification at 7633c28:

- On Elena's PC (CPython 3.14.2) from a fresh clone with the fetched sources, the
  hstspreload checker, `HSTSHEADER_E2E=1` and `HSTSHEADER_E2E_PYPI=1`:
  `ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests`
  and `pytest` exit 0 (455 passed, 0 skipped).
- On this PC, wheel and sdist built from a fresh clone of the pushed 7633c28,
  `twine check --strict` PASSED for both, the wheel holds the package (with
  `_checker.py`), `py.typed`, the entry point and the license; the sdist's suite with
  `src` removed, against the installed wheel and with the checker: CPython 3.10.19, 3.11.5 and 3.12.12
  443 passed and 3 skipped (the two e2e tests, and the mypy consumer test, mypy not being
  installed there), CPython 3.13.2, 3.14.2 and 3.14.2t (with mypy) 444 passed and 2
  skipped (e2e), 9 doctests each; 3.8.20 and 3.9.25 refuse the wheel.
- The commit that records this round also rewords two README sentences (the pointer to
  the guide on quoted strings, line wrapping); `tests/test_docs.py` and
  `tests/test_contract_api.py` pass on it, and the four gate commands exit 0.

### Round 4

Lenses b, c, d and e checked 370723f (lens a was not rerun this round). Lenses b, d and
e found the same defect from three sides (N1), lens c one new defect (C4), and lens e
three surviving mutants of `_checker.py` (N2 to N4); lens c and lens e confirmed every
earlier finding fixed. Every finding is fixed in 103a25a and 589a944; none is disputed.

| Lens | Id | Severity | Finding | Fix | Contract |
| --- | --- | --- | --- | --- | --- |
| b, d, e | N1 | medium | `preload.misread` trimmed and folded Python characters, but the checker reads the octets as UTF-8: with the head decoded as latin-1 (the command line, and the GUIDE advice), the octets `C2 A0`, `C2 85`, `E2 80 80` or `E3 80 80` before `max-age` inside a quoted value were missed (preloadable, exit 0, the checker refuses: B1, B2), the same before `preload` or the long s `C5 BF` in `includeSubDomains` were missed (B3, B4), and a lone `A0` or `85`, which Go keeps as invalid UTF-8, gave a false misread (B5, B6) | `_checker.py` works on octets: a character up to U+00FF is its latin-1 octet, one above stands for its UTF-8 octets; pieces are trimmed by matching the UTF-8 forms of Go's `unicode.IsSpace` set (an invalid octet is never a space), the names are compared on the UTF-8 reading with the long s folded, and octet offsets map back to characters. GUIDE, CHANGELOG and the `preload_issues` docstring describe the octet reading; the oracle driver (`tests/oracle/main.go`) now takes each header as hex octets, so octets that are not UTF-8 reach the checker unchanged | `tests/test_qa_round4.py` (B1 to B6, every Go space and the code points around them, lone octets, the long s, characters above U+00FF, offsets inside a run of them), `tests/test_qa_round4_cli.py` (B1 and B5 by subprocess), `tests/test_oracle_octets.py` (the checker on the same octets for every case); the oracle corpus gains UTF-8 spaces, the long s and lone octets; the round 3 test that pinned the character reading of `\xa0` and `\x85` now uses their UTF-8 octets |
| c | C4 | medium | standard input open but unreadable (a write-only file) made the command line crash with `OSError` and exit 1, the "not honoured" status | the read is guarded: `OSError` or `ValueError` takes the usage error path (exit 2, one line, no traceback); GUIDE and CHANGELOG | `test_standard_input_that_cannot_be_read_is_a_usage_error` (subprocess with a write-only file as stdin) |
| e | N2 | low | the bounds of the Go space set were unpinned (K04, K05, K20 survived) | | every member and its nearest non-members on both sides, as UTF-8 octets, in `tests/test_qa_round4.py` and against the checker in `tests/test_oracle_octets.py` |
| e | N3 | low | the right trim of a piece was unpinned (K12) | | `test_space_after_the_name_is_trimmed`, `test_every_go_space_in_utf8_is_trimmed_after_the_name` |
| e | N4 | low | the long s fold was unpinned (K06, K15); the Kelvin entry was dead (K07) | Kelvin entry removed: an exhaustive run of Go's `strings.EqualFold` and `strings.ToLower` over every code point shows the long s is the only non-ASCII character folding to a letter of `preload` or `includeSubDomains`, and none lowers to one of `max-age=` | `test_the_long_s_in_utf8_folds_to_s`, `test_the_long_s_counts_as_s_outside_a_quote_too`, `test_a_character_above_latin1_stands_for_its_utf8_octets` |

Every new test was run on 370723f first: the B1 to B6 tests, the Go space tests for
every member outside SP and HTAB, the lone `85` and `A0` octet tests, the long s tests,
the above-latin-1 test, the three command line tests and both checker tests failed
there. The reviewers' byte probe (`bytes_probe.py`, the checker on raw octets) gives at
589a944 the checker's verdict for B1 to B6 through the API and the command line.

Mutants of the new `_checker.py`, each applied alone and run against the round 3 and
round 4 contracts with the checker: the lens e survivors K04 (no non-ASCII spaces), K05
(U+200A dropped), K20 (U+000E added), K12 (no right trim) and K06 (no long s fold), and
the character reading of N1 again, U+0085 dropped, U+3000 dropped, the right trim one
octet short, the offset map ignoring runs above U+00FF and the offset map counting
octets inside such a run are all killed (the last by a test added for it, a piece that
ends inside such a run). Decoding a piece with U+FFFD for invalid octets instead of
rejecting it survives and is equivalent: a piece with U+FFFD equals neither name, as a
piece that fails to decode.

Performance stays linear: 640,000 characters of U+3000 in one quoted value take 0.2 s
in the misread check, a run of 600,000 of them followed by 100,000 `;preload` pieces
0.8 s, and on the round 3 shapes the whole of `preload_issues` keeps its time
(`tests/test_hostile.py` within a second of 370723f on this PC).

Verification at 589a944 on Elena's PC (CPython 3.14.2) from a fresh clone with the
fetched sources and the checker built from `tests/oracle` (hex input): `pytest` 543
passed and 3 skipped (the two e2e tests, which need `HSTSHEADER_E2E` and PyPI, and the
mypy consumer test, mypy not installed there). On this PC `ruff format --check .`,
`ruff check .`, `mypy --strict src` and `mypy --strict src tests` exit 0, and the
mypy consumer test passes.

### Round 5

Lens e checked b41d39e and confirmed N1 to N4 fixed: the four raw octet command line
cases and the N2 to N4 repros match the checker, and a differential run of 75,282
headers (every code point to U+30FF plus U+FEFF, U+FFFD and points past the basic plane,
as characters and as UTF-8 octets, before the name, after it and on both sides) and of
every non-ASCII character folding to an ASCII letter shows no difference from the
checker. Its 40 mutants of the code changed since 370723f: 36 killed, one equivalent
(A38: the `ValueError` arm of the standard input guard, since a closed or detached stream
fails earlier at `isatty()` and a read that is not allowed raises
`io.UnsupportedOperation`, an `OSError`), three survived. The survivors were missing
contracts, not wrong behaviour: the library already agreed with the checker on every
repro. Both findings are fixed with tests only, so the library and the CHANGELOG are
unchanged; none is disputed.

| Lens | Id | Severity | Finding | Contract |
| --- | --- | --- | --- | --- |
| e | S1 | low | U+180E and U+FEFF were not pinned as non-members of Go's space set: adding either to `_GO_SPACE` (A11, A12) passed every test | U+180E and U+FEFF join the non-members in `tests/test_qa_round4.py` and the checker's code list in `tests/test_oracle_octets.py`; `tests/test_qa_round5.py` sweeps every code point to U+30FF plus U+FEFF, U+FFFD and three past the basic plane, as UTF-8 octets and as characters, before and after the name, and asserts a misread exactly for Go's spaces (and `;`); `test_every_code_point_is_trimmed_exactly_when_the_checker_trims_it` runs the same sweep (38,351 headers) against the checker itself |
| e | S2 | low | headers mixing octets 0x80 to 0xFF with a character above U+00FF were not pinned: reading every non-ASCII character of such a header as UTF-8 (A18) passed every test | the two repros as tests (a wide character with `C2 A0` before `preload` is misread, with a lone `A0` before `max-age=1` it is not) and as checker cases in `CASES`; every character and UTF-8 form up to U+00FF swept with a character above U+00FF after the quote, in `tests/test_qa_round5.py` and against the checker; the oracle driver now gets each character above U+00FF as its UTF-8 octets, as `preload_issues` reads it |

The new tests pass on b41d39e, and each surviving mutant applied alone fails them: A11
and A12 fail both sweeps, the U+180E and U+FEFF test, the round 4 non-member test and
both checker sweeps; A18 fails the latin-1 sweep beside a wide character, both repro
tests, the checker cases and the checker sweep. The library sweep takes about two
seconds, the checker sweep three.

Verification at the commit that adds these contracts (a6c2ebd), on Elena's PC (CPython
3.14.2) from a clone of the local branch with the fetched sources and the checker built
from `tests/oracle`: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` exit 0 (553 passed, 2 skipped: the two e2e tests,
which need `HSTSHEADER_E2E` and PyPI).

### Disputed findings

None in rounds 1 to 5.
