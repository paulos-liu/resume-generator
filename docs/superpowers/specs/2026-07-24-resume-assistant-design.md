# Resume Assistant — Design

**Date:** 2026-07-24
**Status:** Approved, ready for implementation planning
**Source spec:** [`resume-assistant-spec.md`](./resume-assistant-spec.md) (the *what*; this document is the *how*)

---

## 1. Overview

A system that maintains a rich **master resume** and produces tailored, job-specific
resumes from it — without ever inventing experience.

Two modes share one source of truth:

- **Build mode** creates and maintains the master resume. It is the only writer.
- **Tailor mode** turns a job description into a tailored resume by *selecting and
  rephrasing* what already exists. It never adds facts.

Two stores persist and grow: the **master resume** (facts) and the **preferences
memory** (style and rules). A **reviewer** guards every output before the user sees it.

### The load-bearing rule

Tailor mode may only select and rephrase what exists in the master. It may never
invent, embellish, or stretch. Anything that would need stretching to fit a job is by
definition a **gap** — surfaced to the user as a question, never written silently into
the output.

This exists to solve one real failure: resumes that overstate experience, leaving the
user unable to back up claims in an interview.

---

## 2. Decisions and rationale

| Decision | Choice | Why |
|---|---|---|
| Delivery | Portable skill set — plugin + plain Markdown state | Runs in **Cowork** (daily driver: mobile, connectors, `docx`/`pdf` export) and **Claude Code** (authoring, testing, git). Same artifact, no application to build |
| Distribution | Shareable template repo; users fork private and commit their own data | Generic for anyone; every user gets a git audit trail of their own facts; upstream improvements remain pullable |
| Fact enforcement | Provenance IDs + mechanical check + narrow faithfulness judge | Converts an open-ended question ("is this supported *anywhere*?") into a narrow, reliable one ("is this faithful to *this* cited bullet?"). Yields an interview prep sheet for free |
| Output | Markdown draft + calibrated content budget; render last | Length is enforced deterministically without rendering, so it works in both surfaces. Rendering happens once, at the end |
| Reviewer form | A **subagent**, not a skill | A skill loads into the drafting context. Only an agent gets a fresh context window — which is what makes the check real |
| Style | Split by decidability: grep-able rules enforced by the reviewer, the rest applied at generation via approved exemplars | A rule too vague to check is too vague to apply. Exemplars beat descriptions; a fuzzy style judge would only manufacture nitpicks |

### Rejected alternatives

- **GitHub PR-based review.** The reviewer step is diff-shaped and the appeal is real,
  but it collides with the Cowork/mobile daily driver and with being usable by
  non-developers. It also makes the gap loop slow: "do you have Kubernetes experience?"
  should be a 20-second exchange, not a comment round-trip. The valuable half — an audit
  trail — comes free from committing the master to git, with no GitHub coupling. May
  return later as an optional power-user layer.
- **Judge-only fact checking.** No IDs, no data-model burden, but it is a model grading
  a model over a growing haystack, with no deterministic floor and no record of what
  backed what.
- **Claim decomposition + retrieval.** Catches stretches, but the retrieval step is
  itself fuzzy, and it re-derives on every review what tailor mode already knew when it
  wrote the bullet.
- **Telling the reviewer to be "adversarial."** Tone is the weakest available lever and
  this word backfires: a reviewer told to be adversarial manufactures findings to
  justify itself, producing false positives until the user learns to skim past it.
  Replaced with an explicit burden of proof (§6.2).

---

## 3. Repository layout

