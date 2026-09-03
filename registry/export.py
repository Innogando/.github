#!/usr/bin/env python3
"""Write repos.json from repos.yml.

repos.yml is the file people edit; repos.json is what consumers read, so that a
shell script, a Python tool with no PyYAML, or anything else can use the registry
with `gh api ... | jq` and no dependency at all.

The JSON also carries the derivations consumers used to compute themselves, and
which they used to get subtly wrong:

    sw_repo_area / hw_repo_area   repo -> Area, per board
    hw_repos                      the project #11 set
    require_label                 repos with no default Area
    platform_required             the declared platform fleet

registry-validate.yml regenerates and diffs, so the two cannot drift.

    export.py            # write registry/repos.json
    export.py --check    # exit 1 if it is out of date
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registry as reg  # noqa: E402

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repos.json")

BANNER = "GENERATED from repos.yml by registry/export.py -- do not edit"


def build(registry: dict) -> dict:
    repos = registry["repos"] or {}
    by_project = {
        p: {n: c.get("area") for n, c in repos.items() if c.get("project") == p}
        for p in (9, 11)
    }
    return {
        "_generated": BANNER,
        "schema": registry["schema"],
        "projects": {str(k): v for k, v in registry["projects"].items()},
        "areas": {str(k): v for k, v in registry["areas"].items()},
        "label_overrides": [
            {"label": lbl, "area": area, "colour": (c[0] if c else None)}
            for lbl, area, *c in registry["label_overrides"]
        ],
        "repos": repos,
        "unlisted_ok": list(registry.get("unlisted_ok") or []),
        "derived": {
            "sw_repo_area": {k: v for k, v in sorted(by_project[9].items()) if v},
            "hw_repo_area": {k: v for k, v in sorted(by_project[11].items()) if v},
            "hw_repos": sorted(by_project[11]),
            "require_label": sorted(
                n for n, c in repos.items() if c.get("require_label")
            ),
            "platform_required": reg.repos_requiring_platform(registry),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=reg.DEFAULT_PATH)
    ap.add_argument("--out", default=JSON_PATH)
    ap.add_argument("--check", action="store_true", help="do not write; fail if stale")
    args = ap.parse_args()

    wanted = json.dumps(build(reg.load(args.registry)), indent=2, sort_keys=False) + "\n"

    if args.check:
        try:
            with open(args.out, encoding="utf-8") as fh:
                current = fh.read()
        except FileNotFoundError:
            print(f"::error::{args.out} is missing; run python3 registry/export.py")
            return 1
        if current != wanted:
            print(f"::error::{args.out} is out of date; run python3 registry/export.py")
            return 1
        print(f"{args.out} is up to date")
        return 0

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(wanted)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
