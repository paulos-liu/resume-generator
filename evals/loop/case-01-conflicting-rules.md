# Loop: irreconcilable hard rules must terminate

**Expected outcome:** `surfaced_conflict`

## Setup

Master: `tests/fixtures/master`. Temporarily set `max_lines` to 3 in a copy of
`preferences/hard-rules.md` while keeping every other rule.

## Action

Run `tailor-resume` against any job description that matches three or more bullets.

## Pass

The loop stops at or before 3 iterations and surfaces the unresolved findings to
the user, naming the conflict.

## Fail

The loop runs more than 3 times, or silently ships a draft that violates a hard
rule, or drops content without saying what it dropped.
