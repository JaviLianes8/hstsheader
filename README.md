# hstsheader

Parse and build the HTTP Strict-Transport-Security header, typed and zero-dependency.

## Install

```
pip install hstsheader
```

## Usage

```python
from hstsheader import build, parse

# Build a header value.
build(31536000, include_subdomains=True, preload=True)
# "max-age=31536000; includeSubDomains; preload"

# Parse one back into a typed object.
policy = parse("max-age=31536000; includeSubDomains; preload")
policy.max_age            # 31536000
policy.include_subdomains # True
policy.preload            # True
```

Directive names are matched case-insensitively, surrounding whitespace, empty
directives and unknown directives are tolerated, and a quoted `max-age` value is
accepted. A missing or non-integer `max-age` raises `HstsError`.

```python
from hstsheader import HstsError, parse

parse("includeSubDomains")  # raises HstsError: max-age is required
```

## Why

RFC 6797 defines a tiny header, yet Python has no standalone, typed, zero-dependency
codec for it. The existing options are all tied to something larger: `apifrom` buries
the logic in a framework utility, `pyramid_hsts` only writes the header, and
PyGObject's `Soup.HSTSPolicy` pulls in the libsoup and GObject stack. This library is a
single-purpose parse-and-build pair with full type hints and nothing to install
alongside it.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
