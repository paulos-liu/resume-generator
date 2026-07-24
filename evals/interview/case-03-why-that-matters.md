# Interview: the "why did that matter?" ladder lifts a flat fact

**Expected outcome:** `impact_probe`

## Setup

Master: `tests/fixtures/master-thin` (thin; see `evals/README.md` for what the
fixture contains). Enter interview mode.

## Action

The user states a flat, impact-free fact — not `interview.md`'s own worked
example ("migrated the database") and not a database migration at all:

> "I switched our CI pipeline from Jenkins to GitHub Actions."

## Pass

The interview climbs from the task toward its business impact ("why did that
matter?" / "what did that unblock?") until it reaches a concrete outcome (e.g.
faster builds unblocking more frequent releases, or engineer time no longer spent
babysitting Jenkins), then proposes a bullet carrying that outcome.

## Fail

The bare task is written as the accomplishment with no attempt to surface the
outcome it produced. (A pass that only works because the fact happened to be a
database migration would indicate the rule is pattern-matched to that one
example, not applied generally — that is also a fail.)
