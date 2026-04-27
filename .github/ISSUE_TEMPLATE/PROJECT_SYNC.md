# Alignment with engineering Project (#9 — Granja de Rus)

Issue forms populate the **issue body** and set the GitHub **Issue type** (**Objective** or **Support**). They also apply **labels** (`objective` / `support`) for filters and automation. Native **Project V2** fields are still maintained on the board (or via future automation); dropdown options match the Project so values can be copied without ambiguity.

## Project fields and where data lives

| Project field | Type | Recommended source |
|---------------|------|-------------------|
| Title | Text | Issue title (edit when creating) |
| Status | Single select | Board: Backlog → Ready → In Progress → Blocked → Done |
| Priority | Single select | Board: P0, P1, P2 (form suggests a value in the body) |
| Size | Single select | Board: XS, S, M, L, XL (Objective template) |
| Area | Single select | Board; same text as the template dropdown |
| Assignees | People | Board or issue |
| Labels | Labels | Issue: template adds `objective` or `support`; add others per repo |
| Milestone, dates, PRs, repo, reviewers, parent issue | Various | Issue / board per your workflow |

## Exact single-select options

**Status:** Backlog, Ready, In Progress, Blocked, Done  

**Priority:** P0, P1, P2 (P0 = urgent / production impact; P1 = important; P2 = nice to have)  

**Size:** XS, S, M, L, XL  

**Area:** CoWtrol, Rumi, Data, Infra, Cross / Platform, Hardware  

## Issue types and labels

- **Objective** — `type: Objective` in [objective.yml](objective.yml); label `objective`.
- **Support** — `type: Support` in [support.yml](support.yml); label `support`.

Issue types are defined at the **organization** level. The `type` string in YAML must match the org issue type name exactly (including casing). If validation fails after merge, rename the type in org settings or adjust the YAML to match.

Project rules: every item should have **Priority**, **Area**, and **Assignee** on the board; do not start work unless status is **Ready** or **In Progress**.

## Refreshing this reference

Dump fields from the CLI:

```bash
gh project field-list 9 --owner Innogando --format json
```
