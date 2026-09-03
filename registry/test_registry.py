#!/usr/bin/env python3
"""Tests for the routing resolver. Pure -- no network, no gh.

Runnable with pytest, or directly: `python3 registry/test_registry.py`.
The live-organisation checks are validate.py's job, not these.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registry as reg  # noqa: E402

REGISTRY = reg.load()


def test_repo_default_area():
    d = reg.resolve(REGISTRY, "airflow")
    assert (d.skip, d.project, d.area) == (False, 9, "Data")


def test_porci_is_matched_by_its_real_capitalised_name():
    """Regression: the old shell list said `porci`, so `Porci` reached no board."""
    d = reg.resolve(REGISTRY, "Porci")
    assert (d.skip, d.project, d.area) == (False, 11, "Porci")


def test_repo_names_are_matched_exactly():
    d = reg.resolve(REGISTRY, "porci")
    assert d.skip and d.error, "a mis-cased name must fail loudly, not fall through"


def test_unregistered_repo_is_an_error_not_a_default():
    d = reg.resolve(REGISTRY, "some-repo-created-this-morning")
    assert d.skip and d.error
    assert "registry/repos.yml" in d.reason


def test_unlisted_ok_repo_skips_quietly():
    d = reg.resolve(REGISTRY, "brazo-laser")
    assert d.skip and not d.error


def test_label_overrides_the_repo_default():
    d = reg.resolve(REGISTRY, "rumi-api", ["infra"])
    assert (d.project, d.area, d.from_label) == (9, "Infra", True)


def test_label_is_ignored_when_the_area_is_not_on_that_board():
    """`rumi pro` names an Area that only project 11 has."""
    d = reg.resolve(REGISTRY, "rumi-api", ["rumi pro"])
    assert (d.project, d.area, d.from_label) == (9, "Rumi", False)


def test_rumi_pro_label_works_on_the_hardware_board():
    """Dead before the registry: the label existed only in the one excluded repo."""
    d = reg.resolve(REGISTRY, "rumi-pro", ["rumi pro"])
    assert (d.project, d.area, d.from_label) == (11, "Rumi PRO", True)


def test_label_precedence_is_declaration_order():
    d = reg.resolve(REGISTRY, "rumi-api", ["rumi", "data", "cowtrol"])
    assert d.area == "CoWtrol", "cowtrol is first in label_overrides"


def test_require_label_repo_skips_without_a_label():
    d = reg.resolve(REGISTRY, "management")
    assert d.skip and not d.error
    assert "require_label" in d.reason


def test_require_label_repo_routes_with_a_label():
    d = reg.resolve(REGISTRY, "management", ["data"])
    assert (d.skip, d.project, d.area) == (False, 9, "Data")


def test_every_declared_area_is_declared_for_its_own_project():
    for name, cfg in REGISTRY["repos"].items():
        area, project = cfg.get("area"), cfg.get("project")
        if area is None or project not in REGISTRY["areas"]:
            continue
        assert area in REGISTRY["areas"][project], f"{name}: {area!r} not on #{project}"


def test_every_label_override_names_an_area_of_some_project():
    known = {a for areas in REGISTRY["areas"].values() for a in areas}
    for label, area in REGISTRY["label_overrides"]:
        assert area in known, f"label {label!r} maps to unknown area {area!r}"


def test_no_repo_is_both_registered_and_unlisted():
    assert not (set(REGISTRY["repos"]) & set(REGISTRY["unlisted_ok"]))


def test_every_registered_repo_resolves_or_skips_deliberately():
    for name in REGISTRY["repos"]:
        d = reg.resolve(REGISTRY, name)
        assert not d.error, f"{name}: {d.reason}"


if __name__ == "__main__":
    failures = 0
    for fname, fn in sorted(globals().items()):
        if not fname.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"ok    {fname}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {fname}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
