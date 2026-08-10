---
name: batch-tailor
description: Tailor resumes for several jobs at once, batching every question to the user so each is asked only once. Use when the user has more than one job to tailor for, or asks to tailor a batch, or imports several postings from career-ops. Never adds facts.
---

# Batch tailor

Runs `tailor-resume` across several applications concurrently and collapses
their questions into one conversation. Adds no facts and relaxes no check —
batching changes who asks the questions, never what is enforced.

## Invariants

**Subagents never write to `master/`.** `build-master` is its only writer, and
bullet IDs are append-only: two subagents allocating `nw.b13` at once corrupts
the ID space silently, and every `sources.json` citing it afterward is
ambiguous. You collect answers; you run `build-master` yourself, serially,
between rounds.

**One subagent owns exactly one `library/<slug>/`.** No two agents write the
same file, which is why nothing here needs a lock. A subagent that strays
outside its directory is a bug.

**No subagent talks to the user, and no subagent enforces a bound that spans
more than its own call.** Every decision or report that needs a human — gap
questions, a `redacted_term` finding, what got dropped for budget, a hard-rule
conflict that does not converge — surfaces at a barrier or in the step 9
report this skill controls, never inside a subagent mid-step. Every cap or
count that must hold across more than one dispatch — the per-slug review cap,
`next_round`'s round limit — is tracked by the controller, not by a subagent's
own memory of prior calls. This is why phase B stops at `tailor-resume` step 7
instead of running step 8 or step 9 itself, and why dispatching
`resume-reviewer`, grouping its findings, and bounding the per-slug re-review
loop all live in the barriers below rather than in a subagent's own step
execution.

**Drift checklist. Run this whenever you touch this skill's handling of any
`tailor-resume` step — delegating a new range, changing one already
delegated, or changing how a step is re-implemented or skipped:**

- [ ] For every `tailor-resume` step range this skill **delegates** to a
      subagent: re-read that range's actual text — not this skill's
      paraphrase of it — and grep it for the word "user" (needs a barrier or
      a line in step 9) and for any cap, count, or "stop after N" rule (needs
      controller-side tracking).
- [ ] For every `tailor-resume` step this skill **re-implements itself**
      instead of delegating — e.g. step 7's per-slug review-loop cap, which
      re-implements step 8's "cap at 3 iterations" as a controller barrier
      rather than delegating step 8 verbatim — apply the same grep to the
      step being re-implemented, not to this skill's own restatement of it.
- [ ] For every `tailor-resume` step this skill neither delegates nor
      re-implements: confirm the omission is intentional and recorded in this
      file (see step 10, below), not silently missing coverage.

Three separate reviews of this file each found one instance of the delegated-
range miss (first bullet). The per-slug review cap (second bullet) was a
fourth instance the first bullet's grep alone cannot catch, because step 7
does not delegate step 8 — it re-implements it.

**Recorded decision: `tailor-resume` step 10 (the advisory
`recruiter-impressions` read) has no counterpart here, deliberately.**
Applying the checklist above flags it — this skill neither delegates nor
re-implements step 10 — but that is a known scope boundary, not a bug:
batch-tailor's phase C already runs `resume-reviewer` per draft (this skill's
counterpart to step 8) and stops at step 9's report and hand-off to
`render-resume`. A user who wants the advisory recruiter read gets it from
`tailor-resume` itself, one slug at a time, after render; batch-tailor does
not fan that step out across a batch. Leave this note in place rather than
letting a future editor rediscover the gap and treat it as an oversight.

## 1. Assemble the batch

Take the library slugs the user names. If they ask for jobs from career-ops,
import each first:

    python3 scripts/import_job.py <report-number>

Each slug must already have `job.md`. Confirm the list with the user before
spending anything.

**Run the thin-master gate once, before dispatching anything:**

    python3 scripts/check_master_thin.py --master master

This is `tailor-resume` step 0, which that skill calls the highest
invention-pressure state in the whole system. It is numbered outside the
1–3 range phase A below delegates to each subagent, so nothing runs it unless
this step does. If it reports a `thin_master` finding, stop the batch here and
route the user to `build-master` — do not dispatch a single subagent. Six
agents drafting concurrently against a master too thin to draft from honestly
is the same failure six times over, not six independent judgment calls.

