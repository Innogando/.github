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

{lede}

Routes this repository's new issues to its board, as declared in
[`registry/repos.yml`](https://github.com/Innogando/.github/blob/main/registry/repos.yml):
**project #{project}, Area `{area}`**.

The workflow file is identical in every registered repository -- it names no board
and no Area, it only calls the shared reusable workflow. Moving this repo to a
different board or Area is a one-line change in the registry and needs no further PR
here. Identical is also what lets `engineering-platform` distribute the file and
conformance check it.

Issues opened before this lands are unaffected; only newly opened issues are added.
"""

LEDE = {
    "missing": "Adds the caller workflow: this repo is registered but its issues "
               "currently reach no board.",
    "alias": "Repoints the caller from the `add-issue-to-hw-project.yml` "
             "compatibility alias to the unified workflow. **Routing does not "
             "change** -- the alias already forwards there -- but while any caller "
             "still uses it the alias cannot be deleted.",
    "drift": "Replaces a caller that predates the registry with the current "
             "template. **No behaviour change**: it already called the unified "
             "workflow; only the header and comments differ.",
}

TITLE = {
    "missing": "ci: route new issues to project #{project}",
    "alias": "ci: repoint the issue-routing caller off the hardware alias",
    "drift": "ci: use the current issue-routing caller template",
}


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


def caller_body(repo: str) -> str | None:
    """The repo's caller workflow as text, or None when it has none."""
    code, out, _ = run(
        "gh", "api", f"repos/{ORG}/{repo}/contents/{CALLER_PATH}", "--jq", ".content"
    )
    if code != 0 or not out.strip():
        return None
    import base64
    return base64.b64decode(out).decode("utf-8", "replace")


#: Workflow the unified caller must invoke. Anything else is a functional problem,
#: not a cosmetic one.
UNIFIED_REF = "add-issue-to-project.yml"
ALIAS_REF = "add-issue-to-hw-project.yml"


def caller_state(repo: str, template: str) -> str:
    """One of "missing", "alias", "drift" or "current".

    The first wave could see only "missing", because `has_caller` merely asked
    whether the file existed. Two other states matter:

    "alias"  still calls add-issue-to-hw-project.yml. Routing is already correct --
             the alias forwards to the unified workflow, which reads the registry --
             but it blocks deleting the alias.
    "drift"  calls the right workflow with different text (an older header, no
             comments). Harmless today, but a file that is not identical everywhere
             is one engineering-platform cannot distribute and conformance cannot
             check, which was the point of unifying it.
    """
    body = caller_body(repo)
    if body is None:
        return "missing"
    if body.strip() == template.strip():
        return "current"
    return "alias" if ALIAS_REF in body else "drift"


def has_open_pr(repo: str) -> bool:
    """True when the enrollment PR is already open, so a re-run is idempotent."""
    code, out, _ = run(
        "gh", "pr", "list", "-R", f"{ORG}/{repo}", "--head", BRANCH,
        "--state", "open", "--json", "number", "--jq", "length",
    )
    return code == 0 and out.strip() not in ("", "0")


def default_branch(repo: str) -> str | None:
    code, out, _ = run("gh", "api", f"repos/{ORG}/{repo}", "--jq", ".default_branch")
    return out.strip() if code == 0 and out.strip() else None


def enroll(repo: str, project: int, area: str | None, template: str,
           issue: str | None = None, state: str = "missing") -> str | None:
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
             TITLE[state].format(project=project)),
            # --force-with-lease: a half-finished earlier wave may have left the
            # branch pushed but unmerged, and its content is this same file.
            ("git", "push", "--force-with-lease", "-u", "origin", BRANCH),
        ):
            code, _, err = run(*args, cwd=tmp)
            if code != 0:
                return f"{args[1]} failed: {err}"

        base = default_branch(repo)
        if base is None:
            return "cannot resolve the default branch"
        # --head and --base explicitly: `gh pr create` infers them from the local
        # branch's tracking state, which a throwaway clone does not reliably have,
        # and not every repo's default branch is `main` (rumi-pro-api uses master).
        code, out, err = run(
            "gh", "pr", "create", "-R", f"{ORG}/{repo}",
            "--base", base, "--head", BRANCH,
            "--title", TITLE[state].format(project=project),
            "--body", PR_BODY.format(
                tracking=tracking_line(repo, issue),
                lede=LEDE[state],
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
    ap.add_argument(
        "--repoint", action="store_true",
        help="only repos whose caller exists but is an alias or has drifted",
    )
    ap.add_argument(
        "--all", action="store_true",
        help="both missing and stale callers in one wave",
    )
    args = ap.parse_args()

    registry = reg.load(args.registry)
    with open(TEMPLATE, encoding="utf-8") as fh:
        template = fh.read()

    pending = []
    stale: list[str] = []
    for name, cfg in sorted(registry["repos"].items()):
        if cfg.get("project") not in (9, 11):
            continue
        if args.repo and name not in args.repo:
            continue
        if has_open_pr(name):
            continue
        state = caller_state(name, template)
        if state == "current":
            continue
        wanted = {"missing"} if not (args.repoint or args.all) else \
                 {"alias", "drift"} if args.repoint else {"missing", "alias", "drift"}
        if state not in wanted:
            stale.append(f"{name} ({state})")
            continue
        pending.append((name, cfg["project"], cfg.get("area"), state))

    if not pending:
        print("Every registered repo has the current caller workflow.")
        if stale:
            print(f"{len(stale)} differ from the template:")
            for entry in stale:
                print(f"  {entry}")
            print("Re-run with --repoint to update them.")
        return 0

    for name, project, area, state in pending:
        verb = "enroll" if state == "missing" else "repoint"
        if not args.apply:
            print(f"would {verb} {name:<28} -> #{project} / {area}")
            continue
        print(f"{verb}ing {name} -> #{project} / {area} ... ", end="", flush=True)
        err = enroll(name, project, area, template, args.issue, state)
        print(err or "done")

    if not args.apply:
        print(f"\n{len(pending)} repo(s) pending. Re-run with --apply to open the PRs.")
    if stale:
        print(f"{len(stale)} more differ from the template (--repoint): "
              f"{', '.join(stale)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