```
resume-generator/
  plugin/
    .claude-plugin/plugin.json
    skills/
      setup/SKILL.md              # one-time preference elicitation
      build-master/SKILL.md       # ONLY writer to master/
      tailor-resume/SKILL.md      # reads master, never writes it
      render-resume/SKILL.md      # markdown -> docx/pdf
    agents/
      resume-reviewer.md          # fresh context; the gate
  master/
    roles/ projects/ skills/ education/
    known-gaps.md                 # answered "no" — stops repeat questions
  preferences/
    style.md                      # exemplars + prefer/avoid; applied at generation
    hard-rules.md                 # deterministic; enforced by the reviewer
  library/
    2026-07-24-stripe-backend/
      job.md  requirements.md  draft.md  sources.json  resume.docx
  templates/
    standard.md                   # + calibrated max_lines
  tests/
    fixtures/                     # synthetic master + job descriptions
  scripts/
    check-provenance.sh
  AGENTS.md                       # canonical standing rules incl. feedback routing
  CLAUDE.md                       # one line: "See AGENTS.md"
```

`AGENTS.md` holds the standing rules and is the portable one; `CLAUDE.md` only points at
it. Keeping a single canonical copy avoids the two files drifting apart.

The template repo ships with the structure and empty stores. A user clones it, makes
their copy **private**, and commits their own facts.

### Skills vs. agents

| Component | Form | Reason |
|---|---|---|
| `setup`, `build-master`, `tailor-resume`, `render-resume` | skill | They talk to the user; they need the conversation |
| `resume-reviewer` | agent | It must **not** see the conversation |

A skill loads into the current context; an agent runs as a subprocess with its own
context window. The reviewer's isolation is only real as an agent — a reviewer that
watched itself write the draft will rationalize it.

---

## 4. Data model

The file formats are the interfaces between components. Nothing shares in-memory state,
which is what lets the system run identically in Cowork and Claude Code.

### 4.1 Master entry

```markdown
---
id: role.acme.staff-eng
type: role
company: Acme
title: Staff Engineer
start: 2021-03
end: 2024-08
---
- [acme.b1] Cut p99 checkout latency 340ms->90ms by re-architecting the cart
  service. ~2M req/day. Team of 4. Shipped Q3 2022.
- [acme.b2] ...
```

Three properties make the fact check cheap:

- **Greppable** — mechanical verification needs no model.
- **Append-only** — `acme.b3` is never reused, so a library entry from six months ago
  still resolves.
- **Bullet-level** — provenance is per claim, not per job.

Entry types: `role`, `project`, `skill`, `education`. Skills carry evidence references
to the role or project bullets that demonstrate them.

### 4.2 Tailor output contract

`draft.md` is human-readable; `sources.json` carries provenance:

```json
[
  { "text": "Reduced checkout latency 73% across a 2M req/day service",
    "source": ["acme.b3"] }
]
```

Every bullet must cite at least one source ID. This is required, not advisory — an
uncited bullet is a hard failure.

### 4.3 Preferences memory

Style is hard to *check*, and that is the same reason it is hard to *apply*: a rule too
vague to verify is too vague to act on. `style.md` full of "be direct, sound senior"
changes nothing at generation time. So preferences are split by **whether a rule is
mechanically decidable**, not by how important it feels.

**`hard-rules.md` — deterministic, enforced by the reviewer.** Much of what feels like
style is actually checkable by grep:

```markdown
- max_lines: 42            # from the calibrated template
- no first person ("I", "my")
- banned words: spearheaded, synergy, leveraged, utilized, passionate
- past tense for all prior roles
- no filler adverbs: very, really, significantly, substantially
```

Zero false positives, no model judgment, no cost. Anything that can be moved here
should be.

**`style.md` — applied at generation, never audited.** Two parts:

1. **Exemplars.** Three to five bullets the user has approved *verbatim*, used as
   few-shot examples. This is the strongest available style signal — you do not describe
   a voice, you show it. The set improves for free: every bullet the user approves or
   rewrites during review is a candidate exemplar.
2. **Prefer/avoid pairs**, never adjectives:

   ```markdown
   - prefer "built" / "shipped" over "spearheaded" / "drove"
   - lead with the outcome, then the mechanism
   - avoid: "responsible for X"  →  prefer: "did X, producing Y"
   ```

