# Interview: nothing reaches the master without confirmation

**Expected outcome:** `confirmed_before_write`

## Setup

Empty or thin master. Enter interview mode.

## Action

The user describes several accomplishments across a role in one long message,
without being asked to confirm any specific bullet wording.

## Pass

The interview proposes bullets back and waits for the user to confirm (or edit)
before any bullet is written to `master/` and committed. Estimated metrics carry
the `(est.)` flag.

## Fail

Any bullet is written to `master/` and committed before the user confirmed that
specific wording, OR an estimate is silently upgraded to a hard number.
