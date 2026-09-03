#!/usr/bin/env python3
"""Create the area-override labels in every registered repo.

The registry lets an issue label override its repo's default Area. That mechanism
was dead before this script existed: the labels were only ever created in
`management`, so `PROJECT_SYNC.md` documented an override that no other repo could
use, and the `rumi pro` label -- advertised as working in any repo -- existed only
in the one repo excluded from the hardware board.

Each repo gets only the labels naming an Area its own board actually has, so a
`rumi pro` label never appears on a software repo.

    sync_labels.py --dry-run          # print what would change
    sync_labels.py                    # apply
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registry as reg  # noqa: E402

ORG = "Innogando"


def existing_labels(repo: str) -> dict[str, str]:
    proc = subprocess.run(
        ["gh", "label", "list", "-R", f"{ORG}/{repo}", "--limit", "300",
         "--json", "name,color", "--jq", ".[] | .name + \"\\t\" + .color"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{repo}: {proc.stderr.strip()}")
    out = {}
    for line in proc.stdout.splitlines():
        name, _, colour = line.partition("\t")
        out[name] = colour.lower()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=reg.DEFAULT_PATH)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", action="append", help="limit to these repos (repeatable)")
    args = ap.parse_args()

    registry = reg.load(args.registry)
    overrides = [
        (label, area, (colour[0] if colour else "ededed"))
        for label, area, *colour in registry["label_overrides"]
    ]

    targets = sorted(
        name for name, cfg in registry["repos"].items()
        if cfg.get("project") in (9, 11) and (not args.repo or name in args.repo)
    )

    created = updated = 0
    failures: list[str] = []
    for repo in targets:
        project = registry["repos"][repo]["project"]
        board_areas = set(registry["areas"][project] or ())
        wanted = {
            label: colour for label, area, colour in overrides if area in board_areas
        }
        try:
            have = existing_labels(repo)
        except RuntimeError as exc:
            failures.append(str(exc))
            continue

        for label, colour in sorted(wanted.items()):
            if label in have and have[label] == colour.lower():
                continue
            verb = "update" if label in have else "create"
            print(f"{'would ' if args.dry_run else ''}{verb} {repo}: {label} #{colour}")
            if args.dry_run:
                continue
            # --force both creates and recolours, so one call covers either case.
            proc = subprocess.run(
                ["gh", "label", "create", label, "-R", f"{ORG}/{repo}",
                 "--color", colour, "--force"],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                failures.append(f"{repo}/{label}: {proc.stderr.strip()}")
            elif verb == "create":
                created += 1
            else:
                updated += 1

    print()
    print(f"{len(targets)} repos | created {created} | recoloured {updated} | failed {len(failures)}")
    for f in failures:
        print(f"::error::{f}" if os.environ.get("GITHUB_ACTIONS") else f"ERROR {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
