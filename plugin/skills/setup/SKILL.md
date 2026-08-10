---
name: setup
description: One-time setup for the resume assistant. Elicits hard rules and style preferences, harvests style exemplars, and calibrates the page budget. Use on first run, when preferences/style.md has no exemplars, or when the user asks to redo their resume preferences.
---

# Setup

Runs once. Populates `preferences/hard-rules.md` and `preferences/style.md`, then
calibrates the line budget.

## 0. Check this is the user's own private copy — before anything else

    python3 scripts/check_private.py

Everything after this step writes real personal data, and everything after
`setup` writes more of it. Git history is published along with the tree, so a
repo that turns out to be public or shared cannot be fixed by deleting files
later — the commits still hold the user's name, employers, and dates.

The check answers two questions and fails closed on both:

- **Is this the user's own copy, or the shared upstream tool repo?** Writing one
  person's employment history into the repo everyone pulls from is the mistake
  that cannot be walked back.
- **Is that copy private?**

On `[SAFE]`, continue. On `[UNSAFE]`, **stop** and walk the user through
`README.md` → "Getting your own copy" — they need their own private repo before
any of this is worth doing. On `[UNKNOWN]` the check could not tell (no remote,
a non-GitHub host, or `gh` unavailable); ask the user to confirm both facts
directly, and do not guess on their behalf.

Do not skip this because the repo "looks fine." The failure is silent at the
time and permanent afterwards.

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

## 5. Offer career-ops — optional

[career-ops](https://github.com/santifer/career-ops) scans public ATS boards,
checks a posting is still live, and scores it against a CV. It is **optional**:
everything here works without it. Offer it once; if the user declines, do not
raise it again.

If they want it:

1. Clone it somewhere outside this repo:

       git clone https://github.com/santifer/career-ops.git ~/Projects/career-ops

2. Copy `config/profile.example.yml` to `config/profile.yml` there and fill in
   targets, locations, and comp range. That is search preference, not resume
   fact, so it lives there and not in `master/`.

3. Generate its CV from the master:

       python3 scripts/export_cv_md.py

   `cv.md` is generated, never authored. Tell the user plainly: editing it by
   hand creates a second source of truth, and every score after that describes
   someone the drafts cannot cite.

Do not run step 3 before the master has facts in it — `build-master` comes
first. If `master/` is still empty, note the option and stop.

## Never

- Write to `master/` — that is `build-master`, even during setup.
- Record a style preference as an adjective.
- Skip calibration and guess at `max_lines`.
- Write anything personal before step 0 has returned `[SAFE]`, or before the
  user has confirmed the two facts themselves on `[UNKNOWN]`.
- Put the user's real name, address, email, or employers into anything outside
  `master/`, `preferences/`, and `library/` — test fixtures and examples included.
  Those files are shared; those three directories are not.