## 2. Round 1, phase A — requirements only

Dispatch one subagent per slug, all in a single message so they run
concurrently. Each performs **steps 1–3 of `tailor-resume` only**: extract
requirements, match them to master bullet IDs, write `requirements.md`. Each
returns its no-match list.

Instruct each agent explicitly: do not draft, do not write outside
`library/<slug>/`, do not touch `master/`.

## 3. Barrier — batch the gap questions

**Check `master/known-gaps.md` first and drop anything already recorded
there**, the same as `tailor-resume` step 9. A "no" recorded in a past session
must not be asked again just because it resurfaced through a different job in
this batch — asking someone twice is how a system teaches people to stop
reading its questions. `resumelib.batch.group_gaps` has no filter for this
yet; this paragraph is a stopgap until that filtering becomes deterministic
and moves in beside `group_gaps` itself.

Collapse what's left:

```python
from resumelib.batch import Gap, group_gaps
questions = group_gaps([Gap(slug, req) for slug, req in gaps])
```

Ask the user the grouped questions in one pass, naming which jobs each affects.
Six postings wanting Kubernetes is one question.

Route every answer through `build-master`, serially. A declined question is
recorded as a non-answer so the next batch does not ask it again — without
that, batching makes repeat-asking worse rather than better.

## 4. Round 1, phase B — draft

Resume each subagent with `SendMessage` rather than spawning a fresh one: it
already read the JD and matched the requirements, and should not pay to do that
twice. Each now completes **steps 4–7 of `tailor-resume` only** — select and
rephrase, emit the draft and its sources, check the budget, self-check —
producing `draft.md` and `sources.json`, and runs its own checks unchanged:

    python3 scripts/check_provenance.py library/<slug> --master master
    python3 scripts/check_hard_rules.py library/<slug>/draft.md
    python3 scripts/check_redactions.py library/<slug> --master master
    python3 scripts/keyword_coverage.py library/<slug>

**Not step 8 and not step 9.** Instruct each subagent explicitly to stop after
step 7. Step 8 is the review loop — phase C, below, dispatches
`resume-reviewer` itself, once per draft, so a subagent must not also spawn
its own reviewer. Step 9 is the gap loop, whose own instruction is to route
every answer through `build-master`; letting each subagent run it would mean N
subagents concurrently invoking `build-master`, which is precisely the
append-only-ID corruption the invariants block above exists to prevent. Both
happen in the barriers this skill controls, never inside a subagent.

**A `redacted_term` finding from `check_redactions.py` is not a check the
subagent can resolve.** `tailor-resume` step 7 requires that decision go to
the user, and a subagent has no user to put it to. Instruct each subagent
explicitly: on a `redacted_term` finding, do not rephrase or remove the
bullet yourself, and do not leave it in the draft unremarked either — both are
the silent resolutions step 7 forbids. Return the finding to the controller
unresolved, alongside the rest of its step 7 output, for the barrier in step 5
below.

**A budget drop needs telling, not deciding.** `tailor-resume` step 6 requires
telling the user exactly what was dropped when the selection exceeds
`max_lines`; a subagent has no user to tell. Unlike a `redacted_term`, the
selection call itself is not in question — step 6 already says dropping the
lowest-relevance entries is the correct move, not an error — so this does not
need a barrier of its own. Instruct each subagent to record what it dropped
and why, and return that list to the controller alongside its other step 7
output, for the report in step 9.

## 5. Barrier — redacted-term decisions

Collect every `redacted_term` finding phase B returned, across all slugs.
Group them the same way as the gap questions in step 3 — the same withheld
term is likely to fire on several drafts at once, since they are drawn from
the same `master/`, and should be decided once rather than once per slug.

Ask the user, per term: which application(s) it landed on, and where. Offer
keep, rephrase, or remove. Do not draft a rephrase yourself and offer it as
the default — the decision belongs to the user, not to a suggested edit.

Route the answer back to the owning subagent(s) with `SendMessage` to apply —
rephrase or remove in `draft.md` and, if a bullet is removed, in
`sources.json` too. A term the user chooses to keep needs no further action.
Do this before phase C so review runs against the draft the user actually
approved, not a placeholder.

