"""Headers served by real sites, and what the hstspreload.org checker says about them.

Each value is the Strict-Transport-Security field that `curl -sI https://<host>/` printed
on 2026-10-21. The last column is the verdict of the hstspreload.org header checker (built
from chromium/hstspreload commit d624d7c, see tests/oracle) on that value, run the same day:
True when it found no error. Sites change their headers; these are a dated snapshot.
"""

from __future__ import annotations

import pytest

from hstsheader import is_preloadable, lint, parse

OBSERVED = [
    ("docs.python.org", "max-age=315360000; includeSubDomains; preload", True),
    ("github.com", "max-age=31536000; includeSubdomains; preload", True),
    ("go.dev", "max-age=31536000; includeSubDomains; preload", True),
    ("hstspreload.org", "max-age=31536000; includeSubDomains; preload", True),
    ("pypi.org", "max-age=31536000; includeSubDomains; preload", True),
    ("stackoverflow.com", "max-age=31536000; includeSubDomains", False),
    ("twitter.com", "max-age=631138519; includeSubdomains", False),
    ("www.amazon.com", "max-age=47474747; includeSubDomains; preload", True),
    ("www.apple.com", "max-age=31536000; includeSubdomains; preload", True),
    ("www.bbc.co.uk", "max-age=31536000; preload", False),
    ("www.cloudflare.com", "max-age=31536000; includeSubDomains", False),
    ("www.dropbox.com", "max-age=31536000; includeSubDomains", False),
    ("www.facebook.com", "max-age=15552000; preload", False),
    ("www.gov.uk", "max-age=31536000; preload", False),
    ("www.linkedin.com", "max-age=15552000; includeSubDomains", False),
    ("www.mozilla.org", "max-age=31536000", False),
    ("www.netflix.com", "max-age=31536000; includeSubDomains", False),
    ("www.paypal.com", "max-age=63072000; includeSubDomains; preload", True),
    ("www.python.org", "max-age=63072000; includeSubDomains; preload", True),
    ("www.reddit.com", "max-age=31536000; includeSubdomains", False),
    ("www.wikipedia.org", "max-age=106384710; includeSubDomains; preload", True),
    ("www.youtube.com", "max-age=31536000", False),
]


@pytest.mark.parametrize(("host", "value", "site_accepts"), OBSERVED)
def test_real_headers_read_cleanly_and_match_the_site_checker(
    host: str, value: str, site_accepts: bool
) -> None:
    assert [i.code for i in lint(value) if i.severity == "error"] == [], host
    policy = parse(value, strict=True)
    assert policy == parse(value)
    assert policy.max_age == int(value.split(";")[0].split("=")[1])
    assert policy.include_subdomains == ("includesubdomains" in value.lower())
    assert policy.preload == value.endswith("preload")
    assert is_preloadable(value) is site_accepts, host
