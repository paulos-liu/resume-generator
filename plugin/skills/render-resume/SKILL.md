---
name: render-resume
description: Render an approved resume draft to a sendable document and save it to the library. Use after a draft has passed review and the user has approved it, or when the user asks to export, render, or download a resume.
---

# Render resume

The terminal step. Turns an approved `draft.md` into a document the user can send.

## Preconditions

Do not render a draft that has not passed review. A fresh session cannot see
whether `tailor-resume`'s review loop ever ran — the only trustworthy signal is
the durable record it leaves, so check that first:

    python3 scripts/check_review.py library/<dir>

This fails (exit 1) when `library/<dir>/review.json` is absent, when its recorded
verdict is not clean, or when its recorded hash of `draft.md` no longer matches
the file on disk — the last case is exactly a draft edited by hand (or otherwise)
since the review that cleared it. If it reports a finding, stop: send the draft
back through `tailor-resume`'s review loop (step 8) rather than rendering it.

Then re-run both mechanical checks — they are cheap, and catch the case where
`master/` itself changed (e.g. a cited bullet was retired) since the review ran,
which a matching draft hash cannot rule out on its own:

    python3 scripts/check_provenance.py library/<dir> --master master
    python3 scripts/check_hard_rules.py library/<dir>/draft.md

If either reports findings, stop and report them. Rendering an unreviewed,
stale-reviewed, or since-invalidated draft defeats the gate.

## Render

**Where the built-in `docx` skill is available** (Cowork, claude.ai): use it to
produce `library/<dir>/resume.docx`, following `templates/standard.md` for section
order and heading structure.

**Where it is not** (Claude Code): leave `draft.md` as the deliverable and say so
plainly — "no document skill available here, so this is Markdown; open it in Cowork
to export." Do not fail the run, and do not hand-roll a converter.

## Verify the page count

`max_lines` is a proxy calibrated against the template, not ground truth. After
rendering, check the real page count against the length rule in
`preferences/hard-rules.md`.

If the render disagrees with the budget, the **budget** is wrong, not the draft.
Tell the user, and offer to recalibrate `max_lines` using the procedure in the
header of `templates/standard.md`.

## Save to the library

The application directory keeps the whole trail:

    library/2026-07-24-stripe-backend/
      job.md  requirements.md  draft.md  sources.json  resume.docx

`sources.json` is what makes the library worth keeping. Offer the user an
**interview prep sheet** built from it — every bullet on the resume they sent,
paired with the master fact behind it:

    "Reduced p99 checkout latency 73%"
      <- nw.b1: Cut p99 checkout latency from 340ms to 90ms by re-architecting
         the cart service. ~2M requests/day. Team of 4. Shipped Q3 2022.

That is the payoff of provenance: every claim they sent, with the detail to back
it up, ready before the interview.

## Never

- Render a draft with outstanding findings.
- Render when `review.json` is absent, unresolved, or stale relative to
  `draft.md`. Fix the draft through `tailor-resume`, not by re-running review
  checks yourself and calling it good — the record is what makes "good" durable.
- Edit the draft's content while rendering. Formatting only.
- Delete or overwrite a previous application's directory.