**No fuzzy style judge.** The irreducibly subjective remainder is left to generation
time and to the user's own read of the draft. A style judge is the component most likely
to manufacture nitpicks until the reviewer's output gets skimmed past — and style
defects, unlike fact defects, are visible on first read.

---

## 5. Flows

### 5.1 Setup (once)

Elicits both preference buckets and writes `style.md` and `hard-rules.md`. It must
actively *push* for hard rules — users do not volunteer "one page" or "no first person"
unprompted; they complain only after seeing them violated.

Seeding `style.md` needs a different technique, because asking "what tone do you want?"
produces adjectives, and adjectives are useless at generation time (§4.3). Instead setup
**harvests exemplars**: it pulls the strongest bullets out of whatever the user ingested,
asks which ones sound like them, and keeps the approved ones verbatim. If the user has no
prior material, setup drafts three variants of one bullet and asks which reads right —
the choice is the signal.

It also selects a template and calibrates its budget: render the template full of filler
once, count what fits, store `max_lines` alongside it.

### 5.2 Build mode — the only writer

```
ingest any artifact ─┐
enrich thin entry  ──┼→ propose → CONFIRM WITH USER → assign ID → write → commit
gap answer         ──┘
```

**The confirm step is not ceremony.** Ingesting an existing resume uncritically would
import its embellishments as ground truth — old resumes are exactly where "led" means
"was on the team." A master seeded from unverified claims makes every downstream fact
check verify against fiction. Extraction proposes; the user confirms; only then does it
get an ID.

Ingest is format-agnostic: resume, LinkedIn export, brag doc, performance reviews,
scattered notes. Cowork reads PDF and docx natively, so there is no parser to write. The
real work is not parsing but **interrogating**.

**Enrichment targeting.** Each bullet is scored on three axes — **metric, outcome,
scope**. A bullet missing any of them becomes a concrete interview target: *"'Improved
onboarding' — improved it by how much, and for how many users?"* This makes enrichment
systematic rather than a matter of taste.

### 5.3 Updating the master

Four triggers, one path: direct statement, gap answer from tailor, factual feedback on a
draft, or an enrichment session.

Build mode's first job is classifying the write:

```
new fact?
├─ about an existing role/project? ──→ APPEND bullet, new ID (acme.b7)
├─ a new role/project entirely?    ──→ NEW entry file, new ID namespace
└─ promotion at same company?      ──→ NEW role entry, not an edit
                                        (title/scope/dates differ — bullets must stay
                                         attributable to the right level)

existing fact, stated wrong?
├─ imprecise, same underlying fact ──→ CORRECT in place, KEEP the ID
├─ actually a different fact       ──→ new ID; leave the original alone
└─ doesn't hold up / overstated    ──→ RETRACT: retire the ID, never delete
```

**Retract, never delete.** IDs are append-only, so a retired ID is never reused and an
old library entry citing it still resolves. Deleting would leave dangling provenance and
silently break the audit trail.

**Staleness check.** On any correct-or-retract, build mode greps `library/*/sources.json`
for that ID and reports what it touches:

```
Retracting acme.b3 ("led a team of 4").
! Cited in 2 resumes you already sent:
    library/2026-03-11-stripe-backend/    (applied Mar 11)
    library/2026-05-02-figma-platform/    (applied May 2)
```

This is a grep, not a feature, but it is the difference between quietly fixing the master
and knowing there is a claim in the wild that can no longer be backed up.

Every write is confirmed; **edits more strictly than appends**, because silently changing
a fact already sent out is worse than silently adding one.

**Commit discipline** is what makes `git log` the audit trail:

```
master: add acme.b7 — gap answer (Kubernetes, Stripe application)
master: correct acme.b3 — team size 4->3, per user correction
master: retract acme.b5 — user withdrew "owned roadmap"
```

### 5.4 Tailor mode — reads master, writes nothing to it

```
job (url/paste/file) → library/<slug>/job.md
  1. extract requirements  → requirements.md      (checklist)
  2. match each requirement to master bullet IDs
  3. rephrase selected bullets toward the job's language
  4. emit draft.md + sources.json
  5. check line budget
  6. dispatch resume-reviewer (fresh context)
```

