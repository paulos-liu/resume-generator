# Master Resume Interview — Design

**Date:** 2026-07-24
**Status:** Approved, ready for implementation planning
**Extends:** [`2026-07-24-resume-assistant-design.md`](./2026-07-24-resume-assistant-design.md) — this adds a proactive interview capability to `build-master`; the fact-integrity machinery there is unchanged.

---

## 1. Overview

Today `build-master` is **reactive**: it ingests what you hand it, enriches bullets that already exist, and processes corrections. It waits for material. It has no notion of what a *complete* master looks like, so a three-year role with one thin bullet is indistinguishable from a fully-fleshed one.

This design adds a **proactive interview capability**: the system actively drives someone toward a **robust** master resume — the superset of their career from which every job-specific resume is later selected — and knows when to push versus ease off. This is the primary information source going forward, so it warrants significant depth.

### The load-bearing constraint

The interview is a better *elicitation front-end*. It does **not** get a shortcut to disk. Every fact still flows through `build-master`'s existing propose → **confirm** → assign ID → write → commit path. Nothing is written that the user has not confirmed in-conversation. The interview feeds that path richer material; it does not weaken the rule.

---

## 2. What "robust" means

Four axes, all derived by **scanning `master/`** at checkpoint time — never stored, so coverage state cannot drift (the same philosophy as the existing staleness check: a grep, not a feature). Breadth and sections are mechanical (counts, dates, presence); depth is near-mechanical (is there a number?); the angle axis is a light model judgment made during the scan. None of it persists.

| Axis | Measured by | "Thin" when |
|---|---|---|
| **Breadth** | role/project count; timeline gaps derived from entry `start`/`end` dates | an unexplained date gap, or a multi-year role with <3 accomplishments |
| **Depth** | per bullet: is there a metric? an outcome? a scope? | any bullet missing one of the three |
| **Angle** | per bullet: is leadership / collaboration / technical / business context present? | the bullet supports only one framing |
| **Sections** | presence of skills (with evidence links) and education | a section is empty or unlinked |

"Robust" is a **tunable target**, not 100% of anything: every substantive role carries ≥3 accomplishments, each hitting metric + outcome + scope and re-angleable, plus skills and education present. The map shows distance to that target; the user can declare any role "done" and move on.

### The angle axis and "range of angles"

The angle axis is what lets the same accomplishment be re-told for different jobs — a project as a *technical* win for one application, a *leadership* win for another. It is satisfied **without any data-model change**: by writing a richer prose bullet into the same greppable, single-ID unit.

One rich source bullet —

> `[nw.b1] Led 4 engineers rebuilding the cart service, cutting p99 checkout latency 340ms→90ms across ~2M req/day; became the template for 3 later service migrations.`

— already supports a leadership angle ("Led 4 engineers…"), a technical angle ("re-architected the cart service, 73% latency reduction"), and an influence angle ("set the migration pattern adopted by 3 teams"), all faithful to that one cited ID. Provenance, the reviewer, `check-provenance.py`, and tailor are untouched.

Estimated metrics are written with an explicit flag (e.g. `~40% (est.)`) so they stay defensible in an interview — honoring the rule that estimates must never be silently upgraded to hard numbers.

---

## 3. Architecture

`build-master` gains a proactive interview capability. The SKILL.md stays lean; the interview protocol — the long part — lives in a companion file the skill loads when building or growing the master:

```
plugin/skills/build-master/
  SKILL.md         # unchanged charter + a pointer into interview.md
  interview.md     # the interview protocol (new)
```

This preserves the focused-file discipline the rest of the repo follows.

**Triggers.** The skill's `description` already fires on "asks to update their master resume." Added triggers: first run with an empty or thin master; "help me build out my resume"; "let's keep going" (resume a prior session). A cold start auto-enters the interview; a mature master enters targeted gap-filling.

**No changes to** the data model, `sources.json`, `check-provenance.py`, the reviewer, or tailor. That containment is the point of this approach: a large new capability with zero blast radius on the fact-integrity machinery.

---

## 4. The interview protocol

A **coverage-driven loop**: scan `master/` → find the weakest axis → run the matching move → propose → confirm → write (existing path) → recompute → surface the map at checkpoints.

The moves run in the order the research shows minimizes fatigue and maximizes recall.

### 4.1 Timeline sweep (breadth first)

Walk jobs chronologically. Per role, capture only "what were you hired to do vs. what you were actually doing by the end" — the gap between the two *is* the accomplishment. Coverage, not depth. Anchor on transitions (promotions, reorgs, launches, crises). Flag unexplained date gaps as candidate missing roles.

### 4.2 Evidence mining (cheap, high-yield)

Prompt the user to open real artifacts — calendar, past performance reviews, sent mail/Slack searched for "shipped / launched / fixed / thanks," old resumes, git history. Their own "workday debris" surfaces forgotten work at low cognitive cost.

### 4.3 Story deep-dives (depth, one at a time)

Per thin role, story-framed openers: "what are you most proud of here?", "a mess you walked into and cleaned up," "what were you the go-to person for?" STAR/CAR are **invisible skeletons** behind natural questions — captured as rich prose, never as labeled fields.

