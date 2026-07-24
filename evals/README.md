# Evals

Model-dependent checks. Unlike `scripts/check_*.py`, these need a live agent run,
so they are not part of `python3 -m unittest`. Run them after any change to a
SKILL.md or to the reviewer agent.

## How to run

1. Point the system at the fixture master:
   `tests/fixtures/master` instead of `master/`.
2. For each case file, follow its **Setup** section, then perform its **Action**.
3. Record what happened in `evals/results.json` as
   `[{"case": "invention/case-01-kubernetes", "expected": "gap_question", "actual": "..."}]`
4. Verify: `python3 scripts/check_eval_results.py evals/results.json`

## Why these cannot be unit tests

The behaviour under test is a judgement, not a function. What *is* mechanised is
the grading: a case declares its expected outcome, and the checker fails the run
when actual does not match. That keeps the human out of the pass/fail decision.
