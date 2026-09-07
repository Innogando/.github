"""Load registry/repos.yml and resolve an issue's board and Area.

The routing decision lives here, in one place, so that the reusable workflow, the
registry validator and the reporting consumers cannot drift apart. It replaced two
shell `case` statements that had to be kept in sync by hand -- and had silently
diverged: the hardware list said `porci` while the repo is `Porci`, so every issue
opened there since 2026-05-06 reached no board at all.

Repo names are matched exactly. No fuzzy or case-insensitive fallback, and no
catch-all default: an unregistered repo is an error the caller must surface, not an
issue quietly filed under Cross / Platform.
"""

from __future__ import annotations

import os
import json
from typing import Any, Iterable, NamedTuple

try:
    import yaml
except ImportError:                                  # pragma: no cover - env-dependent
    yaml = None

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(HERE, "repos.yml")
#: Generated from repos.yml by export.py and kept in sync by registry-validate.yml.
#: Read when PyYAML is missing, so `enroll.py` and friends work in a bare
#: environment instead of dying on `ModuleNotFoundError: No module named 'yaml'`.
JSON_PATH = os.path.join(HERE, "repos.json")


class Decision(NamedTuple):
    """What to do with one issue."""

    skip: bool
    reason: str
    project: int | None = None
    area: str | None = None
    #: True when `area` came from a label rather than the repo's registry default.
    from_label: bool = False
    #: True when skipping is a registry gap the caller should fail on, rather than a
    #: deliberate opt-out. Keeps "we added a repo and forgot" loud.
    error: bool = False


def _normalise(registry: dict[str, Any]) -> dict[str, Any]:
    """Make a registry read from repos.json look like one read from repos.yml.

    export.py stringifies the project keys (JSON object keys must be strings) and
    writes label_overrides as objects rather than triples, so both differ from the
    YAML shape the rest of this module expects.
    """
    for key in ("projects", "areas"):
        block = registry.get(key)
        if isinstance(block, dict):
            registry[key] = {
                (int(k) if str(k).isdigit() else k): v for k, v in block.items()
            }
    overrides = registry.get("label_overrides")
    if overrides and isinstance(overrides[0], dict):
        registry["label_overrides"] = [
            [o["label"], o["area"], o.get("colour")] for o in overrides
        ]
    return registry


def load(path: str = DEFAULT_PATH) -> dict[str, Any]:
    """The registry. Prefers repos.yml; falls back to the generated repos.json.

    The YAML is the file people edit, so it is authoritative when readable. Without
    PyYAML the generated JSON is equivalent -- registry-validate.yml fails if the
    two drift -- and reading it keeps every tool here runnable with a bare Python.
    """
    if yaml is not None and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            registry = yaml.safe_load(fh)
    else:
        if not os.path.exists(JSON_PATH):
            raise ValueError(
                f"cannot read {path}: PyYAML is not installed and there is no "
                f"generated {JSON_PATH} to fall back to. `pip install pyyaml`."
            )
        with open(JSON_PATH, encoding="utf-8") as fh:
            registry = _normalise(json.load(fh))
    if registry.get("schema") != 1:
        raise ValueError(f"{path}: unsupported schema {registry.get('schema')!r}")
    for key in ("projects", "areas", "label_overrides", "repos", "unlisted_ok"):
        if key not in registry:
            raise ValueError(f"{path}: missing top-level key {key!r}")
    return registry


def entry(registry: dict[str, Any], repo: str) -> dict[str, Any] | None:
    """The registry entry for `repo`, matched exactly. None when unregistered."""
    return (registry["repos"] or {}).get(repo)


def resolve(registry: dict[str, Any], repo: str, labels: Iterable[str] = ()) -> Decision:
    """Decide the board and Area for an issue opened in `repo` carrying `labels`."""
    cfg = entry(registry, repo)
    if cfg is None:
        if repo in set(registry.get("unlisted_ok") or ()):
            return Decision(
                skip=True, reason=f"'{repo}' is listed in unlisted_ok (deliberately off the boards)"
            )
        return Decision(
            skip=True,
            error=True,
            reason=(
                f"'{repo}' is not in registry/repos.yml. Add it under repos: with a "
                f"project and area, or to unlisted_ok if it should stay off the boards. "
                f"There is deliberately no default."
            ),
        )

    project = cfg.get("project")
    if project in (None, "none"):
        return Decision(skip=True, reason=f"'{repo}' is registered with project: none")

    project = int(project)
    valid_areas = set((registry["areas"] or {}).get(project) or ())

    # A label wins over the repo default, but only if it names an Area that exists on
    # this repo's board: `rumi pro` maps to an Area that only project 11 has.
    for label, area, *_colour in registry["label_overrides"] or []:
        if label in set(labels) and area in valid_areas:
            return Decision(False, f"label '{label}'", project, area, from_label=True)

    area = cfg.get("area")
    if area is None:
        if cfg.get("require_label"):
            return Decision(
                skip=True,
                reason=(
                    f"'{repo}' has require_label: true and the issue carries no area "
                    f"label for project {project}"
                ),
            )
        return Decision(
            skip=True,
            reason=f"'{repo}' has area: null without require_label: true",
        )

    if area not in valid_areas:
        return Decision(
            skip=True,
            reason=(
                f"'{repo}' declares area '{area}', which is not an option of "
                f"project {project}"
            ),
        )
    return Decision(False, "repo default", project, area)


def repos_for_project(registry: dict[str, Any], project: int) -> list[str]:
    return sorted(
        name
        for name, cfg in (registry["repos"] or {}).items()
        if cfg.get("project") == project
    )


def repos_requiring_platform(registry: dict[str, Any]) -> list[str]:
    return sorted(
        name
        for name, cfg in (registry["repos"] or {}).items()
        if cfg.get("platform") == "required"
    )
