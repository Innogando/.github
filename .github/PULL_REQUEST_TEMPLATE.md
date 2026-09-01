<!--
Org-level PR template. Lives at Innogando/.github/.github/PULL_REQUEST_TEMPLATE.md and applies to every repo
without its own. Title must be a Conventional Commit (`feat(scope): …`) — the `Conventional Commits` check
validates the title, and squash-merge turns it into the commit on main.
The AI code review reads "Linked issue" as the review spec; keep the headings.
-->

## What

<!-- One paragraph. What changes, as the user or operator sees it. Not a file list. -->

## Why

<!-- The problem this solves. If the linked issue says it, one line and the link is enough. -->

## Linked issue

Closes <!-- full URL, e.g. https://github.com/Innogando/rumi-api/issues/574 -->

<!-- No issue? Add the `no-issue` label AND write the reason here (chore / deps / release / hotfix). Hotfix → open an Incident issue within 24 h. -->

## How tested

<!-- Evidence, not adjectives: test names, CI run link, `EXPLAIN` before/after, screenshot, a dev-environment URL. -->

## Risk & rollback

<!-- What can break, who notices first, how we go back (revert PR / ArgoCD rollback / migration downgrade). -->

## Screenshots / recordings

<!-- UI changes only. Before / after. -->

## Checklist

- [ ] Title is a Conventional Commit and describes the behaviour, not the person who asked for it
- [ ] Acceptance criteria of the linked issue are all met, or the ones left out are listed under **What**
- [ ] Tests added or updated (bug fixes: a regression test that failed before the fix)
- [ ] Database: migration included, reversible, and `alembic check` passes — no direct DDL in production
- [ ] App: new user-visible strings go through i18n; `pubspec.yaml` version bumped only if this PR releases
- [ ] Docs / `AGENTS.md` / runbook updated if behaviour, commands or operations changed
- [ ] No secrets, customer names or phone numbers in code, fixtures or this description
