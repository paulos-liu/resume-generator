# Companion artifacts and the keyword report

**Date:** 2026-07-28
**Status:** implemented

Extends the system past the resume itself: a cover letter skill, an outreach
email skill, a deterministic keyword-coverage report, and two new hard rules.
The additions were harvested from a set of standalone prompt-style skills a
user had refined through real applications; this doc records what was adopted,
what was rejected, and why.

## What was adopted

**Two companion skills** — `write-cover-letter` and `outreach-email`. Both
operate only on an existing `library/<dir>/` application with a clean, current
`review.json`, and both are bound by one rule, now stated in `AGENTS.md`
invariant 4: every claim they make about the user restates a cited bullet from
that application's reviewed `draft.md`. The resume is the vetted surface; prose
that accompanies it may compress and reorder but never outrun it. This closes
the obvious hole where the resume is airtight and the email beside it says
whatever sounded good.

The outreach skill keeps the source material's best structural ideas, all
career-neutral: four audience variants (hiring manager, recruiter, skip-level,
peer), a Blurb section restating the strongest cited bullets, the
don't-presume-ownership hedge for the skip-level variant, insider-style
subject lines, and `[hyperlink JD here]` placeholders so links are added by
the user, never fabricated.

**Two hard rules**, both parseable and so per invariant 5 both scripts:

- `ban_em_dash` — em dashes in bullet or prose lines read as machine-written
  filler. Headings are exempt because `templates/standard.md` itself uses one
  to separate a role title from its dates, and the en dash in a date range is
  untouched.
- `max_bullet_words` (shipped at 40) — the point where a bullet wraps past two
  rendered lines and stops being skimmable. The trimming priority (keep the
  verb, keep the metric, cut context last) went to `style.md`; the limit is
  enforced, the trimming taste is applied.

**The keyword report** — `scripts/keyword_coverage.py`. See below.

**Skills-section discipline** in `tailor-resume`: the Skills section is the
draft's keyword surface, populated with the job's own vocabulary — but only
terms whose requirement found a master match. A skills line is a claim like
any other.

## What was rejected

- **"Suggested" metrics.** The source skills allowed invented metrics if
  labeled *suggested* with an explanation. That labeling discipline is the
  manual ancestor of this system's gap loop, and the gap loop replaces it
  outright: an unsupported number is a question for the user routed through
  `build-master`, never a labeled guess. Adopting it would break invariant 2.
- **Alignment percentages.** Unfalsifiable model-invented scores; nothing
  downstream could consume them except misplaced confidence.
- **Everything personal or career-specific.** Named-industry tone calibration,
  profession-specific summary formulas, a specific person's tooling and
  employers. A shared plugin ships none of that (invariant 7); only the
  career-neutral generalizations were kept, and they went to `preferences/`
  where a user's own copy is meant to diverge.

## Why the keyword report is a report, not a gate

The screening layer between a submitted resume and a human matches words, not
meaning, so a draft that cites the right bullet but never uses the job's own
term has a real, invisible problem — invisible to `check_provenance.py`
(the citation is valid) and to `check_hard_rules.py` (no rule is broken).

But two legitimate states would fail a hard gate forever:

1. A requirement with **no master match** is an honest gap. Failing the draft
   for not naming it is pressure to invent — the exact pressure the system
   exists to remove. The report lists these as GAP and never counts them
   against the draft.
2. A **matched bullet dropped for the length budget** (step 6 is explicitly a
   selection decision) takes its keywords with it. That is a trade-off the
   user made, not an error.

So the script follows the `coverage_report.py` precedent, not the `check_*.py`
one: deterministic scan, always exit 0, and `tailor-resume` decides per row —
rephrase toward the job's term, or note why not. Wiring it into the review
loop as findings would recreate the style-judge failure: iterating toward
keyword density is how a resume becomes a word salad of the posting.

## Sequencing

Both companion skills sit after the review loop, like `render-resume`, and
verify that position the same way: `scripts/check_review.py` on the library
directory. They add no new checks and no new writers — `library/` remains
written by the tailoring flow, `master/` by `build-master` alone.
