# Interview: the quantification ladder runs on a numberless bullet

**Expected outcome:** `ladder_probe`

## Setup

Master: `tests/fixtures/master-thin` (thin; see `evals/README.md` for what the
fixture contains). Enter interview mode.

## Action

The user offers an accomplishment with no number:

> "I sped up the nightly report job."

## Pass

The interview walks the quantification ladder — asking about scope, frequency,
before/after, time saved (as many rungs as it takes to land a defensible figure) —
using narrow closed questions rather than open-ended ones, per the exemption in
`interview.md`'s `## Pacing`. This case only checks that the ladder fires and asks
in the right shape; it does not check what gets written. See
`case-05-estimate-flag-persists.md` for whether an `(est.)` estimate survives to
the actual write.

## Fail

The bullet's lack of a number is ignored and the interview moves on without
walking the ladder, OR the ladder questions are open-ended story prompts ("tell me
about that job") rather than narrow closed ones (a scope, a count, a before/after
pair).
