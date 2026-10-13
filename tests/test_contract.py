from __future__ import annotations

import importlib.resources

import hstsheader

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "DELTA_SECONDS_MAX",
    "PRELOAD_MIN_MAX_AGE",
    "Hsts",
    "HstsError",
    "Issue",
    "build",
    "is_preloadable",
    "lint",
    "parse",
    "preload_issues",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(hstsheader.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in hstsheader.__all__:
        assert hasattr(hstsheader, name)


def test_version_is_a_three_part_string() -> None:
    parts = hstsheader.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("hstsheader").joinpath("py.typed").is_file()


def test_every_public_function_and_class_has_a_docstring() -> None:
    for name in hstsheader.__all__:
        obj = getattr(hstsheader, name)
        if callable(obj):
            assert obj.__doc__, name


def test_the_constants_hold_the_values_the_sources_name() -> None:
    assert hstsheader.DELTA_SECONDS_MAX == 2**31
    assert hstsheader.PRELOAD_MIN_MAX_AGE == 365 * 86400
