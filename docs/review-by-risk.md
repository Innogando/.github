# Review by risk

> **Status: draft for decision** (Álvaro, Rus). Nothing here is enforced yet; see
> [Enforcement](#enforcement). Refs [#59](https://github.com/Innogando/.github/issues/59).

The [Definition of Done](definition-of-ready-and-done.md#definition-of-done) already
says a change is *"reviewed according to its risk, by a code owner. High-risk changes
are reviewed by two people. The AI review's comments are answered, not ignored."*
This page makes that sentence checkable. It adds no new bar: it says which risk gets
which review, and what a machine checks.

Reviewers check **evidence and risk**, not every line. The evidence is the PR's
`## Evidence` section ([PR template](../.github/PULL_REQUEST_TEMPLATE.md)); the risk is
the PR's `risk:*` label.

## The rule

| Risk | Who must approve | Who may merge | Admin bypass |
|---|---|---|---|
| `risk:low` | AI review (Temis) approves **and** `## Evidence` is filled | the author | no |
| `risk:medium` | one code owner (a person) | the author, after that approval | no |
| `risk:high` | two people, at least one a code owner | the author, after both approvals | no |

`risk:high` is anything touching the sensitive paths of the
[`agent-ready` bar](definition-of-ready-and-done.md#additional-bar-for-agent-ready):
migrations, authentication and permissions, billing and commissions, external
integrations, infrastructure, CI workflows.

For every risk level:

1. **New commits after an approval need a new review.** An approval covers the diff
   that was approved, not what was pushed after it (stale approvals are dismissed).
2. **A *Request changes* from the AI review needs a written reply** on the PR before
   merge: what was fixed, or why it does not apply. Silence is not a reply.
3. **Evidence is filled.** An empty `## Evidence` section is a warning today
   ([#58](https://github.com/Innogando/.github/issues/58)); it becomes part of
   this rule only when enforcement starts.
4. **No label, no shortcut.** A PR without a `risk:*` label is treated as `risk:high`.

## Why this shape

- Most PRs are small and low-risk; asking a person to read every line of them is what
  made people stop reading. Low risk plus evidence plus the AI review is enough.
- The costly failures were not in the lines a reviewer skims: a migration that broke
  the release still running, an endpoint never timed on production-sized data. Those
  are exactly what the Evidence section and the `risk:high` tier ask for.
- A rule that can be skipped routinely is a suggestion. The tiers only mean something
  if bypass is reserved for incidents.

## Enforcement

Enforcement **waits until the risk label is calibrated**: today the label and code
owners agree on too few PRs for it to gate merges (tracked in
`Innogando/github-workflows`, risk-label calibration). Until then this page is the
written rule and reviewers apply it by hand.

When the label is trusted, the repository rulesets change as follows (the exact
commands are prepared separately and run by an org admin after the decision):

1. **Bypass reserved for incidents.** Ruleset bypass is for break-glass merges only,
   each with a linked Incident issue.
2. **Stale approvals dismissed and last push approved** on every repo that has a
   default-branch ruleset.
3. **Code-owner review required** on every repo with a `CODEOWNERS` file.
4. **A required `Review by risk` status check** that reads the `risk:*` label, the
   approvals, the AI review's state and the Evidence section, and passes only when the
   row of the table above is met. Rulesets cannot vary the approval count by label, so
   this check is what makes the tiers real; the ruleset keeps the human approvals that
   apply to everything.
5. **Conversation resolution** is *not* turned on: a written reply is the rule, not
   resolving threads.

## Open questions for Álvaro and Rus

1. **Low risk without a human approval.** The `risk:low` row only works if the
   ruleset's code-owner approval requirement drops to zero and the `Review by risk` check carries it. Accept that, or keep one human
   approval on everything and make the tiers *additional* (medium = same, high = two)?
2. **Who counts as the second person** on `risk:high`: any org member, or a second
   code owner?
3. **Break-glass.** Keep org admins as a bypass actor for incidents (with the Incident
   issue as the paper trail), or remove bypass entirely and use a temporary ruleset
   change when production is down?
4. **Size.** The PR template asks to split or justify PRs over ~800 non-generated
   lines. Should a PR over that size be `risk:high` regardless of paths?

## Where this is used

- [PR template](../.github/PULL_REQUEST_TEMPLATE.md): the `## Evidence` section.
- [Definition of Ready and Done](definition-of-ready-and-done.md): the DoD line this
  page implements, and the sensitive paths.