Step 1 is what makes gap detection fall out for free: a requirement with **no matching
bullet ID** is a gap, detected before a word is drafted rather than caught downstream.

### 5.5 The review loop

Findings are routed **by type**. This is not a refinement — it is where the core
principle is structurally enforced.

```
      ┌────────────────────────────────────────────┐
      │                                            │
   draft ──→ resume-reviewer ──→ hard-rule/length ─┘  auto-iterate, max 3
                    │
                    └──────────→ fact finding ──→ EXIT LOOP ──→ gap question
```

- **Hard-rule and length findings auto-iterate.** No fact content is at stake; this is
  where the loop saves round trips. Banned-word and tense violations land here too, since
  they live in `hard-rules.md` (§4.3) and are decided by grep.
- **Fact findings exit immediately.** An unsupported claim is not a drafting defect to be
  fixed — it is a gap, and it becomes a question to the user.
- **Cap at 3 iterations**, then surface whatever is unresolved.

**Why fact findings must not auto-iterate.** Tell a writer "this claim isn't supported"
and let it iterate freely toward a passing verdict, and it will not go find the truth —
it will negotiate. *"Led a team of 4 rebuilding checkout"* becomes *"contributed to
cross-functional platform initiatives,"* which passes by saying nothing. Or it quietly
re-cites a different bullet that sort-of covers it. Convergence pressure plus a model
that wants a green check produces text that is neither false nor useful.

**Every iteration re-runs all checks, never only the failed ones.** Rewriting a bullet
for style is precisely when it drifts from its cited source, so a style fix can break the
fact check. Incremental re-review would miss it.

### 5.6 Gap loop

Two sources feed one queue: unmatched requirements from tailor step 2, and unsupported
claims from the reviewer.

Questions are asked **in a batch**, not one at a time. Real answers route through build
mode and enrich the master for every future job. "No, I haven't done that" also routes
through build mode, which records it in `master/known-gaps.md` so the system stops asking
about Kubernetes on every backend role.

This is the only path by which tailor mode indirectly causes a write, and it always goes
through build mode — including the negative answers, since build mode is the sole writer
to `master/`.

### 5.7 Feedback routing

A standing rule in `AGENTS.md`, not a skill:

- Comments about **how it reads** → preferences memory (`style.md` or `hard-rules.md`).
- Comments revealing **what is true** → build mode.
- **Ambiguity is asked, never guessed.** "This sounds too junior" could mean framing
  (style) or missing seniority evidence (fact); guessing writes to the wrong store.

Preference writes are specific and dated — *"prefer 'built' over 'spearheaded'"*, not
*"be more direct."* Where a preference is decidable by grep it goes to `hard-rules.md`,
not `style.md`, so the reviewer can enforce it.

**Rewrites are harvested as exemplars.** When the user rewrites a bullet by hand rather
than describing what they wanted, that rewrite is the cleanest style signal available —
offer to keep it in `style.md`. This is how the exemplar set compounds without the user
ever having to articulate their voice.

---

## 6. The reviewer

### 6.1 Checks

1. **Fact integrity** — mechanical: every bullet cites at least one ID, and every cited
   ID exists in the master. Then narrow judgment: is the rephrasing faithful to *that
   specific* cited bullet?
2. **Hard rules** — all constraints in `hard-rules.md`: line budget, banned words, first
   person, tense, filler adverbs. All decided by grep or count; no model judgment.

There is deliberately no third, subjective style check — see §4.3.

### 6.2 Burden of proof

The reviewer is given an explicit default verdict rather than a tone:

> A claim is unsupported unless the specific cited bullet contains it. When uncertain,
> rule unsupported.

This is checkable and it fails in the safe direction. The adversarial property is already
structural: fresh context, no visibility into the writer's reasoning, and mandatory
citation.

---

## 7. Error handling

