# Alignment with engineering Project (#9 — Granja de Rus)

Issue forms populate the **issue body** and set the GitHub **Issue type** (**Objective**) plus the label `objective` for filters and automation. Native **Project V2** fields are still maintained on the board (or via the `add-issue-to-project` workflows); dropdown options match the Project so values can be copied without ambiguity.

## Project fields and where data lives

| Project field | Type | Recommended source |
|---------------|------|-------------------|
| Title | Text | Issue title (edit when creating) |
| Status | Single select | Board: Backlog → Ready → In Progress → Review → Blocked → Done. **Set by workflow / board; do not duplicate in body.** |
| Priority | Single select | **Hardware project (#11) only** — removed from #9 on 2026-09-01 (zero options, zero values; ordering happens via Status + the huddle). On #11 the HW workflow defaults it to P1. |
| Area | Single select | Board. **Set by workflow:** area labels override repo mapping — see [add-issue-to-project.yml](../workflows/add-issue-to-project.yml). |
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

**Area (software project #9):** CoWtrol, Rumi, Data, Infra, Cross / Platform. Optional GitHub labels (_exact name_) override the repo default: `cowtrol`, `cross / platform`, `data`, `infra`, `rumi`. If several are present, precedence is that order. Then repo-based defaults (e.g. `airflow` → Data, …) — see [add-issue-to-project.yml](../workflows/add-issue-to-project.yml).

**Area (hardware project #11):** Rumi, Rumi PRO, Rumi Dairy, Corni, Firmware, Taller, Porci — repo mappings are applied by [add-issue-to-hw-project.yml](../workflows/add-issue-to-hw-project.yml).

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

Dump fields from the CLI:

```bash
gh project field-list 9 --owner Innogando --format json
```
