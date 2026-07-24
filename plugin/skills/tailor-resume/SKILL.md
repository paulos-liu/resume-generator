---
name: tailor-resume
description: Produce a resume tailored to a specific job description by selecting and rephrasing facts already in the master resume. Use when the user shares a job posting, URL, or job description and wants a resume for it. Never adds facts.
---

# Tailor resume

Turn a job description into a tailored resume by **selecting and rephrasing what
already exists in `master/`**. You never add facts. You never write to `master/`.

## 0. Capture the job

Create `library/<YYYY-MM-DD>-<company>-<role-slug>/` and save the posting as
`job.md`.

If given a URL, fetch it. Job boards (Workday, Greenhouse, Lever) frequently block
fetching — this is normal, not an error. Ask the user to paste the text instead and
carry on.

## 1. Extract requirements

Write `requirements.md`: one line per distinct thing the job asks for, separated
into must-have and nice-to-have. Be granular — "Kubernetes" and "multi-region
failover" are two requirements, not one.

## 2. Match requirements to bullet IDs

For each requirement, find the master bullets that support it and record their IDs
next to it in `requirements.md`:

    - [must] Kubernetes operations — NO MATCH
    - [must] Large-scale service migration — nw.b2
    - [nice] Developer experience work — nw.b3

**A requirement with no match is a gap.** Do not try to cover it. Collect the
no-matches; they feed the gap loop.

Never cite a retired bullet. `scripts/check_provenance.py` will reject it anyway.

## 3. Select and rephrase

Choose the matched bullets that best serve this job, ordered by relevance. For
each, rephrase toward the job's own language while staying faithful to the source.

Faithful means: you may compress, reorder, or adopt the job's vocabulary. You may
not add a claim the source does not make, and you may not **drop a qualifier to
make a claim broader**. "Team of 4" must not become "teams." Vaguer is not safer —
it is how a stretch hides.

Apply `preferences/style.md`: match the exemplars' voice, follow the prefer/avoid
list. Obey every rule in `preferences/hard-rules.md`.

## 4. Emit the draft and its sources

Write `draft.md` using `templates/standard.md`.

Write `sources.json` alongside it — **every bullet, with at least one source ID**:

    [
      {"text": "Reduced p99 checkout latency 73% on a 2M req/day service",
       "source": ["nw.b1"]},
      {"text": "Migrated 38 services to ECS with zero customer-facing downtime",
       "source": ["nw.b2"]}
    ]

An uncited bullet is a hard failure, not a warning.

## 5. Check the budget

If the selected content exceeds `max_lines`, that is a **selection decision, not an
error**. Drop the lowest-relevance entries and **tell the user exactly what you
dropped**. Silent truncation is the bad outcome.

## 6. Self-check before review

    python3 scripts/check_provenance.py library/<dir> --master master
    python3 scripts/check_hard_rules.py library/<dir>/draft.md

Fix anything they report before going further.

## Refuse when the master is too thin

If `master/` has fewer than three entries or fewer than eight live bullets, stop
and route the user to `build-master` first. Tailoring against a thin master
produces either an empty resume or an invented one.

## 7. Review loop

Dispatch the `resume-reviewer` agent. Route what it returns **by kind** — this is
where fact integrity is structurally enforced, not a refinement.

| Finding kind | Route |
|---|---|
| `unsupported`, `uncited`, `unknown_source`, `retired_source` | **Exit the loop.** Becomes a gap question |
| `over_budget`, `banned_word`, `first_person`, `filler_adverb`, `present_tense` | Fix and re-review |

**Fact findings never auto-iterate.** If you iterate toward a passing verdict on an
unsupported claim, you will not find the truth — you will negotiate. "Led a team of
4 rebuilding checkout" becomes "contributed to cross-functional platform
initiatives", which passes by saying nothing. An unsupported claim is a gap for the
user to answer, not a drafting defect for you to fix.

**Re-run every check on every iteration, never only the failed ones.** Rewriting a
bullet to remove a banned word is precisely when it drifts from its cited source,
so a style fix can break the fact check.

**Cap at 3 iterations.** Then stop and surface whatever is unresolved. Two hard
rules can genuinely conflict — "lead with metrics" and a 3-line budget cannot both
be satisfied — and without a cap that oscillates forever. When you surface a
conflict, ask the user to prioritise, then record the resolution in
`preferences/hard-rules.md` so it cannot recur.

## Never

- Write to `master/`, including gap answers. Those go through `build-master`.
- Emit a bullet without a source ID.
- Drop a number or qualifier to make a claim easier to support.
- Cover a gap by writing around it.
