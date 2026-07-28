---
name: tailor-resume
description: Produce a resume tailored to a specific job description by selecting and rephrasing facts already in the master resume. Use when the user shares a job posting, URL, or job description and wants a resume for it. Never adds facts.
---

# Tailor resume

Turn a job description into a tailored resume by **selecting and rephrasing what
already exists in `master/`**. You never add facts. You never write to `master/`.

## 0. Refuse when the master is too thin

Before capturing the job, check whether `master/` has enough to draft from
honestly:

    python3 scripts/check_master_thin.py --master master

If it reports a `thin_master` finding (fewer than three entries or fewer than
eight live bullets), stop here and route the user to `build-master` first.
Tailoring against a thin master produces either an empty resume or an invented
one, and this is the highest invention-pressure state in the whole system — the
check runs first, before the job is even captured, precisely so the guard fires
before any drafting exists to be pressured into.

## 1. Capture the job

Create `library/<YYYY-MM-DD>-<company>-<role-slug>/` and save the posting as
`job.md`.

If given a URL, fetch it. Job boards (Workday, Greenhouse, Lever) frequently block
fetching — this is normal, not an error. Ask the user to paste the text instead and
carry on.

## 2. Extract requirements

Write `requirements.md`: one line per distinct thing the job asks for, separated
into must-have and nice-to-have. Be granular — "Kubernetes" and "multi-region
failover" are two requirements, not one.

## 3. Match requirements to bullet IDs

For each requirement, find the master bullets that support it and record their IDs
next to it in `requirements.md`:

    - [must] Kubernetes operations — NO MATCH
    - [must] Large-scale service migration — nw.b2
    - [nice] Developer experience work — nw.b3

**A requirement with no match is a gap.** Do not try to cover it. Collect the
no-matches; they feed the gap loop.

Never cite a retired bullet. `scripts/check_provenance.py` will reject it anyway.

## 4. Select and rephrase

Choose the matched bullets that best serve this job, ordered by relevance. For
each, rephrase toward the job's own language while staying faithful to the source.

Faithful means: you may compress, reorder, or adopt the job's vocabulary. You may
not add a claim the source does not make, and you may not **drop a qualifier to
make a claim broader**. "Team of 4" must not become "teams." Vaguer is not safer —
it is how a stretch hides.

A bullet may open with a leading `(YYYY)` or `(YYYY-QN)` token — that is metadata
about *when* the work happened, not part of the claim. Never carry it into the
drafted bullet; dropping it is not dropping a qualifier.

Apply `preferences/style.md`: match the exemplars' voice, follow the prefer/avoid
list. Obey every rule in `preferences/hard-rules.md`.

**The Skills section is the keyword surface — and it obeys the match table.**
Populate it with the job's own vocabulary, but only terms whose requirement
found a master match in step 3. A NO MATCH term never appears there: a skills
line is a claim like any other, and listing an unmatched keyword is invention
with extra steps.

**Never drop an `(est.)` marker.** `build-master`'s interview mode writes uncertain
figures with an explicit marker, e.g. `Cut build time ~40% (est.)`. Restating that
as `Cut build time 40%` is not compression — it is an unsupported claim. The
marker is the caveat that makes the number honest; keeping the digit while
dropping the marker turns an estimate into a hard number the user cannot back up
in an interview.

**Carry the literal `(est.)` string.** `check_provenance.py` matches that exact
marker, so "an estimated $100K+" reads as honest prose to a human and as a
dropped qualifier to the checker — it will fail. If a rendering without the
parenthetical is genuinely wanted, change the checker deliberately; do not work
around it in a draft. This is
the same failure as dropping "Team of 4" to get "teams" — a claim made broader by
removing the word that limited it — and it is checked the same way: mechanically,
by `scripts/check_provenance.py`'s `estimate_upgraded` finding.

## 5. Emit the draft and its sources

Write `draft.md` using `templates/standard.md`.

Write `sources.json` alongside it — **every bullet, with at least one source ID**:

    [
      {"text": "Reduced p99 checkout latency 73% on a 2M req/day service",
       "source": ["nw.b1"]},
      {"text": "Migrated 38 services to ECS with zero customer-facing downtime",
       "source": ["nw.b2"]}
    ]

An uncited bullet is a hard failure, not a warning.

## 6. Check the budget

If the selected content exceeds `max_lines`, that is a **selection decision, not an
error**. Drop the lowest-relevance entries and **tell the user exactly what you
dropped**. Silent truncation is the bad outcome.

## 7. Self-check before review

    python3 scripts/check_provenance.py library/<dir> --master master
    python3 scripts/check_hard_rules.py library/<dir>/draft.md

Fix anything they report before going further.

Then run the keyword report:

    python3 scripts/keyword_coverage.py library/<dir>

It shows, per requirement, whether the job's own vocabulary surfaces in the
draft — the words an applicant tracking system or a skimming recruiter would
match on. It is a report, not a gate. For each MISSING or PARTIAL row on a
**matched** requirement, either rephrase the supporting bullet toward the job's
term (staying faithful to the source) or note why not — a bullet dropped for
budget in step 6 is a legitimate reason. GAP rows are honest gaps: they feed
step 9, and the draft must never be pushed to name them.

## 8. Review loop

Dispatch the `resume-reviewer` agent. Route what it returns **by kind** — this is
where fact integrity is structurally enforced, not a refinement.

