# career-ops integration and batch tailoring

Connects [career-ops](https://github.com/santifer/career-ops) as the discovery,
scoring, and tracking front end to this repo's tailoring and rendering back end,
and adds a batch mode that tailors many jobs at once while asking the user each
question only once.

## Why

Job intake today is manual: postings are pasted by hand into an untracked
`jobs/` directory. career-ops already solves the upstream half — it scans public
ATS APIs, checks that a posting is still live, and scores it against a CV — and
it tracks applications across their lifecycle. Its generation layer overlaps
with `render-resume` and `write-cover-letter`, but without their provenance
guarantee, so generation stays here.

Scanning produces many candidate jobs at once, which makes the per-job gap loop
the bottleneck. Six postings that all want Kubernetes should produce one
question, not six.

## Principles

1. **No code is added to career-ops.** It stays a clean upstream clone so
   `update-system.mjs` keeps working. Every new component lives in this repo.
2. **`cv.md` is generated, never authored.** `export_cv_md.py` is its only
   writer, mirroring the rule that makes `build-master` the only writer to
   `master/`.
3. **Nothing flows back into `master/` automatically.** A gap career-ops
   surfaces becomes a question for `build-master`, never a write.
4. **Claims are versioned; scouting notes are not.** `master/`, `library/`, and
   `preferences/` are permanent and in git. career-ops' `pipeline.md`,
   `applications.md`, and `reports/` are disposable and gitignored upstream.

## Architecture

```
  master/  ──[export_cv_md.py]──►  career-ops/cv.md   (generated, gitignored)
                                          │
                                          ▼
   scan.mjs ──► data/pipeline.md ──► oferta eval ──► reports/NNN-*.md
                                          │              data/applications.md
                                          │
                       [import_job.py] ◄──┘  (a report the user pursues)
                                          │
                                          ▼
                  library/<slug>/job.md ──► batch-tailor ──► draft ──► render
```

Two crossings, both one-way: facts out as a generated `cv.md`, jobs in as a
`job.md`.

### Repository layout

career-ops stays at `~/Projects/career-ops`, tracking upstream. Its `.gitignore`
already excludes `cv.md`, `data/*`, `reports/*.md`, `jds/*`, and
`config/profile.yml`, so personal data lands in the working tree and never in a
commit. The residual risk is a deliberate `git add -f`, not the default path.

`config/profile.yml` — targets, locations, comp range — is hand-authored once in
career-ops. It is search preference, not resume fact, so it does not belong in
`master/` and is not generated.

## Component 1 — `scripts/export_cv_md.py`

Renders `master/` into career-ops' `cv.md` format.

**Output structure.** Header from `master/contact.md` frontmatter: name,
location, email, LinkedIn, GitHub. Phone is excluded — it buys nothing in an
evaluation and is the field least worth placing in a model prompt. Then
`## Work Experience` (one `###` per role, ordered by `start` descending),
followed by `## Projects`, `## Skills`, and `## Education` in that order —
each is emitted only when it has bullets, so a master with an empty section
never produces an empty heading.

`master/known-gaps.md` is never read. Its bullets are precisely what cannot be
claimed.

No Professional Summary is emitted. career-ops' format has one, but a summary is
synthesized prose, and this export never writes a sentence that is not a master
bullet.

Roles with no live bullets still get a heading. Timeline continuity is why a career-break
entry exists at all.

**Bullet extraction is an allowlist.** Only lines matching `- [<id>] …` and
their indented continuations are exported. Prose paragraphs, `**bold notes**`,
and confirmation lines are excluded by construction, so a new kind of private
annotation added to `master/` later is excluded without anyone updating a
blocklist.

Within a bullet: strip the `[id]` marker and a leading `(YYYY)` or `(YYYY-QN)`
token, which `tailor-resume` already treats as metadata rather than a claim.
Nothing else is removed; the only other transformation is the redaction
substitution below, applied after extraction.

In particular, `**Scope boundary:**` segments are retained. They read oddly in a
CV, but `cv.md` is an evaluator input rather than something an employer sees.
Removing one would drop a qualifier — the failure `tailor-resume` forbids — and
would bias the fit score optimistic.

Bullets under `## Retired` are skipped.

**Redaction.** Some master bullets name a fact the user has decided not to
publish without being asked first — a real customer, a project codename.
`cv.md` is read by `gemini-eval`, `openai-eval`, and `openrouter`, so a verbatim
export would disclose a deliberately withheld fact to a third party without
asking. Stripping the phrase instead would drop a qualifier. Neither default is
correct.

The withheld term itself is never written into this document, the plan, or any
test fixture. It lives in `master/redactions.md` and nowhere else — a spec that
spelled it out would leak precisely what the feature exists to contain, into the
one directory that gets shared.

`master/redactions.md` is a single store, not a block in each role's
frontmatter: one term per line, `- term => replacement`. It carries no
frontmatter, so `load_entries` skips it exactly as it skips `known-gaps.md`,
and applies to the whole export, not only the file that would have declared
it — a term withheld once is withheld everywhere. The export **fails closed**:
a bare `- term` with no `=> replacement` matched against a bullet stops the
export and names the offending bullet.

A single flat file rather than a `redact:` list in each role's frontmatter is
a deliberate deviation from the original plan: `split_frontmatter` parses flat
`key: value` scalars only and is shared with `check_manifest.py`, so a nested
YAML list could not be represented there without changing a parser three other
checks depend on.

**Staleness.** The generated `cv.md` carries, in an HTML comment, a SHA-256 over
the extracted live bullet texts, concatenated in the order `load_entries`
returns them (file path, not the start-descending order used to render roles) —
any deterministic order works, since the digest only needs to detect drift, not
to be read. `export_cv_md.py --check` recomputes it from `master/` and exits
nonzero on mismatch or on a missing comment.

## Component 2 — `scripts/check_redactions.py`

Loads the same `master/redactions.md` list and flags any occurrence of a
declared term in `library/*/draft.md`, along with cover letters and outreach
emails in the same directory. A draft may name a withheld term only after the
user decides to, so the check reports rather than rewrites, and its findings
carry into the review record. This closes the same hole for real resumes, which
exists today independent of career-ops.

## Component 3 — `scripts/import_job.py`

Takes a career-ops report number, reads `reports/NNN-{company}-{date}.md` and
the saved `jds/{company}-{role-slug}.md`, and writes
`library/<YYYY-MM-DD>-<company>-<role-slug>/job.md` in the format
`tailor-resume` already reads: an H1 provenance line, then the raw posting.

```
# Initech — Platform Engineering (Austin, TX). Captured 2026-08-05
  from career-ops report 012 (score 4.3), jds/initech-platform.md.
```

Refuses to run when `export_cv_md.py --check` reports drift: a score computed
against a stale `cv.md` is not evidence about the current master. Refuses to
overwrite an existing library directory. The evaluation report itself stays in
career-ops; only the pointer crosses.

Both this script and `export_cv_md.py` locate career-ops through one setting: a
`--career-ops` flag, falling back to the `CAREER_OPS_ROOT` environment variable,
falling back to `~/Projects/career-ops`. Neither script writes anywhere in
career-ops except `cv.md`.

## Component 4 — `plugin/skills/batch-tailor`

Tailors many jobs concurrently, batching every question to the user.

One subagent per job, each owning exactly one `library/<slug>/` directory. That
ownership is what makes the fan-out safe: no two agents write the same file, so
there is no locking anywhere in this design.

```
 round 1  ├─ fan-out: N agents │ capture → requirements → match → return gaps
          ├─ BARRIER: merge + dedup gaps across all N jobs
          │            ask the user once  →  build-master (serial, main agent)
          ├─ fan-out: resume each agent │ draft.md + sources.json
          ├─ fan-out: N reviewers        │ review.json
          └─ BARRIER: route findings ─ fact? → question queue
                                     ─ style? → preferences/
                                     ─ ambiguous? → ask, never guess
 round 2  └─ re-draft and re-review only the jobs whose citations changed
```

**Subagents never write to `master/`.** Invariant 1 makes `build-master` the
only writer, and invariant 3 makes bullet IDs append-only: two subagents
concurrently allocating `nw.b13` would corrupt the ID space silently and make
every later `sources.json` citing it ambiguous. Gap answers are collected by the
main agent and written by one serial `build-master` pass at a barrier.

**Two question waves, not one.** Gaps surface during matching, and again during
review — a reviewer finding is frequently a fact question. Both are barriers.
Findings are routed by the table in `AGENTS.md`: how it reads goes to
`preferences/`, what is true goes to `build-master`, and ambiguous findings are
asked rather than guessed.

**Dedup is the payoff.** Six postings asking about Kubernetes is one question
and one `build-master` write. The same holds for review findings that appear
across every draft at once.

**Agents are resumed, not respawned.** After each barrier the main agent
continues each subagent with `SendMessage`, preserving the context in which it
already read the JD and matched requirements.

**Termination.** A round producing no new fact questions ends the batch. Rounds
are capped at 2; anything unresolved is reported as an open gap rather than
looped on.

**Entry point.** `/resume-assistant:batch-tailor` over a list of library slugs,
or pulled from the career-ops tracker above a score threshold, following
`batch-tailor.mjs`'s `--min-score` idea.

Per-draft `check_provenance.py`, `check_hard_rules.py`, and
`keyword_coverage.py` run inside each subagent, unchanged. Batching changes who
asks the questions, never what is enforced.

## Failure modes

| Failure | Handling |
|---|---|
| Stale `cv.md` | Hash mismatch; `import_job.py` refuses |
| Undeclared sensitive term | Export exits nonzero, names the bullet |
| Subagent dies mid-batch | One partial `library/<slug>/`, detectable by shape, resumable; no sibling affected |
| Concurrent `master/` writes | Impossible: writes only at barriers, only in the main agent, only serial |
| Gap answer retires a cited bullet | `check_provenance.py` rejects it; round 2 re-drafts that job |
| User declines a gap question | Recorded as a non-answer in `master/` so the next batch does not re-ask |
| Upstream changes `jds/` naming or `cv.md` format | Both scripts assert the shapes they depend on and fail loudly naming the upstream file |

Nothing is pinned against upstream, and breakage is visible rather than silent.
The alternative is importing garbage without noticing.

## Testing

Deterministic pieces get unit tests against an invented persona, never real
data, per invariant 7:

- `export_cv_md.py` — prose excluded; `## Retired` excluded; `known-gaps.md`
  never read; `(YYYY)` stripped; `**Scope boundary:**` retained; redaction
  applied; undeclared term exits nonzero; `--check` detects drift.
- `check_redactions.py` — flags an undeclared term in a draft.
- `import_job.py` — fixture report and JD produce the expected `job.md`; stale
  CV refused; existing directory refused.

The batch loop's judgment — is this finding fact or style? — belongs in
`evals/`. Its mechanics — gap dedup grouping and round termination — live in
`resumelib/` as plain functions with unit tests, keeping the skill file thin.
Invariant 5: if it can be parsed, it is not a judgement call.

Existing gates apply: `python3 -m unittest discover -s tests` and
`python3 scripts/check_manifest.py plugin`, which the new skill must be
registered in.

## Out of scope

- career-ops' CV, PDF, and cover-letter generation. `render-resume` and
  `write-cover-letter` have a provenance guarantee those lack.
- Relocating career-ops' tracker and reports into this repo via
  `CAREER_OPS_TRACKER` and `CAREER_OPS_REPORTS_DIR`. Considered and deferred:
  it would version the pass/no-pass history, but `cv.md`'s hardcoded path shows
  not every script honors relocation, and each release could add another.
  Revisit if the unversioned history proves to be a real loss.

## Ideas adopted from career-ops

- `config/cv-facts.json` and `verify-cv-facts.mjs` — an explicit allowlist of
  claimable metrics plus forbidden phrases. `sources.json` proves a bullet has a
  source; this catches numbers that drift within a sourced bullet. Not adopted
  here, but the closest thing to a genuine gap in this system.
- `modes/_writing.md`'s two-tier voice split — anti-slop rules bind all
  generated text, while conversational register applies only to letters and
  outreach, never to resume bullets. This repo splits style by decidability;
  splitting by artifact as well is worth doing now that three artifact types are
  generated from one style file.
- `check-liveness.mjs` — verify a posting is open before spending on it. Used
  through career-ops rather than reimplemented.
- `batch-tailor.mjs`'s `--min-score` gate and `agent-inbox.md`'s append-only
  queue of requests awaiting a human, both reflected in component 4.
