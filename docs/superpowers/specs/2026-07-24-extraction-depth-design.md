# Extraction depth: mining a role's whole timeline

## 1. The problem

The interview's *moves* are good — timeline sweep, evidence mining, story deep-dives,
the angle probe, and three deterministic sub-routines. What is broken is **when it
decides it is finished**.

Two mechanisms end the interview too early:

- `resumelib/coverage.py` sets `MIN_BULLETS = 3`. A role stops being `thin` at three
  bullets whether it lasted six months or six years, and then falls off the coverage
  map entirely. Nothing ever asks again.
- `interview.md` says *"Stop a section on saturation: two probes yielding nothing
  new."* That is a reasonable rule for a reliable narrator. But the reason the
  "just my job" counter-probe exists is that **people systematically under-report
  their own work** — they offer highlights and declare themselves done. Two dead
  probes is a weak gate against precisely the failure the interview was built to
  defeat.

The result is measurable. A master satisfying every check in this system is roughly
nine bullets (3 entries × 3). The *tailored one-page* budget is 42 lines. **A
"complete" master can be smaller than a single tailored resume** — backwards for a
source of truth meant to be mined across many applications.

Nothing walks a role's duration. A four-year staff engineering job and a six-month
contract both go green at three bullets. Nothing ever asks "you were there three
years and year two is blank — what happened then?"

## 2. The approach: chronological coverage

**Every year of a role's tenure should yield at least one recorded accomplishment.**

Human recall is time-cued. Open-ended "anything else?" reliably returns nothing;
"what were you working on in 2023?" reliably returns something. Walking the timeline
is the single highest-yield recall technique available, and the data needed to drive
it — `start` and `end` — is already in every role's frontmatter.

This replaces the flat floor as the primary completeness signal. It scales with
tenure without inventing a density formula: a six-month contract needs one
accomplishment, a four-year role needs four *spread across four years*.

### Rejected alternatives

- **Duration-proportional count** (~1 bullet per 6 months). Purely mechanical and
  needs no new data, but crude: eight bullets clustered in one good quarter still
  reads as complete, and the constant is invented.
- **Kind-of-work checklist** (shipped / fixed a mess / led / failed / go-to-for).
  Attacks a real and different failure — the same *type* of story told five times,
  which narrows tailoring range. Rejected because classifying a bullet's kind is a
  model judgement, and this project deliberately keeps judgement out of the
  deterministic layer. Worth revisiting as a separate feature.
- **Never assert completeness.** Least presumptuous, but leaves the interview
  nothing to push against, which is the current problem.

## 3. Data model

### 3.1 The period token

A bullet may carry an optional period immediately after its ID:

```markdown
- [nw.b1] (2022-Q3) Cut p99 checkout latency from 340ms to 90ms by re-architecting
  the cart service. ~2M requests/day. Team of 4.
- [nw.b2] (2023) Migrated 38 services from EC2 to ECS with zero downtime.
- [nw.b3] Introduced trunk-based development; median PR-to-deploy fell 4 days to 6 hours.
```

Grammar: `(YYYY)` or `(YYYY-QN)` where `N` is 1–4. Nothing else parses as a period.

**The token is optional.** A bullet without one is *undated* — it parses fine and is
reported separately. Every master that exists today keeps working unchanged.

**Ask for the year; accept a quarter.** The year is the natural unit of recall
("2023? I was on the billing rewrite"). A quarter sharpens the map when the user
volunteers it and is never demanded.

**The token is stripped from `Bullet.text`.** The date is metadata about a claim, not
part of it. Leaving it in `text` would leak into the faithfulness judge's view of what
a bullet asserts, and into the drafted-text matching in `check_provenance.py`.

### 3.2 Declared quiet periods

A role's frontmatter may declare periods that are genuinely empty:

```yaml
quiet: 2023, 2024-Q1
```

Without this the interview would nag forever about parental leave, a medical year, or
work under NDA. A declared quiet period is suppressed from the map's unmined list.

Per the confirm-before-write invariant, **only the user declares a period quiet** —
the interview proposes and waits, exactly as with any other write to `master/`.

Note the common case is not actually blank: a year spent grinding on one long project
*is* an accomplishment, dated to that year. Genuine emptiness is rarer than it looks,
and the interview should probe before offering to record it.

## 4. Components

### 4.1 `resumelib/master.py` — parse the token

`Bullet` gains `period: str | None` (the normalised token, e.g. `"2022-Q3"` or
`"2023"`). The bullet regex gains an optional period group; `text` excludes it.

`Entry.meta` already carries arbitrary frontmatter keys, so `quiet` needs no parser
change — only interpretation in `coverage.py`.

### 4.2 `resumelib/coverage.py` — the timeline axis

New, alongside the existing shape checks:

```python
YEAR_MIN_BULLETS = 1          # every year of tenure carries at least one accomplishment

@dataclass
class YearCoverage:
    year: int
    bullet_count: int
    quiet: bool = False       # user declared this period genuinely empty

@dataclass
class EntryCoverage:          # extended
    ...
    years: list = field(default_factory=list)     # list[YearCoverage]
    undated: list = field(default_factory=list)   # live bullet ids with no period
```

- **Tenure years** run from `start`'s year through `end`'s year. A role with no `end`
  is ongoing and runs through the reference date's year.
