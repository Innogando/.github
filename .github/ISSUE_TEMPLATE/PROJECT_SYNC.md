# Alignment with engineering Project (#9 — Granja de Rus)

Issue forms populate the **issue body** and set the GitHub **Issue type** (**Objective**) plus the label `objective` for filters and automation. Native **Project V2** fields are still maintained on the board (or via the `add-issue-to-project` workflows); dropdown options match the Project so values can be copied without ambiguity.

## Project fields and where data lives

| Project field | Type | Recommended source |
|---------------|------|-------------------|
| Title | Text | Issue title (edit when creating) |
| Status | Single select | Board: Backlog → Ready → In Progress → Review → Blocked → Done. **Set by workflow / board; do not duplicate in body.** |
| Priority | Single select | **Hardware project (#11) only** — removed from #9 on 2026-09-01 (zero options, zero values; ordering happens via Status + the huddle). On #11 the HW workflow defaults it to P1. |
| Area | Single select | **Set by workflow from [`registry/repos.yml`](../../registry/repos.yml)** — the repo's declared Area, overridden by an area label on the issue. |
| Size | Single select | Board: XS, S, M, L, XL (only useful for tasks, not for quarterly objectives) |
| Milestone | Milestone | Issue sidebar. Quarterly convention (see below). |
| Assignees | People | Board or issue |
| Labels | Labels | Issue: template adds `objective`; add others per repo |
| Dates, PRs, repo, reviewers, parent issue | Various | Issue / board per your workflow |

## Exact single-select options

**Status:** Backlog, Ready, In Progress, Review, Blocked, Done

Status semantics (automation-managed — [pr-review-status.yml](../workflows/pr-review-status.yml) and the closed→Done net in [project-dates.yml](../workflows/project-dates.yml)):

| Status | Meaning |
|---|---|
| In Progress | Being implemented; no PR yet (or the PR is a draft) |
| Review | The PR is open/ready — and for rumi-app, also merged to `develop` awaiting the Tuesday release train |
| Done | **Deployed / published, not merely merged.** Deploy-on-merge repos: at merge to `main` (the issue auto-closes). rumi-app: when the train ships (its `cd.yml` closes the shipped issues) |

**Priority (hardware project #11 only):** P0, P1, P2 (P0 = urgent / production impact; P1 = important; P2 = nice to have)

**Size:** XS, S, M, L, XL

**Area (software project #9):** CoWtrol, Rumi, Data, Infra, Cross / Platform.

**Area (hardware project #11):** Rumi, Rumi PRO, Corni, Taller, Hw Operations, Porci, Firmware, Rumi Dairy.

Both lists, and which repo gets which Area, live in one place: [`registry/repos.yml`](../../registry/repos.yml). Adding a repo or moving it between areas is a one-line change there.

An area label on the issue (`cowtrol`, `cross / platform`, `data`, `infra`, `rumi`, `rumi pro`) overrides the repo's declared Area. Precedence is the order they appear in `label_overrides`, and a label is ignored when it names an Area that its board does not have — `rumi pro` therefore does nothing on #9. `label-sync.yml` creates these labels in every enrolled repo; until it ran they existed only in `management`, so the override was documented but not usable.

`management` is the one repo with no default Area (`require_label: true`): an issue there without an area label is not added to the board at all.

Repo names in the registry are matched exactly. `registry-validate.yml` rejects a name the organisation does not spell that way — the check exists because the previous hardware list said `porci` while the repo is `Porci`, so every issue opened there from 2026-05-06 reached no board.


## Issue types and labels

- **Objective** — `type: Objective` in [objective.yml](objective.yml); label `objective`.
- **Support** — no template in this repo. The intake form lives in a separate app that creates issues via API with the `support` label; the workflow then sets the org Issue Type **Support** automatically.
- **Task** — default Issue Type applied by the workflow when no other label matches.
- **Censo** — applied when the label `censo` is present.

Issue types are defined at the **organization** level. The `type` string in YAML must match the org issue type name exactly (including casing). If validation fails after merge, rename the type in org settings or adjust the YAML to match.

Project rules: every item should have **Priority**, **Area**, and **Assignee** on the board; do not start work unless status is **Ready** or **In Progress**.

## Milestones (quarterly objectives)

Quarterly objectives live inside a **Milestone**. One milestone per quarter per repo that hosts objective issues.

- **Naming convention:** `YYYY Qn (Mmm-Mmm)` — e.g. `2026 Q2 (Apr-Jun)`, `2026 Q3 (Jul-Sep)`. Sortable alphabetically and human-readable.
- **Due date:** last day of the quarter, 23:59 UTC.
- **Where to create it:** in this repo (`Innogando/.github`) during the first week of the quarter. If an objective is opened in a different repo, create the same milestone there with the identical title.
- **Why Milestones and not Project V2 Iterations:** Milestones give a native progress bar on each issue, render on the issue sidebar, and can be added as a column on the Project board. Iterations are powerful but force you to work from the board to see progress.

Create a milestone with `gh`:

```bash
gh api repos/Innogando/.github/milestones \
  -f title='2026 Q2 (Apr-Jun)' \
  -f due_on='2026-06-30T23:59:59Z' \
  -f description='Quarterly objectives for Q2 2026.'
```

## Refreshing this reference

`registry-validate.yml` already compares the registry's Area lists against both boards on every change and weekly, so a rename shows up as a failed check rather than as silent mis-routing. To look by hand:

```bash
gh project field-list 9 --owner Innogando --format json
gh project field-list 11 --owner Innogando --format json
```

To see how a given issue would be routed:

```bash
python3 registry/resolve.py --repo cowtrol-api --labels '["infra"]'
```
