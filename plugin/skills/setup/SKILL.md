---
name: setup
description: One-time setup for the resume assistant. Elicits hard rules and style preferences, harvests style exemplars, and calibrates the page budget. Use on first run, when preferences/style.md has no exemplars, or when the user asks to redo their resume preferences.
---

# Setup

Runs once. Populates `preferences/hard-rules.md` and `preferences/style.md`, then
calibrates the line budget.

## 1. Push for hard rules

Users do not volunteer "one page" or "no first person" — they complain after seeing
them violated. So ask directly, offering the common ones as a checklist:

- Maximum length: one page, two pages, no limit?
- First person allowed?
- Words you never want to see? (offer the defaults already in the file)
- Anything a recruiter in your field expects or hates?

Write each answer into the JSON fence in `preferences/hard-rules.md`. **If a rule
is decidable by parsing, it goes here, not in style.md** — a rule here is enforced,
a rule there is only applied.

If a stated rule is not mechanically decidable ("sound senior"), say so and route
it to the prefer/avoid list in `style.md` instead.

## 2. Harvest exemplars, do not ask about tone

Never ask "what tone do you want?" — that returns adjectives, and adjectives do
nothing at generation time.

Instead:

**If the user has ingested material:** pull the 8-10 strongest bullets out of it,
show them, and ask which sound like them. Keep the approved ones **verbatim** under
`## Exemplars` in `style.md`. Keep 3-5.

**If they have no prior material:** take one fact they have given you and draft the
same bullet three ways — outcome-first, scope-first, terse. Ask which reads right.
The choice is the signal; store the winner as the first exemplar.

## 3. Calibrate the budget

Follow the procedure in the header comment of `templates/standard.md`: fill the
template with filler bullets, render it, count the non-blank lines that fit on page
one. Write that number to `max_lines` in `preferences/hard-rules.md` and note the
date in the prose section beneath it.

## 4. Confirm

Show the user both finished files and get explicit sign-off before finishing. These
two files shape every resume the system will ever produce.

## Never

- Write to `master/` — that is `build-master`, even during setup.
- Record a style preference as an adjective.
- Skip calibration and guess at `max_lines`.
