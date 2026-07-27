# Recruiter impressions pass

**Date:** 2026-07-27
**Status:** approved, not yet implemented

Adds one advisory agent that reads a finished draft the way a senior recruiter
would and reports impressions, with an emphasis on style. Its feedback reaches
`preferences/` only through the user, and it can never block a render.

## Why this is not the style judge the design rejected

`plugin/agents/resume-reviewer.md` forbids itself from commenting on style:

> There is deliberately no style check here. Inventing one produces nitpicks
> until your output gets ignored.

`preferences/style.md` says the same from the other side: style is "applied at
generation time, never audited."

That objection is about a style *judge* — an agent whose findings enter a fix
loop and iterate toward a passing verdict. This is a different thing. It returns
prose to a human, never findings to a machine; nothing parses its output, and no
code path leads from it to the render gate. The rejection stands for judges; it
does not cover an advisory reader.

The distinction is load-bearing. If a later change routes this agent's output
into the review loop, the original objection applies again in full and the loop
will grind toward vagueness, because vaguer bullets attract fewer style notes.

## Component

One file: `plugin/agents/recruiter-impressions.md`.

**Blind by construction.** Its prompt receives the rendered PDF and nothing
else — no `master/`, no `preferences/`, no conversation history, no target
posting. It sees what an inbound recruiter sees.

This is the feature, not a limitation. An agent told which claims the master
supports stops reacting like a reader and starts reasoning like an insider,
which is the one perspective the rest of the system already has. The cost is
that it will sometimes suggest something impossible; filtering those is the
assistant's job, not the agent's.

**Persona.** An experienced recruiter, deliberately not tied to any industry —
the tool ships to anyone. It infers the field, function and seniority from the
page itself and then reads as a specialist for that desk would, because a nurse,
a litigator and a data engineer are judged by different standards and generic
advice serves none of them. If it cannot place the resume, that is its lead
finding: a resume whose field cannot be identified in seconds gets discarded,
and no line-level polish fixes it.

Calibration is blunt: it reads the resume as one of forty for the same opening
and says what would get it passed over. Encouragement is not the product.

**Output.** Prose, in five parts: the eight-second scan; style and voice, with
lines quoted; what would get it screened out; what a first call would ask; and
line-level rewrites shown against the originals.

## Placement

A terminal step in `tailor-resume`, after the gap loop (step 9), and separately
invocable on demand.

After the facts settle, because style notes on a bullet that a fact finding is
about to delete are wasted, and because the harvest writes preferences based on
final wording.

The tradeoff accepted: no style feedback on a rough draft. On-demand invocation
covers the case where the user wants an early read anyway.

## Harvest

The agent writes nothing. The user reads the impressions and says what they
agree with; only then is anything recorded, routed through the table already in
`AGENTS.md`:

| Feedback is about | Goes to |
|---|---|
| Phrasing, ordering, voice | `preferences/style.md`, prefer/avoid list |
| A bullet the user rewrites by hand | `preferences/style.md` as an exemplar, verbatim |
| Decidable by parsing (length, a banned word) | `preferences/hard-rules.md` |
| "Add a number here" | `build-master`, as a gap question |

The last row is the one that will be got wrong. A recruiter's reflex is to ask
for quantification, and some bullets have no measurement behind them by record —
`master/roles/lytx-swe3-b.md` states plainly that no before/after exists for the
AI transformation work and that no draft may imply one. Routing "quantify this"
to `preferences/` would encode *invent metrics* as a house style. It is a fact
gap or it is nothing.

Ambiguous feedback follows the existing rule: ask, never guess.

## Guarantees

- Never writes `review.json`; never emits findings; never gates `render-resume`.
  This holds because no code reads its output, not because the prompt says so.
- Never edits a draft.
- Never sees `master/`, so it cannot leak a fact the resume deliberately omits.

## Testing

The agent is a prompt, so the testable surface is wiring, mirroring the existing
`TestInterviewWiring` guard on `build-master`'s `interview.md` link:

- `check_manifest.py` already validates agent frontmatter; the new file is
  covered once it exists.
- Add a test asserting `tailor-resume/SKILL.md` references
  `recruiter-impressions`, so the step cannot be silently dropped.
- Add a test asserting `recruiter-impressions.md` does **not** mention `master/`
  — the blindness is the design, and a later edit that helpfully grants it
  access should fail the build rather than pass review.

## Out of scope

- Changing the review loop's termination. The 3-iteration cap and the deliberate
  non-looping on fact findings stay as they are.
- Making generation a subagent. Raised and set aside; the writer benefits from
  conversation context in a way the reviewer must not, and that asymmetry needs
  its own design.
- Automatic rendering after a clean review.

## Porting

The feature lands in `resume-generator`. `paulos-resume` carries its own copy of
the tool and picks changes up by cherry-pick from the `upstream` remote.
