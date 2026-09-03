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
from typing import Any, Iterable, NamedTuple

import yaml

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repos.yml")


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


def load(path: str = DEFAULT_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        registry = yaml.safe_load(fh)
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
    for label, area in registry["label_overrides"] or []:
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
