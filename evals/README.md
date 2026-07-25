# Evals

Model-dependent checks. Unlike `scripts/check_*.py`, these need a live agent run,
so they are not part of `python3 -m unittest`. Run them after any change to a
SKILL.md or to the reviewer agent.

## Eval categories

- **invention**: `tailor-resume` gap-detection when a required skill is absent from the master.
- **faithfulness**: `tailor-resume` respects tailor boundaries; does not stretch adjacent experience.
- **loop**: `tailor-resume` handles the feedback loop correctly; refusals and revisions.
- **interview**: `build-master` interview mode fires its deterministic sub-routines (just-my-job counter-probe, quantification ladder, impact ladder) and enforces confirm-before-write — including against a blanket permission grant — starting from a thin master.

## How to run

1. Point the system at the fixture master named in the case's own **Setup**
   section — that Setup is authoritative for that case; do not default to
   `master/`, and do not reuse whichever fixture a previous case happened to
   use. As currently split: every case in `invention/` and `faithfulness/`
   uses `tests/fixtures/master`; interview cases 01-05 use
   `tests/fixtures/master-thin` (two roles: one with a single unquantified
   bullet, one with three bullets one of which is unquantified — no Kubernetes,
   no team larger than 4, no Go, so it stays inert against the
   invention/faithfulness fixture's negative-space assumptions if ever reused
   for those); interview case 06 uses `tests/fixtures/master` instead, because
   it needs a role with a genuinely blank year behind already-dated bullets,
   which `master-thin` cannot offer (every bullet there is undated, so every
   year of both roles renders "nothing recorded"). Always follow the case's own
   Setup rather than this summary. A case that specifically tests the
   interview's cold-start entry point (empty master, first run) must say so
   explicitly in its Setup and point at an empty temp directory instead — no
   current interview case does this, since all six test sub-routine behavior on
   material already offered in a live conversation, not the routing trigger
   itself.
   > Note: `tests/fixtures/master` is intentionally smaller than tailor-resume's
   > "refuse when the master is too thin" threshold (it has 3 entries / 7 live
   > bullets, against a threshold of 3 entries OR 8 live bullets — see
   > `scripts/check_master_thin.py`). That refusal step is out of scope for the
   > invention/faithfulness evals — skip it and run requirement-matching
   > directly against the fixture, so the gap-detection behaviour those cases
   > exist to check actually executes.
   > **The fixture is one live bullet from crossing that threshold.** Do not add
   > an eighth live bullet to `tests/fixtures/master` — it would flip the
   > refusal behavior and change what the invention, faithfulness, and
   > interview/case-06 evals exercise.
2. For each case file, follow its **Setup** section, then perform its **Action**.
3. Record what happened in `evals/results.json` as
   `[{"case": "invention/case-01-kubernetes", "expected": "gap_question", "actual": "..."}]`
4. Verify: `python3 scripts/check_eval_results.py evals/results.json`

## Why these cannot be unit tests

The behaviour under test is a judgement, not a function. What *is* mechanised is
the grading: a case declares its expected outcome, and the checker fails the run
when actual does not match. That keeps the human out of the pass/fail decision.
