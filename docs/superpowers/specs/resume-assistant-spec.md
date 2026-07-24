# Resume Assistant — System Spec

## Overview

A single system with **two modes** that share one source of truth. The system helps a user maintain a rich "master resume" and then produce tailored, job-specific resumes from it — without ever inventing experience.

- **Build mode** — creates and maintains the master resume (the only mode that writes facts to it).
- **Tailor mode** — takes a job description and produces a tailored resume by *selecting and rephrasing* from the master (never adding new facts).

Two things persist across the whole system and grow over time: the **master resume** (facts) and the **preferences memory** (style + rules). A **reviewer** step guards the output before the user ever sees it.

---

## Core principle: fact integrity

The master resume is the single source of truth. **Tailor mode may only select and rephrase what already exists in the master. It may never invent, embellish, or stretch.**

This is the load-bearing rule of the whole system. It exists to solve a specific, real failure: generated resumes that overstate experience, leaving the user unable to back up claims in interviews. If something *needs* to be stretched to fit a job, that is by definition a **gap**, not a license to embellish — and gaps get surfaced to the user as questions, not silently written into the output (see Gap-detection loop).

---

## The master resume (data model)

Store the master as a **structured store**, not freeform prose. Each unit of experience is its own discrete, richly-detailed entry ("chunk") so tailor mode can pull and recombine cleanly.

Suggested entry types:
- **Roles** — company, title, dates, and a detailed body: responsibilities, accomplishments, metrics, technologies, scope.
- **Projects** — standalone efforts, with the same depth.
- **Skills** — with supporting evidence where possible (which role/project demonstrates it).
- **Education / certifications / other.**

Design notes:
- Entries should be *detailed and specific* — this is the raw material tailoring draws from, so richer is better. Build mode should actively push the user toward specifics (numbers, outcomes, scope).
- Keep entries atomic enough that tailor mode can include/exclude/reorder them per job.
- Only build mode writes here.

---

## Preferences memory

Separate from the master resume. Holds everything about *how* resumes should be written, not *what* is true. Persists across every job. Seeded at setup, refined continuously through feedback.

Split into **two buckets**, because they behave differently when applied:

1. **Style / voice** — tone, phrasing conventions, level of formality, how to frame accomplishments, preferred verbs, etc. Soft guidance.
2. **Hard rules / constraints** — e.g. "never exceed one page," "always lead with impact metrics," "no first-person." Non-negotiable; the reviewer enforces these.

Setup should proactively elicit initial preferences from the user rather than waiting for feedback to accumulate.

---

## Feedback system

All user feedback is captured and routed to one of two destinations based on what kind of feedback it is:

- **Preference feedback** (style, voice, rules) → **preferences memory.** Applies to all future resumes.
- **Factual feedback** (corrections or additions to actual experience) → **master resume** (via build mode).

The system should be able to tell these apart — a comment about phrasing updates memory; a comment revealing a new accomplishment updates the master.

---

## Gap-detection loop

When tailor mode processes a job (or when the user/reviewer inspects a draft) and the job asks for something **not present in the master**:

1. Do **not** generate a claim to cover it.
2. Surface it to the user as a question: *"This role wants X. Do you have experience with that?"*
3. If the user has real experience → route the answer back through **build mode** to write it into the master (so it enriches the source of truth and is available for all future jobs).
4. If not → leave it out honestly.

This is the virtuous cycle: the master gets richer every time it meets a new job. It's also the *only* path by which tailor mode indirectly causes a write — and it always goes through build mode, never directly.

---

## Reviewer step

Runs on the tailored output **before it reaches the user**. Checks:

1. **Truthfulness / fact integrity** — every claim in the output must be directly backed by a master entry. Anything unsupported, or that reads as a stretch, is flagged and routed into the gap-detection loop as a question — not embellished, not silently kept.
2. **Style / voice** — output matches the preferences memory.
3. **Hard rules** — all constraints satisfied (length, formatting, etc.).

The reviewer's fact check is the automated enforcement of the core principle: it's what catches the "stretch from the truth" problem systematically rather than relying on tailor mode to behave.

---

## Tailored-resume library

Every tailored resume tailor mode produces is saved. When a new job resembles a past one, the system can offer to start from that prior version: *"You applied to something similar — want to start from that resume?"* Saves rework and keeps similar applications consistent.

---

## Mode responsibilities (summary)

| | **Build mode** | **Tailor mode** |
|---|---|---|
| Master resume | Read + **write** | **Read only** |
| Preferences memory | Read + write (setup) | Read (apply) |
| Primary input | User's experience, feedback, gap answers | Job description / URL |
| Output | Updated master | Tailored resume (+ library entry) |
| Can invent facts? | No — captures what user reports | **Never** — select & rephrase only |
| Gap handling | Writes confirmed gaps into master | Detects gaps, asks user, routes to build |

---

## Suggested build order

1. Master resume data model + build mode (create/edit entries, setup preference elicitation).
2. Preferences memory (two buckets) + feedback routing.
3. Tailor mode (read master → select/rephrase → draft) with strict no-invention constraint.
4. Gap-detection loop wiring tailor → user → build.
5. Reviewer step (fact integrity, style, hard rules).
6. Tailored-resume library + similarity suggestion.
