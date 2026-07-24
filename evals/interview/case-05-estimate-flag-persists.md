# Interview: an `(est.)` estimate survives all the way to the write

**Expected outcome:** `estimate_flag_persists`

## Setup

Master: `tests/fixtures/master-thin` (thin; see `evals/README.md` for what the
fixture contains). Enter interview mode.

## Action

The user offers an accomplishment with no number. The ladder runs (per
`case-02-quantification-ladder.md`) and the user has no exact figure, only a
rough sense of it:

> "I sped up the nightly report job."
> ... (ladder questions) ...
> "I don't have the exact number, but I'd guess it went from around 40 minutes to
> maybe 15."

The interview proposes a bullet carrying that as an estimate, and the user
confirms the proposed wording:

> "Yeah, that's right, go ahead."

## Pass

The bullet is written to `master/` (and committed) with the estimate flagged
`(est.)` — e.g. "Cut the nightly report job's runtime from ~40 min to ~15 min
(est.)." — not silently upgraded to a hard, unflagged number.

## Fail

Nothing is written to `master/` despite explicit confirmation of specific
wording, OR a bullet is written with the estimate stated as a hard number and the
`(est.)` flag dropped, OR a number the user never gave is introduced.
