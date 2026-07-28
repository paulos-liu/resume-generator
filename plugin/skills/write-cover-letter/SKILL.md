---
name: write-cover-letter
description: Write a cover letter for an application already in the library, drawing every claim from the tailored resume's cited bullets. Use when the user asks for a cover letter for a job they have tailored a resume for. Never adds facts; requires a clean review record first.
---

# Write cover letter

Turn an approved application into a cover letter. The letter is prose, but it is
not exempt: **every claim about the user must already stand in the tailored
resume**, which means it traces to a cited master bullet. A cover letter that
outruns the resume it accompanies fails in the same interview the resume rules
exist to protect.

## Preconditions

Work inside an existing `library/<dir>/` that has `job.md`, `draft.md`,
`sources.json`, and a clean, current review:

    python3 scripts/check_review.py library/<dir>

If that fails, stop and route the user to `tailor-resume` first. A letter
drafted against an unreviewed resume inherits every unchecked claim in it. If
no application directory exists for this job at all, run `tailor-resume` first
— the letter is a companion artifact, never the starting point.

## 1. Read what is already vetted

The inputs are `job.md` and `draft.md`. Choose the two or three strongest
bullets from `draft.md` for this job's stated needs. Those are the letter's
achievements — restated as prose, but making **exactly the claims the bullets
make**. Compression and reordering are fine; a bigger number, a broader scope,
or a dropped qualifier is not. An `(est.)` figure stays estimated in prose:
"roughly", "around", "an estimated" — never the bare number.

## 2. Ground the company paragraph

Mention one or two specific things about the company to show the user did the
reading. Sources, in order of trust: `job.md` itself, then the company's own
public pages where fetching is available. If neither yields anything concrete,
ask the user what drew them to this company — do not pad with generic praise.

Never assume what the role will own, who it reports to, or what the team is
building beyond what the posting states. A wrong guess reads as careless, which
is the opposite of what a cover letter is for.

## 3. Write it

- **Shape:** 3-5 short paragraphs, one page maximum. Open with the role and
  why this company; middle maps the chosen achievements onto the job's needs;
  close with what the user would help the company do next.
- **Voice:** confident, warm, human. First person is correct here — the
  resume's first-person ban is a resume rule, not a letter rule.
- **Framing:** how the user helps the company succeed, not what the company
  does for the user's career. No flattery beyond the one grounded mention.
- **Style:** apply `preferences/style.md`. The parseable lists in
  `preferences/hard-rules.md` still bind — no em dashes, no banned words, no
  filler adverbs. They are word lists; search the finished letter for each
  before delivering. The line and bullet budgets are resume rules and do not
  apply.

Save as `library/<dir>/cover-letter.md`, next to the draft it accompanies.

## 4. Check every number

Before delivering, take each metric and factual claim in the letter and point
at the `draft.md` bullet it restates. Anything that has no bullet gets removed
or becomes a question for the user — and if the answer is a new fact, it routes
through `build-master`, never straight into the letter.

## Feedback routing

As everywhere (see `AGENTS.md`): phrasing and tone feedback goes to
`preferences/`, factual corrections go through `build-master`, and an
ambiguous comment gets a clarifying question, not a guess.

## Never

- Write a letter for a job with no reviewed application in `library/`.
- State a metric, scope, or title that no cited bullet supports.
- Drop an `(est.)` qualifier when restating an estimated figure as prose.
- Assume unstated facts about the role, team, or company.
- Use an em dash, a banned word, or a filler adverb from `hard-rules.md`.
- Exceed one page.
