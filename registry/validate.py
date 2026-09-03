#!/usr/bin/env python3
"""Check registry/repos.yml against the live organisation.

The registry is only worth having if it cannot quietly disagree with reality, so
every way it has actually gone wrong is a check here:

  1. schema    every entry has the fields the resolver needs, and nothing else
  2. names     every key is a live, non-archived repo spelled exactly that way
               -- the check that would have caught `Porci` vs `porci`
  3. areas     every `area` is a current option of that board's Area field
               -- option ids are never stored, but names still get renamed
  4. coverage  every recently active repo is in `repos` or `unlisted_ok`, so a new
               repo forces a decision instead of being forgotten
  5. callers   every repo carrying auto-add-to-project.yml has a matching entry

Needs `gh` authenticated with access to the org and to both project boards.

    validate.py [--registry PATH] [--active-days 60] [--format text|github]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registry as reg  # noqa: E402

ORG = "Innogando"
CALLER_PATH = ".github/workflows/auto-add-to-project.yml"
ENTRY_KEYS = {
    "project", "area", "platform", "require_label", "product", "confirm", "notes",
}
REQUIRED_KEYS = {"project", "area", "platform"}


class Report:
    def __init__(self, fmt: str) -> None:
        self.fmt = fmt
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)
        print(f"::error::{msg}" if self.fmt == "github" else f"ERROR   {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"::warning::{msg}" if self.fmt == "github" else f"WARN    {msg}")

    def ok(self, msg: str) -> None:
        print(f"ok      {msg}")


def gh_json(*args: str) -> object:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout or "null")


def org_repos() -> dict[str, dict]:
    rows = gh_json(
        "repo", "list", ORG, "--limit", "500",
        "--json", "name,isArchived,pushedAt,updatedAt",
    )
    return {r["name"]: r for r in rows}


def area_options(project: int) -> set[str]:
    query = """
      query($org: String!, $number: Int!) {
        organization(login: $org) {
          projectV2(number: $number) {
            field(name: "Area") {
              ... on ProjectV2SingleSelectField { options { name } }
            }
          }
        }
      }
    """
    data = gh_json(
        "api", "graphql", "-f", f"query={query}",
        "-F", f"org={ORG}", "-F", f"number={project}",
    )
    field = data["data"]["organization"]["projectV2"]["field"]
    return {o["name"] for o in (field or {}).get("options", [])}


def issues_since(repo: str, since: str) -> int:
    try:
        rows = gh_json(
            "api", "-X", "GET", f"repos/{ORG}/{repo}/issues",
            "-f", "state=all", "-f", f"since={since}", "-f", "per_page=100",
        )
    except RuntimeError:
        return 0
    return len(rows or [])


def caller_body(repo: str) -> str | None:
    proc = subprocess.run(
        ["gh", "api", f"repos/{ORG}/{repo}/contents/{CALLER_PATH}", "--jq", ".content"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    import base64
    return base64.b64decode(proc.stdout).decode("utf-8", "replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=reg.DEFAULT_PATH)
    ap.add_argument("--active-days", type=int, default=60)
    ap.add_argument("--format", choices=("text", "github"), default="text")
    ap.add_argument(
        "--skip-callers", action="store_true",
        help="skip check 5, which costs one API call per org repo",
    )
    args = ap.parse_args()
    rep = Report(args.format)

    # ---- 1. schema ---------------------------------------------------------
    try:
        registry = reg.load(args.registry)
    except (OSError, ValueError) as exc:
        rep.error(str(exc))
        return 1
    repos = registry["repos"] or {}
    unlisted = set(registry.get("unlisted_ok") or ())

    for name, cfg in repos.items():
        if not isinstance(cfg, dict):
            rep.error(f"{name}: entry must be a mapping, got {type(cfg).__name__}")
            continue
        for missing in sorted(REQUIRED_KEYS - set(cfg)):
            rep.error(f"{name}: missing required key '{missing}'")
        for unknown in sorted(set(cfg) - ENTRY_KEYS):
            rep.error(f"{name}: unknown key '{unknown}'")
        if cfg.get("platform") not in ("required", "exempt"):
            rep.error(f"{name}: platform must be 'required' or 'exempt', got {cfg.get('platform')!r}")
        if cfg.get("project") not in (9, 11, "none", None):
            rep.error(f"{name}: project must be 9, 11 or none, got {cfg.get('project')!r}")
        if cfg.get("area") is None and cfg.get("project") in (9, 11) and not cfg.get("require_label"):
            rep.error(f"{name}: area is null but require_label is not true")
    overlap = sorted(set(repos) & unlisted)
    if overlap:
        rep.error(f"listed in both repos and unlisted_ok: {', '.join(overlap)}")
    if not rep.errors:
        rep.ok(f"schema: {len(repos)} entries, {len(unlisted)} unlisted_ok")

    # ---- 2. names ----------------------------------------------------------
    live = org_repos()
    lowered = {n.lower(): n for n in live}
    for name in sorted(set(repos) | unlisted):
        if name in live:
            if live[name]["isArchived"]:
                rep.error(f"{name}: repo is archived; remove it from the registry")
            continue
        canonical = lowered.get(name.lower())
        if canonical:
            rep.error(
                f"{name}: no such repo -- the canonical name is '{canonical}'. "
                f"Names are matched exactly; this is the Porci class of bug."
            )
        else:
            rep.error(f"{name}: no repo by that name in {ORG}")
    rep.ok(f"names: checked {len(repos) + len(unlisted)} against {len(live)} org repos")

    # ---- 3. areas ----------------------------------------------------------
    for project in sorted(p for p in registry["areas"] if isinstance(p, int)):
        declared = set(registry["areas"][project] or ())
        try:
            live_areas = area_options(project)
        except (RuntimeError, KeyError, TypeError) as exc:
            rep.warn(f"project #{project}: could not read the Area field ({exc})")
            continue
        for gone in sorted(declared - live_areas):
            rep.error(f"project #{project}: area '{gone}' is declared but no longer an option")
        for extra in sorted(live_areas - declared):
            rep.warn(f"project #{project}: option '{extra}' exists on the board but not in the registry")
        rep.ok(f"areas: project #{project} has {len(live_areas)} options, {len(declared)} declared")

    for name, cfg in sorted(repos.items()):
        project, area = cfg.get("project"), cfg.get("area")
        if area is None or project not in registry["areas"]:
            continue
        if area not in set(registry["areas"][project] or ()):
            rep.error(f"{name}: area '{area}' is not an area of project #{project}")

    # ---- 4. coverage -------------------------------------------------------
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.active_days)
    since = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    unaccounted = []
    for name, row in sorted(live.items()):
        if row["isArchived"] or name in repos or name in unlisted:
            continue
        pushed = row.get("pushedAt") or ""
        active = pushed > since or issues_since(name, since) > 0
        if active:
            unaccounted.append(name)
    for name in unaccounted:
        rep.error(
            f"{name}: active in the last {args.active_days} days but in neither repos "
            f"nor unlisted_ok -- decide which and add it"
        )
    if not unaccounted:
        rep.ok(f"coverage: every repo active in the last {args.active_days} days is accounted for")

    # ---- 5. callers --------------------------------------------------------
    if not args.skip_callers:
        for name, row in sorted(live.items()):
            if row["isArchived"]:
                continue
            body = caller_body(name)
            if body is None:
                if name in repos and repos[name].get("project") in (9, 11):
                    rep.warn(f"{name}: registered for project #{repos[name]['project']} but has no {CALLER_PATH}")
                continue
            cfg = repos.get(name)
            if cfg is None:
                rep.error(f"{name}: has {CALLER_PATH} but no registry entry")
                continue
            if cfg.get("project") in (None, "none"):
                rep.error(f"{name}: has {CALLER_PATH} but is registered with project: none")
            elif "add-issue-to-hw-project" in body and cfg["project"] != 11:
                rep.error(
                    f"{name}: its caller invokes the hardware workflow but the registry "
                    f"says project #{cfg['project']}"
                )
        rep.ok(f"callers: checked {CALLER_PATH} across the org")

    print()
    print(f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
