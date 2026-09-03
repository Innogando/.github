# Repository registry

`repos.yml` is the single source of truth for two facts about every active software
and firmware repository:

1. **which board its issues go to, and which Area they get** — project #9 *Granja de
   Rus* or #11 *Granja de Hardware*
2. **whether the repo is expected to carry the `engineering-platform` conventions**

Both used to be spread across seven hand-maintained copies kept aligned by comments.

## Common changes

**A new repo.** Add one line under `repos:`, using the name exactly as GitHub spells
it. If it should stay off the boards, add it to `unlisted_ok` with a reason instead —
`registry-validate.yml` fails on a repo that is in neither, so a new repo forces a
decision rather than being forgotten.

```yaml
  my-new-service:  { project: 9, area: Infra, platform: required }
```

Then give it the caller workflow: `python3 registry/enroll.py --apply --repo my-new-service`.

**Move a repo to another area.** Change its `area`. Nothing else, anywhere.

**A new Area on a board.** Add the option in the GitHub Projects UI, then add its name
to `areas:` for that project. Never record option ids — see below.

**Take a repo off the boards.** Set `project: none`. Its existing board items stay;
only new issues stop being added.

## Checking a change

```bash
pip install pyyaml

python3 registry/test_registry.py                          # routing rules, no network
python3 registry/validate.py                               # registry vs the live org
python3 registry/resolve.py --repo cowtrol-api --labels '["infra"]'
python3 registry/sync_labels.py    --dry-run               # area labels per repo
python3 registry/platform_drift.py                         # declared vs actual adoption
python3 registry/enroll.py                                 # repos missing the caller
```

## Why it is shaped this way

**Names are matched exactly, with no case-insensitive fallback.** The list this
replaced said `porci` while the repo is `Porci`, and the shell guard used
case-sensitive `grep -qw`, so every issue opened there from 2026-05-06 was silently
dropped from both boards. `validate.py` now rejects a name the organisation does not
spell that way, and says what the canonical spelling is.

**Option ids are never stored, only Area names.** Editing a single-select field
regenerates every option id (learned 2026-09-01, recorded in `project-dates.yml`), and
the two boards reuse the same id strings for different names — `8f3c6346` is CoWtrol
on #9 and Rumi on #11. The workflow resolves ids by name on every run.

**There is no catch-all default.** A repo in neither `repos` nor `unlisted_ok` fails
the run and names this file. The old `*)` arm filed every unmapped repo under
Cross / Platform, which is how a new *Data* or *Infra* repo could look correctly
routed while being wrong, and how 102 of 126 active repos came to route nowhere in
particular.

**`confirm: true`** marks an Area seeded from board history rather than chosen by the
area owner. Remove it once someone has confirmed the value.

## Consumers

| What | Reads |
|---|---|
| `.github/workflows/add-issue-to-project.yml` | `resolve.py` — routing for every new issue |
| `.github/workflows/registry-validate.yml` | `test_registry.py`, `validate.py` |
| `.github/workflows/label-sync.yml` | `sync_labels.py` |
| `.github/workflows/platform-drift.yml` | `platform_drift.py` |
| `innobot/reports` | `sw_repo_area`, `hw_repos`, `label_area` all come from here |
| `framework-personas-v2/operativa` | the area list and label ids |

Fetch it, do not copy it. `repos.json` is generated from `repos.yml` by
`export.py` and kept in sync by CI, so a consumer needs no YAML parser:

```bash
gh api repos/Innogando/.github/contents/registry/repos.json --jq .content \
  | base64 -d | jq '.derived.sw_repo_area'
```

It carries the derivations consumers used to compute for themselves:
`derived.sw_repo_area`, `derived.hw_repo_area`, `derived.hw_repos`,
`derived.require_label` and `derived.platform_required`.

**After editing `repos.yml`, run `python3 registry/export.py`.** CI fails if you forget.
