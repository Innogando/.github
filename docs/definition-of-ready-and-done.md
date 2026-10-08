# Definition of Ready and Definition of Done

One bar for every issue on the engineering boards, and a stricter one for issues an
agent may pick up. [`issue-writing.md`](https://github.com/Innogando/engineering-platform/blob/main/context/issue-writing.md)
explains how to write each field; this page says when an issue is ready to start and
when it is finished.

## Definition of Ready

An issue moves to **Ready** on the board only when every box is true. If one is not,
it stays in **Backlog** and the gap is written on the issue.

- [ ] **The problem is stated**, not only the solution: who has it, what they see, and
      the evidence (links, ids, numbers).
- [ ] **Acceptance criteria** (Bug, Feature) or **Done when** (Task) are binary checks
      that a reviewer can verify from the issue and the diff alone.
- [ ] **One repo, one concern.** It lives in the repo where the change goes, and its
      Area on the board is correct. Two unrelated outcomes are two issues.
- [ ] **Scope is bounded.** What it deliberately does not change is written down when
      it is not obvious (the Feature form's *Out of scope*).
- [ ] **Dependencies are known.** Blocking issues are linked as full URLs and are
      closed, or the issue says why it can start anyway.
- [ ] **No open questions.** Anything still undecided is either answered on the issue
      or split out as its own issue.
- [ ] **Context pointers** name the files, modules, dashboards or prior issues to start
      from.

The litmus test in `issue-writing.md` still applies: could someone with no Slack
context produce a plan you would approve, given only this issue?

### Additional bar for `agent-ready`

`agent-ready` tells an agent that it may take the issue. **A person always sets it**,
never an agent, after checking the Definition of Ready above plus all of these:

- [ ] **Risk is estimated** in the issue (low, medium or high) using the paths and size
      it is expected to touch.
- [ ] **Affected paths are named** in *Context pointers*.
- [ ] **It is reproducible in CI.** A failing test can be written with the repo's test
      fixtures and the throwaway CI database. It needs no access to dev, the replica
      or production.
- [ ] **It needs no secrets** beyond what CI already has.
- [ ] **It is small.** The expected diff is 300 lines or fewer.
- [ ] **It avoids sensitive paths:** migrations, authentication and permissions,
      billing and commissions, external integrations, infrastructure, CI workflows.
      An issue that must touch them is not `agent-ready` until the agent has earned
      that risk level.

If an agent finds during the work that any of these is false, it stops, comments
on the issue, and the issue goes back to triage.

## Definition of Done

An issue is **Done** when every box is true. "Merged" is not done.

- [ ] Every acceptance criterion or *Done when* check is true.
- [ ] **Tests cover the change.** A bug fix ships with a regression test that fails
      before the fix and passes after it.
- [ ] **CI is green**, including the required checks of the repo's ruleset.
- [ ] **The PR links the issue** with `Closes <full issue URL>`.
- [ ] **It was reviewed according to its risk**, by a code owner. High-risk changes are
      reviewed by two people. The AI review's comments are answered, not ignored.
- [ ] **Docs and `AGENTS.md`** are updated when behaviour, setup or conventions changed.
- [ ] **It is deployed.** The change is in production (or published, for libraries and
      docs). In deploy-on-merge repos that is the merge to `main`; in repos with release
      trains it is the release that contains the PR.

For **Support** issues and user-reported **Bugs**, closing also means telling the
person who reported it what changed, once the release is in production.

## Where these are used

- [`ISSUE_TEMPLATE/config.yml`](../.github/ISSUE_TEMPLATE/config.yml) links this page
  from the issue chooser, and the Bug, Feature and Task forms link it from their text.
- [`ISSUE_TEMPLATE/PROJECT_SYNC.md`](../.github/ISSUE_TEMPLATE/PROJECT_SYNC.md) maps
  **Ready** and **Done** on the board to these definitions.
- The `agent-ready` bar is what the Developer agent will check before it plans
  (agents project, action S1). Until then it is the checklist for whoever sets the
  label.
