---
name: build-master
description: Add, enrich, correct, or retract facts in the master resume. Use when the user reports experience, answers a gap question, corrects a draft's facts, uploads a resume or brag doc, or asks to update their master resume — including on a first run against an empty or thin master, or when the user says "help me build out my resume," "build out my resume," or "let's keep going." This is the only component permitted to write to master/.
---

# Build master

You maintain `master/` — the single source of truth. **You are the only writer.**
Every other component reads it.

## The rule that matters

Never write a fact the user has not confirmed in this conversation. Not from a
resume they uploaded, not from a LinkedIn export, not from inference.

Ingesting an existing resume uncritically imports its embellishments as ground
truth — old resumes are exactly where "led" means "was on the team." Every
downstream fact check then verifies against fiction. Propose, confirm, then write.

## Interview mode

When the master is empty or thin, or the user asks to "build out" their resume or
to "keep going," don't wait for material — **drive**. Follow the protocol in
[`interview.md`](./interview.md): scan coverage, attack the weakest area, and
surface the coverage map at checkpoints. It is still propose → confirm → write;
the interview only feeds that path richer, more complete material.

## Entry format

One file per role, project, skill, or education item, under the matching
`master/<type>s/` directory:

    ---
    id: role.northwind.staff-eng
    type: role
    company: Northwind Logistics
    title: Staff Engineer
    start: 2021-03
    end: 2024-08
    quiet: 2023
    ---

    - [nw.b1] (2022-Q3) Cut p99 checkout latency from 340ms to 90ms by
      re-architecting the cart service. ~2M requests/day. Team of 4.

A bullet may open with a period token — `(YYYY)` or `(YYYY-QN)` — immediately
after the id, before the text. It records *when the work happened*, not part of
the claim itself, and is stripped from the bullet's text when parsed. Write one
whenever the year is known; it is better to leave the token off than to guess a
date. An undated bullet is invisible to the coverage map's per-year accounting, so
date what you can.

`quiet: <years>` is a frontmatter key alongside `start`/`end`, bare years only,
comma-separated (e.g. `quiet: 2019, 2023`). It declares a year genuinely empty —
leave, illness, work under NDA — and, like any other write, only goes in after the
user confirms it.

**Bullet IDs are append-only.** Pick a short stable prefix per entry (`nw`, `ndj`)
and number upward forever. Never reuse a number, never renumber. A library entry
from six months ago still cites these.

## Ingest

Accept anything: resume, LinkedIn export, brag doc, performance review, notes.
Read it, extract candidate facts, and present them in batches of at most ten with
their proposed IDs. Ask the user to confirm, edit, or drop each batch. Write only
what survives.

For large material, batch — never ask someone to verify 200 facts in one message.

## Enrich

Score every bullet on three axes and target what is missing:

| Axis | Question |
|---|---|
| Metric | Is there a number? |
| Outcome | Did something change as a result? |
| Scope | How large — users, requests, dollars, headcount, duration? |

A bullet missing one is a concrete question, not a vague nudge:
"'Improved onboarding' — improved it by how much, and for how many users?"

Stop when the user says stop. Enrichment is a conversation, not an interrogation.

## Write

For each confirmed fact, classify the write first:

- New fact on an existing entry -> **append** a bullet with the next free ID.
- New role or project -> **new entry file**, new ID prefix.
- Promotion at the same company -> **new role entry**, not an edit. Title, scope,
  and dates all differ, and bullets must stay attributable to the right level.

Correction and retraction have their own flow — see the `## Correct and retract`
section of this skill.

## Commit

One commit per confirmed write. The message records what changed and why, because
`git log master/` is the audit trail:

    master: add nw.b7 — gap answer (Kubernetes, Stripe application)
    master: correct nw.b1 — team size 4->3, per user correction

## Correct and retract

Classify first — these are three different writes:

- **Imprecise, same underlying fact** -> correct the text in place, **keep the ID**.
  Past resumes made this same claim; correcting the source corrects the record.
- **Actually a different fact** -> new ID. Leave the original alone.
- **Does not hold up / was overstated** -> **retract**: move the bullet under a
  `## Retired` heading in its entry file. Never delete it.

Retract rather than delete because IDs are append-only. A retired ID still
resolves, so a library entry from six months ago does not dangle — but
`check_provenance.py` will reject any *new* draft that cites it.

### Always run the staleness check first

    python3 scripts/check_staleness.py nw.b3 --library library

If it reports hits, show them to the user before making the change:

    ! nw.b3 is cited in 2 resume(s) you already sent:
        library/2026-03-11-northwind-platform
        library/2026-05-02-acme-infra

That is the whole point. Quietly fixing the master leaves the user unaware they
have a claim in the wild they can no longer back up — which is the exact interview
failure this system exists to prevent.

Confirm edits more strictly than appends. Silently changing a fact already sent
out is worse than silently adding one.

## Recording gap answers

Gap answers arrive from `tailor-resume`. Both kinds are writes, and both are yours.

**"Yes, I have done that."** Treat it as a new fact: confirm the specifics
(metric, outcome, scope) before writing, exactly as in `## Enrich`. A gap answer
is not pre-confirmed just because it answers a question — this is precisely where
someone stretches to fit a job they want.

**"No, I haven't."** Append to `master/known-gaps.md`:

    - [2026-07-24] Kubernetes — asked during Stripe Backend application

Commit as `master: record known gap — Kubernetes`.

## Never

- Write without confirmation.
- Reuse or renumber a bullet ID.
- Write to `preferences/` — that is the setup skill and the feedback rules.
- Invent a metric because a bullet felt thin. Ask.
