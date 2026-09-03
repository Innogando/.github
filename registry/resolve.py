#!/usr/bin/env python3
"""Resolve one issue's board and Area from the registry, for GitHub Actions.

Reads the repo name and the issue's labels, writes the decision to $GITHUB_OUTPUT:

    skip=true|false      whether to stop here
    project=9|11         board number, when not skipping
    area=<name>          Area *name*; the workflow resolves its option id by name
    project_id=<node>    convenience, straight from the registry
    reason=<text>        one line, for the run log

Exits 1 when the repo is in neither `repos` nor `unlisted_ok`, so a repo nobody
registered fails visibly instead of being filed under a catch-all default.

    resolve.py --repo Porci --labels '["bug"]'
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registry as reg  # noqa: E402


def emit(**pairs: object) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    # GITHUB_OUTPUT is line-oriented: a newline in a value would forge extra outputs.
    lines = [f"{k}={str(v).replace(chr(10), ' ').replace(chr(13), ' ')}" for k, v in pairs.items()]
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    for line in lines:
        print(line, file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="repository name, exactly as GitHub spells it")
    ap.add_argument("--labels", default="[]", help="JSON array of the issue's label names")
    ap.add_argument("--registry", default=reg.DEFAULT_PATH)
    args = ap.parse_args()

    labels = json.loads(args.labels) or []
    if not isinstance(labels, list):
        print(f"--labels must be a JSON array, got {type(labels).__name__}", file=sys.stderr)
        return 2

    registry = reg.load(args.registry)
    decision = reg.resolve(registry, args.repo, labels)

    if decision.skip:
        emit(skip="true", reason=decision.reason)
        if decision.error:
            print(f"::error::{decision.reason}")
            return 1
        print(f"Skipping: {decision.reason}")
        return 0

    project_cfg = registry["projects"][decision.project]
    emit(
        skip="false",
        project=decision.project,
        project_id=project_cfg["id"],
        area=decision.area,
        default_priority=project_cfg.get("default_priority", ""),
        reason=decision.reason,
    )
    print(
        f"{args.repo} -> project #{decision.project} "
        f"({project_cfg['name']}), Area '{decision.area}' [{decision.reason}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
