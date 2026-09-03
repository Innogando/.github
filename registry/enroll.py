#!/usr/bin/env python3
"""Open a PR in each registered repo that is missing the caller workflow.

Every enrolled repo carries the same auto-add-to-project.yml -- see
registry/templates/. It used to differ per repo, because the caller chose which of
the two reusable workflows to invoke, which made it a third copy of the repo-to-board
mapping. Now the file is identical everywhere and the routing lives in the registry.

Defaults to a dry run. Applying opens one small PR per repo, so review the dry run
first.

    enroll.py                     # list what is missing
    enroll.py --apply             # open the PRs
    enroll.py --apply --repo grafana --repo asterisk
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registry as reg  # noqa: E402

ORG = "Innogando"
CALLER_PATH = ".github/workflows/auto-add-to-project.yml"
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates",
                        "auto-add-to-project.yml")
BRANCH = "ci/auto-add-to-project"

TRACKING_REPO = f"{ORG}/.github"

PR_BODY = """\
{tracking}

Routes this repository's new issues to its board, as declared in
[`registry/repos.yml`](https://github.com/Innogando/.github/blob/main/registry/repos.yml):
**project #{project}, Area `{area}`**.

The workflow file is identical in every enrolled repository -- it names no board and
no Area, it only calls the shared reusable workflow. Moving this repo to a different
board or Area is a one-line change in the registry and needs no further PR here.

Issues opened before this lands are unaffected; only newly opened issues are added.
"""


def tracking_line(repo: str, issue: str | None) -> str:
    """How this PR points at the issue that explains the wave.

    Only `Innogando/.github` gates on a same-repo linked issue, and that is where
    the tracking issue lives, so it gets `Closes`. Everywhere else a cross-repo
    reference is the honest form: one issue explains twenty identical PRs, and
    twenty near-identical issues would be noise on the boards this very change is
    meant to make readable.
    """
    if not issue:
        return ""
    if repo == TRACKING_REPO.split("/", 1)[1]:
        return f"Closes #{issue}."
    return f"Part of {TRACKING_REPO}#{issue}."


def run(*args: str, cwd: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def has_caller(repo: str) -> bool:
    code, _, _ = run("gh", "api", f"repos/{ORG}/{repo}/contents/{CALLER_PATH}")
    return code == 0


def enroll(repo: str, project: int, area: str | None, template: str,
           issue: str | None = None) -> str | None:
    """Open the PR. Returns an error message, or None on success."""
    with tempfile.TemporaryDirectory() as tmp:
        code, _, err = run("gh", "repo", "clone", f"{ORG}/{repo}", tmp, "--", "--depth", "1")
        if code != 0:
            return f"clone failed: {err}"
        code, _, err = run("git", "checkout", "-b", BRANCH, cwd=tmp)
        if code != 0:
            return f"branch failed: {err}"
        dest = os.path.join(tmp, CALLER_PATH)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(template)
        for args in (
            ("git", "add", CALLER_PATH),
            ("git", "-c", "commit.gpgsign=false", "commit", "--no-gpg-sign", "-m",
             f"ci: route new issues to project #{project}"),
            ("git", "push", "-u", "origin", BRANCH),
        ):
            code, _, err = run(*args, cwd=tmp)
            if code != 0:
                return f"{args[1]} failed: {err}"
        code, out, err = run(
            "gh", "pr", "create", "-R", f"{ORG}/{repo}",
            "--title", f"ci: route new issues to project #{project}",
            "--body", PR_BODY.format(
                tracking=tracking_line(repo, issue),
                project=project,
                area=area or "from the issue's area label",
            ),
            cwd=tmp,
        )
        if code != 0:
            return f"pr create failed: {err}"
        return None if not out else f"opened {out}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=reg.DEFAULT_PATH)
    ap.add_argument("--apply", action="store_true", help="actually open the PRs")
    ap.add_argument("--repo", action="append", help="limit to these repos (repeatable)")
    ap.add_argument(
        "--issue",
        help=f"number of the tracking issue in {ORG}/.github that the PRs reference",
    )
    args = ap.parse_args()

    registry = reg.load(args.registry)
    with open(TEMPLATE, encoding="utf-8") as fh:
        template = fh.read()

    pending = []
    for name, cfg in sorted(registry["repos"].items()):
        if cfg.get("project") not in (9, 11):
            continue
        if args.repo and name not in args.repo:
            continue
        if has_caller(name):
            continue
        pending.append((name, cfg["project"], cfg.get("area")))

    if not pending:
        print("Every registered repo already has the caller workflow.")
        return 0

    for name, project, area in pending:
        if not args.apply:
            print(f"would enroll {name:<28} -> #{project} / {area}")
            continue
        print(f"enrolling {name} -> #{project} / {area} ... ", end="", flush=True)
        err = enroll(name, project, area, template, args.issue)
        print(err or "done")

    if not args.apply:
        print(f"\n{len(pending)} repo(s) pending. Re-run with --apply to open the PRs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