| Finding kind | Route |
|---|---|
| `unsupported`, `uncited`, `unknown_source`, `retired_source` | **Exit the loop.** Becomes a gap question |
| `over_budget`, `banned_word`, `first_person`, `filler_adverb`, `present_tense`, `em_dash`, `long_bullet` | Fix and re-review |

**Record the review durably, every time you dispatch the reviewer.** Save the
JSON list it returns to a file (e.g. `library/<dir>/.review-findings.json`), then:

    python3 scripts/check_review.py library/<dir> --record library/<dir>/.review-findings.json

This writes `library/<dir>/review.json`: the findings, a clean/unresolved
verdict, and a hash of the `draft.md` this review applied to. Do this on every
iteration, including the one that finally comes back clean — a fresh session
running `render-resume` cannot see this loop happen, only the record it leaves.
Without it, nothing distinguishes a reviewed draft from a draft that was never
reviewed, or one hand-edited after the review that cleared it.

**Fact findings never auto-iterate.** If you iterate toward a passing verdict on an
unsupported claim, you will not find the truth — you will negotiate. "Led a team of
4 rebuilding checkout" becomes "contributed to cross-functional platform
initiatives", which passes by saying nothing. An unsupported claim is a gap for the
user to answer, not a drafting defect for you to fix.

**On a fact finding, remove the bullet — from both files — before exiting the
loop.** Routing the finding to a gap question is not enough by itself: unless the
offending bullet is also deleted from `draft.md` and its entry deleted from
`sources.json`, it keeps citing a live ID and keeps passing both mechanical
checks while the gap question sits unanswered. "Leave unanswered gaps out of the
resume" (step 9) is about no-match requirements that were never drafted; this is
about a bullet that already exists on the page and must be taken back off it.
Put a bullet back covering this ground only if the eventual gap answer supports
it — a new bullet from `build-master`, matched and cited fresh through step 3 —
never the original unsupported line restored as-is.

**Re-run every check on every iteration, never only the failed ones.** Rewriting a
bullet to remove a banned word is precisely when it drifts from its cited source,
so a style fix can break the fact check.

**Cap at 3 iterations.** Then stop and surface whatever is unresolved. Two hard
rules can genuinely conflict — "lead with metrics" and a 3-line budget cannot both
be satisfied — and without a cap that oscillates forever. When you surface a
conflict, ask the user to prioritise, then record the resolution in
`preferences/hard-rules.md` so it cannot recur.

## 9. Gap loop

Two sources feed one queue: no-match requirements from step 3, and fact findings
that exited the review loop in step 8.

**Check `master/known-gaps.md` first** and drop anything already recorded there.
Asking someone twice whether they know Kubernetes is how a system teaches people to
stop reading its questions.

**Ask the remaining gaps in one batch**, not one at a time:

    This role wants three things your master doesn't cover:
      1. Kubernetes operations
      2. Multi-region failover
      3. Go
    Do you have real experience with any of them?

Route every answer through `build-master` — you never write to `master/` yourself,
and that includes the answers that are "no".

- **Yes** -> `build-master` writes a new entry or bullet. Then re-run from step 3;
  the new bullet is now available to every future job too.
- **No** -> `build-master` records it in `known-gaps.md`.

Leave unanswered gaps out of the resume. Honestly absent beats plausibly stretched.
That includes a bullet a fact finding already removed in step 8 — it stays out
unless a fresh, properly sourced bullet earns its way back in.

## 10. Recruiter impressions (advisory, terminal)

Once the facts have settled — review clean, gaps resolved — dispatch the
`recruiter-impressions` agent for a read on how the page actually lands.

It gets the rendered resume and **nothing else**: no `master/`, no
`preferences/`, no posting, no context from this conversation. That blindness is
the whole value. Do not helpfully brief it.

**Its output is advice, not findings.** It never writes `review.json`, never
blocks a render, and never enters the review loop of step 8. Wiring it into that
loop reintroduces exactly the failure `resume-reviewer` refuses style checks to
avoid: iterating toward a passing style verdict grinds bullets toward vagueness.

**Filtering its suggestions is your job, not its.** Being blind, it will
sometimes propose something the master cannot support — a stronger verb than the
source carries, a range resolved to its flattering end, a number that does not
exist. Check every suggested rewrite against the cited master bullet before
applying it. Take the lesson, not the literal wording.

Then route what the user agrees with, and only what they agree with:

| Feedback is about | Goes to |
|---|---|
| Phrasing, ordering, voice | `preferences/style.md`, prefer/avoid |
| A bullet the user rewrites by hand | `preferences/style.md` as an exemplar, verbatim |
| Decidable by parsing (length, a banned word) | `preferences/hard-rules.md` |
| "Add a number here" | `build-master`, as a gap question |

That last row is the one that will be got wrong. A recruiter's reflex is to ask
for quantification, and some bullets have no measurement by record. Routing that
to `preferences/` would encode *invent metrics* as house style. It is a fact gap
or it is nothing.

## Never

- Write to `master/`, including gap answers. Those go through `build-master`.
- Let `recruiter-impressions` output become a finding, gate a render, or brief
  itself on the master.
- Apply a recruiter rewrite without checking it against the cited master bullet.
- Emit a bullet without a source ID.
- Drop a number or qualifier to make a claim easier to support.
- Drop an `(est.)` marker while keeping the number it qualified.
- Cover a gap by writing around it.
- List a NO MATCH requirement's term in the Skills section, or let the keyword
  report pressure a gap into the draft.
- Leave a bullet in `draft.md` or `sources.json` after a fact finding routed it
  out of the review loop.
- Skip recording `review.json` on any review iteration, including the clean one.
