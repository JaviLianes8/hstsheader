# hstsheader improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: RFC 6797, RFC 9110, RFC 9111, RFC 2616, hstspreload.org, the hstspreload header checker, the Chromium header parser
- [x] Grammar-driven scanner with offsets: tokens, quoted strings, implied whitespace, recovery
- [x] Two reading modes: strict (the RFC 6797 processing model) and tolerant (recover the intent)
- [x] Linter: every finding with a code, a severity and an offset
- [x] Preload eligibility checker (hstspreload.org header requirements)
- [x] Safe builder: typed flags, capped max-age, extension directives without injection
- [x] Command line
- [ ] Contracts: pinned sources, README examples, typing, installed wheel
- [x] Docs and packaging: README, CHANGELOG, metadata, sdist contents
- [ ] Gates: ruff format, ruff check, mypy --strict, pytest
- [ ] Mutation run: removing guarded logic makes the suite fail
- [ ] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` gives `parse`, `build`, the frozen `Hsts` dataclass and `HstsError`. Probed
against the sources below:

- `max-age` is read with `str.isdigit()` and `int()`, so a fullwidth seven and Arabic-Indic
  digits are accepted as numbers, a superscript two escapes as a bare `ValueError` instead of
  `HstsError`, and a value of 5000 digits trips the interpreter's integer conversion limit.
  RFC 6797 section 6.1.1 allows only ASCII `1*DIGIT`.
- A repeated directive is accepted and the last `max-age` wins. Section 6.1 rule 2 says every
  directive appears once, and rule 4 says a UA ignores a header that breaks the syntax.
- `includeSubDomains=no` is read as asserted, although section 6.1.2 defines a valueless
  directive (Chromium refuses the whole header in this case).
- Syntax is never checked: a name with a space, an unterminated quote, junk after a value,
  a comma instead of a semicolon and CR LF inside the value all end in a confusing message
  about `max-age`, or are silently accepted for directives other than `max-age`. There are no
  offsets.
- The quoted form drops quoted-pairs only for two characters; RFC 9110 section 5.6.4 says
  any quoted-pair stands for the octet after the backslash.
- `bytes` input gives a `TypeError` from inside `str.split`.
- `build` takes any truthy value as a flag and writes any integer, including 10**40.
  There is no way to add an extension directive, no linter, no preload check and no command
  line.

## Sources (fetched 2026-10-13)

- RFC 6797, https://www.rfc-editor.org/rfc/rfc6797.txt: the field grammar and the rules for
  directives (6.1), max-age (6.1.1), includeSubDomains (6.1.2), the examples (6.2), the UA
  processing model including "first field only" and max-age zero (8.1). Errata page
  https://www.rfc-editor.org/errata/rfc6797 read: five reports, all rejected, none changes the
  grammar.
- RFC 2616, https://www.rfc-editor.org/rfc/rfc2616.txt: the grammar RFC 6797 builds on,
  implied linear whitespace and the token and separator sets (2.1, 2.2).
- RFC 9110, https://www.rfc-editor.org/rfc/rfc9110.txt: field values and CR, LF, NUL (5.5),
  token (5.6.2), whitespace (5.6.3), quoted-string and quoted-pair (5.6.4).
- RFC 9111, https://www.rfc-editor.org/rfc/rfc9111.txt: the current delta-seconds rule and the
  2147483648 ceiling for values that overflow (1.2.2).
- https://hstspreload.org/: submission requirements (max-age at least 31536000,
  includeSubDomains, preload, served on the base domain).
- chromium/hstspreload `header.go` at commit d624d7c87b33307629f776b26c79448ca193a38f: the
  checker behind the site. It does not accept a quoted max-age, warns on leading zeros, on
  repeated directives and on max-age above ten years, and treats max-age=0 as a removal.
- Chromium `net/http/http_security_headers.cc` and `.h` at commit
  78ed3b7f37599d8a7dba1aa8375a22a23740a31d: a shipping UA parser. It refuses the header on a
  repeated max-age or includeSubDomains, on a value for includeSubDomains and on non-token
  unknown directives, and it clamps max-age (an overflow included) to one year.
- None of these files is committed. `tests/upstream/MANIFEST.json` records URL, revision,
  size, sha256 and licence; `scripts/fetch_upstream.py` fetches and checks them into the
  ignored `tests/upstream/` folder, and the tests that read them skip while they are absent.

## Ranked improvements

1. **Correct max-age.** ASCII digits only, quoted form unescaped before the check, leading
   zeros accepted, values above 2147483648 read as 2147483648 without converting long digit
   strings. Every failure is an `HstsError` with a code and an offset.
2. **Grammar-driven scanner.** `[ directive ] *( ";" [ directive ] )` with token names,
   token or quoted-string values, implied whitespace around `;` and `=`, and offsets for every
   directive. CR, LF, NUL and other controls are syntax errors. Names are compared with ASCII
   case folding only. `bytes` gets a clear `TypeError`.
3. **Strict and tolerant reading.** `parse(value, strict=True)` applies the RFC 6797 model: a
   header that a conforming UA must ignore raises `HstsError` (syntax, missing or malformed
   max-age, repeated directive, a value on a valueless directive). The default tolerant mode
   recovers the intent: it skips broken directives, keeps the first max-age and refuses only a
   header with no usable max-age. Both accept several field lines and use the first (8.1).
4. **Linter.** `lint(value)` lists every finding as an `Issue` (code, message, severity,
   offset): errors mean a UA ignores the header, warnings flag legal but risky choices
   (unknown or empty directives, leading zeros, a capped value, a quoted max-age, a zero
   max-age with includeSubDomains, more than one field line).
5. **Preload eligibility.** `preload_issues(value)` and `is_preloadable(value)` apply the
   hstspreload.org header requirements on top of the RFC errors: one year minimum, both flags,
   a separate code for max-age=0, a warning above ten years, and an error for a quoted max-age
   because the site's checker refuses it.
6. **Safe builder.** `build` takes an `Hsts` or the keyword form, refuses non-bool flags and
   values above the ceiling, and writes extension directives with token names and token or
   quoted-string values; names that clash with the three known directives, control
   characters and non-ASCII text are refused, so no header can be injected.
   `parse(build(policy), strict=True) == policy` holds for every valid policy.
7. **Typed API.** `Hsts` validates its fields, `Issue` is frozen, `HstsError` carries `code`
   and `offset`, constants `DELTA_SECONDS_MAX` and `PRELOAD_MIN_MAX_AGE` are exported.
8. **Command line.** `hstsheader` reads a value or a `curl -sI` dump and prints the policy and
   the findings as JSON; `--preload` adds the eligibility check; the exit status says whether
   the header is honoured. It fits: checking a site's header is a shell task.
9. **Contracts.** RFC examples and preload thresholds are read from the pinned files, README
   examples run, types are checked with mypy, and the installed wheel and its console script
   are driven from an empty folder.
10. **Docs and packaging.** README with executed examples and an API table, CHANGELOG,
    keywords and classifiers, sdist without planning notes or fetched files.

## Out of scope

- Host matching, storage and expiry (RFC 6797 sections 8.1.1 to 8.3): they belong to a UA.
- The legacy 18 week preload policy for bulk entries submitted before October 2017.
- Network checks that hstspreload.org also runs (redirects, certificates, subdomains).
