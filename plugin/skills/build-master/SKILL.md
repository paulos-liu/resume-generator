---
name: build-master
description: Add, enrich, correct, or retract facts in the master resume. Use when the user reports experience, answers a gap question, corrects a draft's facts, uploads a resume or brag doc, or asks to update their master resume. This is the only component permitted to write to master/.
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
    ---

    - [nw.b1] Cut p99 checkout latency from 340ms to 90ms by re-architecting the
      cart service. ~2M requests/day. Team of 4. Shipped Q3 2022.

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

Correction and retraction have their own flow — see the `update-master` section
of this skill once Task 13 adds it.

## Commit

One commit per confirmed write. The message records what changed and why, because
`git log master/` is the audit trail:

    master: add nw.b7 — gap answer (Kubernetes, Stripe application)
    master: correct nw.b1 — team size 4->3, per user correction

## Never

- Write without confirmation.
- Reuse or renumber a bullet ID.
- Write to `preferences/` — that is the setup skill and the feedback rules.
- Invent a metric because a bullet felt thin. Ask.