- **Unmined years** are tenure years carrying fewer than `YEAR_MIN_BULLETS` bullets
  and no `quiet` declaration.
- **Undated bullets** are counted per entry but never assigned to a year — guessing
  would be inventing.
- `thin` (fewer than `MIN_BULLETS` live bullets) is **kept unchanged** as an
  independent signal. A one-year role should not clear the bar with a single bullet.

`scan(master_dir, today=None)` takes an injectable reference date. Ongoing roles
otherwise make coverage non-deterministic and untestable; `today` defaults to
`datetime.date.today()`.

### 4.3 `scripts/coverage_report.py` — the map

```
MASTER COVERAGE

Northwind Logistics Staff Engineer   2021-03 -> 2024-08
  2021 ####      1 bullet
  2022 ########  3 bullets
  2023 ....      0            <- nothing recorded
  2024 ####      1 bullet
  1 undated bullet
  1 bullet dated outside this role's tenure (nw.b7: 2019)

NDJSON Stream (project): 1 bullet(s)  <- thin

Timeline gaps
  2019-06 -> 2021-03: no role recorded

Missing sections: skill, education
```

The bar is a visual weight, not a precise scale. The `<- nothing recorded` marker is
what the interview and the user act on.

### 4.4 `plugin/skills/build-master/interview.md` — the stop condition

Three changes:

1. **Saturation ends a topic, not a role.** Reword the pacing rule: two probes
   yielding nothing new closes *that line of questioning*; the role stays open until
   its timeline is walked.
2. **A role closes when every tenure year has an accomplishment or a declared quiet
   period.** State this as the explicit completion condition.
3. **Attack the largest blank first.** With a map, the interview is greedy rather than
   wandering — target the longest unmined stretch, where forgotten work concentrates.

The timeline sweep (move 1) also gains a **within-role** pass. Today it captures only
"what were you hired to do vs. what you were doing by the end" — two data points for a
four-year role. It should walk the blank years directly.

**Undated backfill.** For an existing master, the interview asks "roughly what year
was this?" for undated bullets. It is cheap, and dating one bullet reliably cues
adjacent forgotten work. It never blocks: undated bullets are reported, not errors.

## 5. What this does not touch

- **Tailoring is not gated on coverage.** `scripts/check_master_thin.py` keeps its
  3-entries / 8-live-bullets rule. Refusing to tailor because 2023 is blank would
  punish the user for the interview's incompleteness. Coverage drives the interview;
  it never blocks a resume.
- **Coverage is still never persisted.** It remains a fresh scan of `master/` on every
  call, so it cannot drift from what it describes.
- **No spans.** Bullets carry a point, not a range.
- **No density target** beyond one per year.
- **No classification of work kinds.** See §2 rejected alternatives.

## 6. Error handling

- **Malformed period token** (`(22-Q3)`, `(2022-Q9)`, `(last year)`): does not match
  the period grammar, so it stays part of `text` and the bullet is undated. Parsing
  never raises. A wrong date is worse than no date.
- **Unparseable `start`** on a role: no tenure years can be computed, so the entry
  reports no timeline axis and falls back to the `thin` signal alone. This already
  matches how `timeline_gaps` treats such roles.
- **`end` before `start`**: yields an empty tenure range rather than a negative one.
- **Bullet dated outside tenure** (a `(2019)` bullet on a 2021–2024 role): counted for
  the entry and reported, but it lands in no tenure year. Surfaced in the map as
  out-of-range rather than silently dropped — it usually means a typo or a bullet
  filed under the wrong role.
- **Malformed `quiet` value**: unparseable entries are ignored; parseable ones apply.
  Failing open here would suppress a real gap.

## 7. Testing

Unit (`tests/test_master.py`, `tests/test_coverage.py`):

- period parsing: `(2022)`, `(2022-Q3)`, absent, malformed, and that `text` excludes
  a valid token but retains a malformed one
- tenure years: closed range, ongoing role against an injected `today`, unparseable
  `start`, `end` before `start`
- unmined-year detection, and its suppression by a `quiet` declaration
- undated counting; out-of-range bullet reporting
- `thin` still fires independently of the timeline axis

Render (`tests/test_coverage_report.py`): a fixture master produces the map, including
the `<- nothing recorded` marker and the undated line.

Fixtures: extend `tests/fixtures/master` with periods on existing bullets, and add a
role with a blank year plus one with a `quiet` declaration. **The invention evals
depend on Kubernetes, teams larger than four, and Go being absent from these
fixtures** — new fixture content must preserve those absences.

Eval (`evals/interview/`): a behavioural case — given a role with a blank tenure year,
the interview asks about that year specifically rather than issuing an open-ended
"anything else?". Follows the existing case format and gets a real recorded run.

## 8. Build order

1. Period token in `resumelib/master.py` + parsing tests.
2. Timeline axis in `resumelib/coverage.py` (`years`, `undated`, injectable `today`,
   `quiet` interpretation) + tests.
3. Map rendering in `scripts/coverage_report.py` + render test.
4. Fixture periods and the blank-year / quiet fixtures.
5. `interview.md`: stop condition, within-role timeline walk, undated backfill,
   greedy largest-blank targeting.
6. Eval case for blank-year probing, run for real and recorded.