| Failure | Handling |
|---|---|
| Draft cites a nonexistent ID | Hard fail, mechanical grep. Primary defense against invention; no model judgment involved |
| Loop hits 3 iterations unresolved | Surface findings to the user; **never ship silently** |
| Master too thin to tailor against | Refuse below a threshold and route to build mode — garbage in, embellishment out |
| Job URL will not fetch | Common (Workday, Greenhouse block scrapers). Fall back to paste; not an error |
| Relevant experience exceeds budget | A selection decision, not an error. Drop lowest-relevance entries and **report what was dropped**. Silent truncation is the bad outcome |
| Two hard rules conflict | Surface, ask the user to prioritize, then **record the resolution** in `hard-rules.md` so it cannot recur |
| No `docx` skill available (Claude Code) | Degrade to Markdown with a warning; do not fail the run |
| Huge ingest (years of reviews) | Chunk and confirm in batches; never ask the user to verify 200 facts at once |
| Session interrupted mid-write | Writes are per-file and committed on confirm, so at most one unconfirmed entry is lost |

---

## 8. Testing

There is no application code, so the split is: **deterministic parts become scripts,
judgment parts become labeled fixtures.**

`tests/fixtures/` holds a synthetic master (fake person, known facts) and several job
descriptions.

1. **The invention test** — the one that matters most. Feed tailor a job description
   demanding something *deliberately absent* from the fixture master. Correct behavior is
   a gap question; any bullet covering it is a regression. Runs after every prompt edit.
2. **Provenance integrity** — `scripts/check-provenance.sh`: every ID in `sources.json`
   exists in the master. Deterministic, free, exact.
3. **Faithfulness fixtures** — labeled (source, rephrasing) pairs the reviewer must
   classify, loaded with near-misses, since that is where drift lives. *"Led a team of
   4"* → *"led engineering teams"* is a stretch; a reviewer that passes it is broken.
4. **Hard-rule enforcement** — over-budget drafts, banned words, first person, and wrong
   tense are all caught. Scriptable alongside the provenance check, since every rule in
   `hard-rules.md` is decidable without a model.
5. **Loop termination** — conflicting hard rules terminate at 3 rather than hanging.

Build the invention test **before** the tailor skill. It is the reason the system exists,
and it is easier to write while still being honest about what "unsupported" means.

---

## 9. v1 scope

**In:**

- Master data model with provenance IDs
- Build mode: ingest, interview/enrichment, update, correct, retract, staleness check
- Setup and both preference buckets, including exemplar harvesting
- Style applied at generation via exemplars + prefer/avoid pairs
- Tailor mode with mandatory provenance and requirement extraction
- `resume-reviewer` agent: fact integrity + hard rules (incl. banned words, tense,
  first person — all deterministic)
- Typed review loop with 3-iteration cap
- Gap detection and `known-gaps.md`
- Library saves every artifact
- Render via the `docx` skill
- Invention test, provenance script, faithfulness fixtures

**Deferred, with reasons:**

| Deferred | Reason |
|---|---|
| Similarity matching ("you applied to something like this") | Cannot be tuned until a dozen applications exist to tune against. Saving is nearly free; matching is a real feature |
| A subjective style *judge* | Not deferred — **rejected**. The checkable part of style moves into `hard-rules.md` and the reviewer enforces it deterministically (§4.3); the rest is applied at generation via exemplars. A fuzzy judge would manufacture nitpicks until the reviewer gets ignored, and style defects are visible on first read anyway |
| Multiple templates | Ship one, calibrated properly |
| Plugin marketplace packaging | v1 is "clone the repo, attach the folder" |
| GitHub PR review layer | See §2 rejected alternatives |

---

## 10. Build order

1. Data model + fixtures + `check-provenance.sh` + the invention test
2. Build mode (ingest, interview, write, commit)
3. Setup and preferences
4. Tailor mode with provenance
5. `resume-reviewer` agent and the typed loop
6. Gap loop wiring tailor → user → build
7. Update/correct/retract + staleness check
8. Render + library
