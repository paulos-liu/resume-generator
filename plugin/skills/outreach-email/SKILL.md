---
name: outreach-email
description: Draft follow-up emails to people on a hiring team for an application already in the library - hiring manager, recruiter, skip-level, and peer variants. Use when the user wants to follow up on an application or reach out about a role. Never adds facts; requires a clean review record first.
---

# Outreach email

Draft the short emails a candidate sends after applying: one message, four
audiences. Same integrity rule as everything else here — **every claim about
the user restates a cited bullet from the tailored resume**. An email is the
easiest place to inflate, because nobody checks it against anything. This
skill checks it against `draft.md`.

## Preconditions

An existing `library/<dir>/` with `job.md`, `draft.md`, `sources.json`, and a
clean, current review:

    python3 scripts/check_review.py library/<dir>

If that fails, route the user to `tailor-resume` first.

## 1. Collect what only the user knows

Ask for, and never invent: the recipients' names and roles (or write
`[Name]` placeholders if unknown), the user's preferred title line, and the
links for the signature. A fabricated LinkedIn URL or phone number in a sent
email is worse than none — leave a `[link]` placeholder for anything the user
has not supplied.

## 2. Write four variants

All four share one body shape; the opening line and the ask shift with the
reader's stake in the role:

- **Hiring manager** — the direct fit: lead with the one achievement most
  relevant to their team's stated problem.
- **Recruiter** — the process: confirm interest, make the fit skimmable in
  one sentence, make it easy to slot the user into the pipeline.
- **Above the hiring manager** — the redirect: shortest of the four, and it
  must not presume they own the role. Include the hedge, in substance:
  "While researching the team, your name came up. I am not sure whether this
  role falls within your team, but if it does not, I would appreciate a
  pointer in the right direction."
- **Peer (future teammate)** — the perspective ask: curiosity about the team
  and the work, not a pitch.

Rules that bind all four:

- **Length:** 2-3 short paragraphs, one screen maximum. No bulky blocks.
- **Subject line:** a natural internal nudge — "Quick follow-up", "Touching
  base". No company name, no role title, nothing that reads as a campaign.
- **Job reference:** write the role as `[Role Title (hyperlink JD here)]` in
  the body, so the user remembers to add the real link before sending. Never
  fabricate the URL.
- **Framing:** how the user helps the company succeed. Warm, confident,
  specific; no flattery padding.
- **Style:** `preferences/style.md` applies, and the parseable word lists in
  `preferences/hard-rules.md` bind — no em dashes, no banned words, no filler
  adverbs. Search the finished text for each. Resume line budgets do not
  apply.

## 3. Blurb and signature

After the body, a **Blurb:** section of two or three sentences carrying the
user's strongest achievements for this role — each one a restatement of a
`draft.md` bullet, smooth prose, no run-ons and no choppiness. `(est.)`
figures stay estimated in prose.

Signature: full name and title in bold, then links and phone from what the
user supplied in step 1. A short metrics line (e.g. "12 services migrated |
40% latency reduction") is welcome **only** when every figure in it comes
from a cited bullet — this line is the single most tempting place in the
whole system to round up, which is exactly why it is checked like a bullet.

Save all four variants in one file: `library/<dir>/outreach-emails.md`.

## 4. Check every number

Point each metric and factual claim, including the Blurb and the signature
metrics line, at the `draft.md` bullet it restates. No bullet, no claim. A
missing fact the user wants to add routes through `build-master` first.

## 5. Check for withheld terms

    python3 scripts/check_redactions.py library/<dir> --master master

This **reports, never rewrites**: whether to name a withheld term in an email
that reaches a hiring team is the user's decision. If it returns a
`redacted_term` finding, present it to the user — which term, and which
variant it landed in — and let them choose to rephrase, remove it, or
knowingly keep it. Do not silently edit or silently leave it yourself.

## Never

- Draft outreach for a job with no reviewed application in `library/`.
- Invent a recipient, a link, a phone number, or any contact detail.
- State a metric or scope no cited bullet supports, anywhere — body, Blurb,
  or signature.
- Presume the recipient owns the role, or skip the hedge in the skip-level
  variant.
- Put the company or role name in the subject line.
- Use an em dash, a banned word, or a filler adverb from `hard-rules.md`.
- Resolve a `check_redactions.py` finding yourself instead of putting the
  decision to the user.
