# Interview: the "just my job" flag generalizes past its own example

**Expected outcome:** `counter_probe`

## Setup

Master: `tests/fixtures/master-thin` (thin — one role has a single unquantified
bullet, the other has three bullets, one of them unquantified; see
`evals/README.md` for what the fixture contains). Enter interview mode
(`build-master` / `interview.md`).

## Action

During a role deep-dive the user waves off their own work, but not with either
phrase `interview.md` names verbatim ("that was just my job," "we did it"):

> "I mean, I untangled the on-call rotation so people stopped getting paged at
> 3am, but honestly, anyone on the team could've done it."

## Pass

The interview recognizes this as a dismissal despite the different wording and
counter-probes for the individual contribution — e.g. "plenty of people could be
on that team and not fix the rotation; what did you specifically do that someone
else in your seat wouldn't have?" — before moving on.

## Fail

The dismissal is accepted and the interview moves to the next role/section without
probing what the user actually did. (A pass that only works because the exact
phrase "that was just my job" or "we did it" appeared would indicate the rule is
matched as a literal string, not a dismissive pattern — that is also a fail.)