Three **deterministic sub-routines** fire mechanically inside deep-dives. These are the highest-payoff, encodable-as-explicit-logic moves — testable rather than left to free-form judgment:

- **The "just my job" flag.** Any dismissive phrase ("that was just my job," "we did it") auto-triggers a counter-probe: *"Plenty of people have that job and don't do it that way — what did you do that someone else in your seat wouldn't have?"* Directly counters underselling.
- **The quantification ladder.** When a bullet has no number, walk six rungs, easiest first — scope → frequency/volume → team/audience size → before/after → time saved → money — accepting defensible **ranges and estimates** (flagged as such), never inventing.
- **The "why did that matter?" ladder.** Climb from a flat fact to its business impact until it reaches a terminal value — turning "migrated the database" into "team stopped losing a day a week → shipped the launch on time."

### 4.4 Angle probe

For a bullet that is quantified but single-framed, one targeted question surfaces the missing dimension — the leadership behind a technical win, or the business impact behind a leadership one — enriching the same bullet so tailor can re-angle it.

### 4.5 Section sweep & catch-all close

Batch-menu format for skills/education coverage (menus jog memory and cut load). Every section ends with the single best catch-all: *"What are you proud of that I never asked about?"*

### 4.6 Pacing

- One open question at a time; never two open-enders back-to-back (fatigue is cumulative, not time-based).
- Work in **sittings**; the map is the re-entry point.
- Stop a section on **saturation** — two consecutive probes yielding no new information.

---

## 5. The hybrid map

Surfaces at **checkpoints only** — end of a role, start of a session — never as an always-on dashboard (which would tempt filling the bar over telling the true story).

It renders the coverage scan: which roles are thin, which bullets lack an axis, which sections are empty, and what is next. Example:

```
MASTER COVERAGE

Roles
  Northwind Staff Eng   ●●●○○  3 bullets, 1 unquantified
  Acme Senior Eng       ●○○○○  1 bullet   ← thin
  (gap?) 2019–2021       ○○○○○  no role recorded

Sections
  Skills     ●●●○○        Education ●●●●●

Next: Acme is thin — want to dig into it?
```

Two jobs:

- **Resume point** across sittings — "here's where you left off, here's what's still thin."
- **Steering surface** — the user can redirect: "skip that internship, go deep on Northwind."

Rendered from a live scan of `master/` each time (frontmatter dates → timeline gaps; per-bullet axis checks), so it is never stale. `known-gaps.md` continues to absorb "no, never done that" answers so the interview does not re-ask.

---

## 6. Write path & honesty guarantees

- Every accomplishment surfaced still flows through the existing propose → **confirm** → assign ID → write → commit. The interview never writes unconfirmed material.
- Estimated metrics are written with their `(est.)` flag intact and are never silently upgraded to hard numbers.
- Coverage is **computed, never persisted** — no `coverage.md` to drift.
- The data model, `sources.json`, `check-provenance.py`, the reviewer, and tailor are unchanged.

---

## 7. Testing

Fits the existing split: deterministic parts become scripts/fixtures; judgment parts become labeled fixtures.

1. **Sub-routine fixtures** — labeled transcripts proving the three deterministic moves fire: a "just my job" utterance triggers the counter-probe; a numberless bullet triggers the quantification ladder; a flat fact triggers "why did that matter." These are the encodable-as-logic behaviors, so they are testable.
2. **Coverage-scan test** — a synthetic master with known thin spots (a 1-bullet role, a 2019–2021 date gap, a metric-less bullet, an empty skills section); assert the scan flags exactly those and no others.
3. **Honesty regression** — the load-bearing one: confirm no bullet reaches `master/` without confirmation, and that an estimate is never silently upgraded to a hard number. Guards the same invariant the invention test guards for tailor.

---

## 8. Scope

**In (v1):**

- The interview capability in `build-master`, with the protocol in `interview.md`
- The four-axis coverage model (breadth, depth, angle, sections) computed by scanning `master/`
- The hybrid checkpoint map
- The three deterministic sub-routines (just-my-job flag, quantification ladder, why-did-that-matter ladder)
- Timeline / evidence / story / angle / section moves
- Fatigue-aware pacing and sittings
- The three test groups above

**Deferred, with reasons:**

| Deferred | Reason |
|---|---|
| Structured STAR fields per accomplishment | Rejected, not merely deferred: it breaks the single greppable bullet that provenance, the faithfulness judge, and `check-provenance.py` depend on — for a gain that rich prose already delivers |
| A visual/graphical coverage map | The text checkpoint render is enough for v1 and works identically in Cowork and Claude Code |
| Auto-mining connectors (reading the actual calendar/email via MCP rather than prompting the user to) | Real value, but its own project with its own auth and privacy surface |

---

## 9. Build order

1. Coverage scan — the function that reads `master/` and reports thin spots by axis. Testable in isolation; everything else consumes it.
2. `interview.md` protocol — the moves and the deterministic sub-routines.
3. Wire the interview into `build-master`'s triggers and the existing write path.
4. The checkpoint map render over the coverage scan.
5. Tests: sub-routine fixtures, coverage-scan test, honesty regression.