## 6. Round 1, phase C — review

Dispatch one `resume-reviewer` per draft, concurrently.

**Record the review durably, every time you dispatch the reviewer, per
application, as its output comes back.** Save the JSON list it returns to a
file (e.g. `library/<slug>/.review-findings.json`), then:

    python3 scripts/check_review.py library/<slug> --record library/<slug>/.review-findings.json

This writes `library/<slug>/review.json`. Do this on every iteration for every
application, including one that comes back clean on the first pass —
`render-resume` refuses to run without it, and a fresh session running
`render-resume` cannot see this loop happen, only the record it leaves.

## 7. Barrier — route the findings

Route every reviewer finding **by kind**, using `tailor-resume` step 8's
table — not the comment-routing table in `AGENTS.md`. That table governs what
a *user* says about a draft; a reviewer finding is a different kind of input.

| Finding kind | Route |
|---|---|
| `unsupported`, `uncited`, `unknown_source`, `retired_source` | Exit the loop. Becomes a gap question |
| `over_budget`, `banned_word`, `first_person`, `filler_adverb`, `present_tense`, `em_dash`, `long_bullet` | Fix in the draft, then re-review |

**Style-kind findings never leave the slug that raised them and never become a
question.** Resume the owning subagent with `SendMessage`, have it fix
`draft.md` in place, then dispatch `resume-reviewer` again for that slug alone
and re-record the review — the same per-slug loop `tailor-resume` step 8 runs,
just triggered from this barrier instead of from inside the subagent. A
`banned_word` finding is not a missing preference: `hard-rules.md` already
states the rule the reviewer is enforcing; the fix is applying it in the
draft, never writing a new preference for a rule that already exists.

**Cap this per-slug loop at 3 iterations, the same cap `tailor-resume` step 8
sets.** `next_round` in step 8 below caps gap *rounds*, not review iterations
within a slug — nothing else bounds this loop, and without a cap it can
oscillate forever, exactly as step 8 describes: two hard rules can genuinely
conflict, e.g. "lead with metrics" and a 3-line budget cannot both be
satisfied. If a slug is still unresolved after 3 iterations, stop iterating on
it, surface the conflict to the user asking them to prioritise, and record the
resolution in `preferences/hard-rules.md` so it cannot recur on this slug or
any other. Report that slug's outcome in step 9 as it stands; do not let one
non-converging slug hold up the rest of the batch.

**On a fact finding, remove the offending bullet — from both `draft.md` and
`sources.json` — before it exits the loop**, exactly as `tailor-resume` step 8
requires. Routing the finding into the gap queue is not enough by itself:
unless the bullet is also deleted from both files, it keeps citing a live ID
and keeps passing the mechanical checks while the gap question sits
unanswered.

Group the fact questions the same way as step 3 — including the
`known-gaps.md` filter — and ask them in one pass. A finding that appears on
every draft at once — a timeline hole, a missing seniority signal — is one
question.

**Re-run every check on every iteration, on every affected slug, never only
the ones that failed before.** Rewriting a bullet to remove a banned word is
precisely when it drifts from its cited source, so a style fix can break the
fact check.

## 8. Round 2, or stop

```python
from resumelib.batch import next_round
next_round(round_index=1, new_questions=len(questions))
```

If it returns `True`, re-draft and re-review **only** the jobs whose cited
bullets changed. If `False`, stop. Report any gap still unresolved as an open
gap rather than looping on it — a reviewer can always find one more thing to
ask.

## 9. Report

Per application: whether checks passed, which questions it raised, **which
bullets were dropped for budget and why** — relaying what each phase B
subagent recorded in step 4, since `tailor-resume` step 6 requires the user
be told this and a subagent cannot tell them directly — and anything else
left open. Then hand off to `render-resume` for the ones the user approves.

A subagent that died mid-round leaves one partial directory, detectable by
shape — `requirements.md` with no `draft.md`, or a draft with no `review.json`.
Report it as incomplete and offer to resume that slug alone. Because each agent
owned one directory, no sibling application is affected.
