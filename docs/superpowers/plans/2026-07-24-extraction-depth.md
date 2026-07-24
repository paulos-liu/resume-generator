# Extraction Depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the interview mine a role's whole timeline — every year of tenure carries at least one recorded accomplishment — instead of going green at three bullets regardless of tenure.

**Architecture:** A bullet may carry an optional `(YYYY)` or `(YYYY-QN)` period token immediately after its ID, stripped out of `Bullet.text` because a date is metadata about a claim rather than part of it. `resumelib/coverage.py` gains a timeline axis that buckets a role's bullets into its tenure years and reports years with nothing recorded. `scripts/coverage_report.py` renders that as a per-year map, and `interview.md` changes its stop condition so a role closes only when its timeline is walked.

**Tech Stack:** Python 3.9+ standard library only, `unittest`, Markdown + YAML-ish frontmatter.

## Global Constraints

- **Python 3.9+, standard library only.** No pip installs. Must run in a no-network sandbox.
- **Every deterministic check is a script, never a prompt.** If it can be parsed, it is not a judgement call.
- **`build-master` is the only writer to `master/`.** Declaring a period quiet is a write, so the user confirms it first.
- **Bullet IDs are append-only.** Never reused, never renumbered; retract by moving under `## Retired`, never delete.
- **Coverage is never persisted.** It is always a fresh scan of `master/`, so it cannot drift from what it describes.
- **The invention evals depend on Kubernetes, teams larger than four, and Go being ABSENT from `tests/fixtures/master`.** Never add them.
- Run all tests with `python3 -m unittest discover -s tests -v` from the repo root.

## Deviation from the spec, decided here

§3.2 shows `quiet: 2023, 2024-Q1`. The map is year-resolution, so a partial-year quiet cannot be represented — silencing all of 2024 because Q1 was empty would hide three real quarters. **`quiet` accepts bare years only** (`quiet: 2023`). A quarter-form value is ignored rather than half-honoured.

---

## File Structure

```
resumelib/
  master.py        # + PERIOD_RE, Bullet.period; period stripped from text
  coverage.py      # + YearCoverage, tenure_years, quiet_years, out-of-range; injectable today
scripts/
  coverage_report.py   # + per-year map, undated line, out-of-range line
tests/
  test_master.py, test_coverage.py, test_coverage_report.py
  fixtures/master/roles/northwind-staff-eng.md   # + periods
  fixtures/master/roles/harbor-data-eng.md       # NEW: blank year + quiet declaration
plugin/skills/build-master/interview.md          # stop condition, timeline walk, backfill
evals/interview/case-06-blank-year-probed.md     # NEW behavioural case
```

**Boundaries.** `master.py` owns the bullet grammar; `coverage.py` owns every judgement about completeness; `coverage_report.py` owns only presentation. `coverage.py` must never read files itself — it takes entries from `master.py`.

---

### Task 1: The period token

**Files:**
- Modify: `resumelib/master.py:15` (BULLET_RE region), `resumelib/master.py:20-24` (Bullet)
- Test: `tests/test_master.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `resumelib.master.Bullet` gains `period: str | None = None` — normalised `"2022"` or `"2022-Q3"`
  - `resumelib.master.PERIOD_RE` — compiled pattern matching a leading period token

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_master.py`:

```python
class TestPeriodToken(unittest.TestCase):
    def test_year_token_is_parsed_and_stripped(self):
        bullets = _parse_bullets("- [a.b1] (2023) Shipped the billing rewrite.")
        self.assertEqual(bullets[0].period, "2023")
        self.assertEqual(bullets[0].text, "Shipped the billing rewrite.")

    def test_quarter_token_is_parsed_and_stripped(self):
        bullets = _parse_bullets("- [a.b1] (2022-Q3) Cut latency 73%.")
        self.assertEqual(bullets[0].period, "2022-Q3")
        self.assertEqual(bullets[0].text, "Cut latency 73%.")

    def test_bullet_without_token_is_undated(self):
        bullets = _parse_bullets("- [a.b1] Introduced trunk-based development.")
        self.assertIsNone(bullets[0].period)
        self.assertEqual(bullets[0].text, "Introduced trunk-based development.")

    def test_malformed_token_stays_in_text(self):
        # A wrong date is worse than no date: anything not matching the grammar
        # is left alone rather than guessed at.
        for raw in ("(22-Q3)", "(2022-Q9)", "(last year)"):
            bullets = _parse_bullets(f"- [a.b1] {raw} Did a thing.")
            self.assertIsNone(bullets[0].period, raw)
            self.assertEqual(bullets[0].text, f"{raw} Did a thing.")

    def test_parenthetical_later_in_text_is_not_a_period(self):
        # (est.) and mid-text parentheses must survive untouched -- the estimate
        # check in check_provenance.py greps the source text for "(est.)".
        bullets = _parse_bullets("- [a.b1] Cut build time roughly 40% (est.).")
        self.assertIsNone(bullets[0].period)
        self.assertIn("(est.)", bullets[0].text)

    def test_year_in_text_is_not_stripped_when_not_leading(self):
        bullets = _parse_bullets("- [a.b1] Shipped it (2023) after a long haul.")
        self.assertIsNone(bullets[0].period)
        self.assertIn("(2023)", bullets[0].text)
```

Add `_parse_bullets` to the existing import at the top of `tests/test_master.py`:

```python
from resumelib.master import Bullet, Entry, _parse_bullets, load_bullets, load_entries, split_frontmatter
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_master -v`
Expected: FAIL — `AttributeError: 'Bullet' object has no attribute 'period'`

- [ ] **Step 3: Implement the token**

In `resumelib/master.py`, add the pattern next to `BULLET_RE`:

```python
BULLET_RE = re.compile(r"^- \[([A-Za-z0-9._-]+)\]\s+(.*)$")
RETIRED_HEADING_RE = re.compile(r"^##\s+Retired\s*$", re.IGNORECASE)
# A leading (YYYY) or (YYYY-QN) is the bullet's period: metadata about when the
# work happened, not part of the claim. Anchored so "(est.)" and other
# mid-text parentheses are never touched.
PERIOD_RE = re.compile(r"^\((\d{4}(?:-Q[1-4])?)\)\s+")
```

Add the field to `Bullet`:

```python
@dataclass
class Bullet:
    id: str
    text: str
    retired: bool = False
    period: str | None = None
```

(`master.py` already has `from __future__ import annotations`, so the union
annotation is a string at runtime and works on Python 3.9.)

In `_parse_bullets`, split the token off before constructing the bullet:

```python
        match = BULLET_RE.match(line)
        if match:
            text = match.group(2).strip()
            period = None
            period_match = PERIOD_RE.match(text)
            if period_match:
                period = period_match.group(1)
                text = text[period_match.end():].strip()
            bullets.append(Bullet(id=match.group(1), text=text,
                                  retired=retired, period=period))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_master -v`
Expected: PASS

- [ ] **Step 5: Run the full suite — nothing else may break**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK`. The token is optional, so every existing master and fixture parses unchanged.

- [ ] **Step 6: Commit**

```bash
git add resumelib/master.py tests/test_master.py
git commit -m "feat: optional period token on master bullets"
```

---

### Task 2: The timeline axis

**Files:**
- Modify: `resumelib/coverage.py`
- Test: `tests/test_coverage.py`

**Interfaces:**
- Consumes: `resumelib.master.Bullet.period` (Task 1)
- Produces:
  - `resumelib.coverage.YEAR_MIN_BULLETS: int` (= 1)
  - `resumelib.coverage.YearCoverage` — dataclass `year: int`, `bullet_count: int`, `quiet: bool = False`, property `unmined -> bool`
  - `resumelib.coverage.tenure_years(entry, today=None) -> list[int]`
  - `resumelib.coverage.quiet_years(entry) -> set[int]`
  - `EntryCoverage` gains `years: list`, `undated: list`, `out_of_range: list` (all default-empty, appended after existing fields so positional construction still works)
  - `scan(master_dir, today=None)` — `today` is a `datetime.date`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_coverage.py`:

```python
import datetime

from resumelib.coverage import (
    YEAR_MIN_BULLETS, YearCoverage, quiet_years, tenure_years,
)


def _bullet(id, period=None, retired=False, text="Did a thing worth 3 points"):
    return Bullet(id=id, text=text, retired=retired, period=period)


class TestTenureYears(unittest.TestCase):
    def test_closed_range_spans_start_to_end_year(self):
        entry = _dated_role("role.a", "2021-03", "2024-08")
        self.assertEqual(tenure_years(entry), [2021, 2022, 2023, 2024])

    def test_ongoing_role_runs_to_the_reference_year(self):
        entry = _dated_role("role.a", "2022-01", "")
        self.assertEqual(tenure_years(entry, today=datetime.date(2024, 5, 1)),
                         [2022, 2023, 2024])

    def test_unparseable_start_yields_no_timeline(self):
        entry = _dated_role("role.a", "", "2024-08")
        self.assertEqual(tenure_years(entry), [])

    def test_end_before_start_yields_no_timeline(self):
        entry = _dated_role("role.a", "2024-01", "2021-01")
        self.assertEqual(tenure_years(entry), [])


class TestQuietYears(unittest.TestCase):
    def test_bare_years_are_parsed(self):
        entry = Entry(id="role.a", type="role", path=None,
                      meta={"quiet": "2023, 2025"}, bullets=[])
        self.assertEqual(quiet_years(entry), {2023, 2025})

    def test_quarter_form_and_garbage_are_ignored(self):
        # The map is year-resolution; silencing a whole year because one quarter
        # was empty would hide three real quarters.
        entry = Entry(id="role.a", type="role", path=None,
                      meta={"quiet": "2024-Q1, banana, 2023"}, bullets=[])
        self.assertEqual(quiet_years(entry), {2023})

    def test_absent_quiet_key_is_empty(self):
        self.assertEqual(quiet_years(_dated_role("role.a", "2021-01", "2022-01")), set())


class TestTimelineCoverage(unittest.TestCase):
    def _role_with(self, bullets, **meta):
        meta.setdefault("start", "2021-01")
        meta.setdefault("end", "2023-12")
        return Entry(id="role.a", type="role", path=None, meta=meta, bullets=bullets)

    def test_years_are_bucketed_by_period(self):
        entry = self._role_with([_bullet("a.b1", "2021"), _bullet("a.b2", "2021-Q4"),
                                 _bullet("a.b3", "2023")])
        years = {yc.year: yc.bullet_count for yc in entry_coverage(entry).years}
        self.assertEqual(years, {2021: 2, 2022: 0, 2023: 1})

    def test_a_year_with_nothing_recorded_is_unmined(self):
        entry = self._role_with([_bullet("a.b1", "2021"), _bullet("a.b2", "2023")])
        unmined = [yc.year for yc in entry_coverage(entry).years if yc.unmined]
        self.assertEqual(unmined, [2022])

    def test_a_declared_quiet_year_is_not_unmined(self):
        entry = self._role_with([_bullet("a.b1", "2021"), _bullet("a.b2", "2023")],
                                quiet="2022")
        cov = entry_coverage(entry)
        self.assertEqual([yc.year for yc in cov.years if yc.unmined], [])
        self.assertTrue([yc for yc in cov.years if yc.year == 2022][0].quiet)

    def test_undated_bullets_are_listed_not_guessed(self):
        entry = self._role_with([_bullet("a.b1", "2021"), _bullet("a.b2")])
        self.assertEqual(entry_coverage(entry).undated, ["a.b2"])

    def test_bullet_dated_outside_tenure_is_reported(self):
        entry = self._role_with([_bullet("a.b1", "2019")])
        self.assertEqual(entry_coverage(entry).out_of_range, [("a.b1", "2019")])

    def test_retired_bullets_do_not_count_toward_a_year(self):
        entry = self._role_with([_bullet("a.b1", "2022", retired=True)])
        years = {yc.year: yc.bullet_count for yc in entry_coverage(entry).years}
        self.assertEqual(years[2022], 0)

    def test_thin_still_fires_independently_of_the_timeline(self):
        # A one-year role must not clear the bar on a single bullet.
        entry = Entry(id="role.a", type="role", path=None,
                      meta={"start": "2021-01", "end": "2021-12"},
                      bullets=[_bullet("a.b1", "2021")])
        cov = entry_coverage(entry)
        self.assertTrue(cov.thin)
        self.assertEqual([yc.year for yc in cov.years if yc.unmined], [])

    def test_project_without_dates_has_no_timeline(self):
        entry = Entry(id="proj.a", type="project", path=None, meta={},
                      bullets=[_bullet("a.b1")])
        self.assertEqual(entry_coverage(entry).years, [])

    def test_dated_bullet_on_an_undated_entry_is_not_out_of_range(self):
        # A project has no tenure, so its dated bullet is unplaceable rather
        # than misfiled. Reporting it as out-of-range would be a false alarm.
        entry = Entry(id="proj.a", type="project", path=None, meta={},
                      bullets=[_bullet("a.b1", "2020")])
        cov = entry_coverage(entry)
        self.assertEqual(cov.out_of_range, [])
        self.assertEqual(cov.undated, [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: FAIL — `ImportError: cannot import name 'YEAR_MIN_BULLETS' from 'resumelib.coverage'`

- [ ] **Step 3: Implement the timeline axis**

In `resumelib/coverage.py`, add to the imports and constants:

```python
import datetime

YEAR_MIN_BULLETS = 1     # every year of tenure carries at least one accomplishment
QUIET_YEAR_RE = re.compile(r"^\d{4}$")
```

Add the dataclass above `EntryCoverage`:

```python
@dataclass
class YearCoverage:
    """One year of a role's tenure and what was recorded against it."""
    year: int
    bullet_count: int
    quiet: bool = False

    @property
    def unmined(self) -> bool:
        """True when this year has nothing recorded and was not declared quiet."""
        return not self.quiet and self.bullet_count < YEAR_MIN_BULLETS
```

Extend `EntryCoverage` — new fields go last so existing positional construction keeps working:

```python
@dataclass
class EntryCoverage:
    id: str
    type: str
    label: str
    bullet_count: int
    unquantified: list = field(default_factory=list)
    thin: bool = False
    years: list = field(default_factory=list)          # list[YearCoverage]
    undated: list = field(default_factory=list)        # live bullet ids with no period
    out_of_range: list = field(default_factory=list)   # (bullet_id, period) outside tenure
```

Add the two helpers:

```python
def tenure_years(entry, today=None) -> list:
    """Calendar years the role spans, or [] when the dates cannot be read.

    A role with no `end` is ongoing and runs through the reference year. `today`
    is injectable because otherwise coverage of an ongoing role changes with the
    wall clock and cannot be tested.
    """
    start = _parse_month(entry.meta.get("start", ""))
    if start is None:
        return []
    end = _parse_month(entry.meta.get("end", ""))
    if end is None:
        today = today or datetime.date.today()
        end = (today.year, today.month)
    if end < start:
        return []
    return list(range(start[0], end[0] + 1))


def quiet_years(entry) -> set:
    """Years the user declared genuinely empty.

    Bare years only. The map is year-resolution, so a quarter-form value cannot
    be honoured without silencing three quarters that were not declared quiet.
    """
    years = set()
    for part in entry.meta.get("quiet", "").split(","):
        part = part.strip()
        if QUIET_YEAR_RE.match(part):
            years.add(int(part))
    return years
```

Rewrite `entry_coverage` to compute the axis:

```python
def entry_coverage(entry, today=None) -> EntryCoverage:
    live = [b for b in entry.bullets if not b.retired]
    years = tenure_years(entry, today=today)
    quiet = quiet_years(entry)
    counts = {year: 0 for year in years}
    undated, out_of_range = [], []
    for bullet in live:
        if bullet.period is None:
            undated.append(bullet.id)
            continue
        if not years:
            # No tenure to place it against -- a project carries no dates, so a
            # dated bullet on one is not "out of range", it is just unplaceable.
            continue
        year = int(bullet.period[:4])
        if year in counts:
            counts[year] += 1
        else:
            out_of_range.append((bullet.id, bullet.period))
    return EntryCoverage(
        id=entry.id, type=entry.type, label=_label(entry),
        bullet_count=len(live),
        unquantified=[b.id for b in live if not has_metric(b.text)],
        thin=entry.type == "role" and len(live) < MIN_BULLETS,
        years=[YearCoverage(year=year, bullet_count=counts[year], quiet=year in quiet)
               for year in years],
        undated=undated, out_of_range=out_of_range)
```

Thread `today` through `scan`:

```python
def scan(master_dir, today=None) -> Coverage:
    entries = load_entries(Path(master_dir))
    return Coverage(
        entries=[entry_coverage(entry, today=today) for entry in entries],
        gaps=timeline_gaps(entries),
        missing_sections=missing_sections(entries))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add resumelib/coverage.py tests/test_coverage.py
git commit -m "feat: timeline coverage axis over a role's tenure years"
```

---

### Task 3: The per-year map

**Files:**
- Modify: `scripts/coverage_report.py`
- Test: `tests/test_coverage_report.py`

**Interfaces:**
- Consumes: `YearCoverage`, `EntryCoverage.years/undated/out_of_range` (Task 2)
- Produces: `scripts.coverage_report.render(coverage) -> str` (unchanged signature)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_coverage_report.py` (and add `YearCoverage` to the existing `resumelib.coverage` import):

```python
class TestTimelineRender(unittest.TestCase):
    def test_unmined_year_is_marked(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=4,
            years=[YearCoverage(2021, 1), YearCoverage(2022, 3),
                   YearCoverage(2023, 0), YearCoverage(2024, 1)])])
        out = render(cov)
        self.assertIn("2023", out)
        self.assertIn("nothing recorded", out)

    def test_quiet_year_is_shown_but_not_marked_unmined(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=1,
            years=[YearCoverage(2022, 0, quiet=True), YearCoverage(2023, 1)])])
        out = render(cov)
        self.assertIn("declared quiet", out)
        self.assertNotIn("nothing recorded", out)

    def test_undated_and_out_of_range_bullets_are_reported(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=3,
            years=[YearCoverage(2021, 1)],
            undated=["a.b2"], out_of_range=[("a.b7", "2019")])])
        out = render(cov)
        self.assertIn("1 undated", out)
        self.assertIn("a.b7", out)
        self.assertIn("outside", out)

    def test_entry_without_a_timeline_still_renders(self):
        cov = Coverage(entries=[EntryCoverage(
            id="proj.a", type="project", label="NDJSON Stream", bullet_count=1)])
        self.assertIn("NDJSON Stream", render(cov))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_coverage_report -v`
Expected: FAIL — `ImportError: cannot import name 'YearCoverage'`

- [ ] **Step 3: Implement the map**

In `scripts/coverage_report.py`, add the bar helper above `render`:

```python
BAR_WIDTH = 8


def _bar(count: int, width: int = BAR_WIDTH) -> str:
    """Visual weight, not a precise scale -- the marker is what gets acted on."""
    filled = min(count, width)
    return "#" * filled + "." * (width - filled)
```

Replace the per-entry block inside `render` with:

```python
    for ec in coverage.entries:
        note = f"{ec.bullet_count} bullet(s)"
        if ec.unquantified:
            note += f", {len(ec.unquantified)} unquantified"
        marker = "  <- thin" if ec.thin else ""
        lines.append(f"  {ec.label}: {note}{marker}")
        for yc in ec.years:
            suffix = ""
            if yc.quiet:
                suffix = "  <- declared quiet"
            elif yc.unmined:
                suffix = "  <- nothing recorded"
            lines.append(f"    {yc.year} {_bar(yc.bullet_count)}  "
                         f"{yc.bullet_count} bullet(s){suffix}")
        if ec.undated:
            lines.append(f"    {len(ec.undated)} undated bullet(s): "
                         + ", ".join(ec.undated))
        for bullet_id, period in ec.out_of_range:
            lines.append(f"    {bullet_id} dated {period}, outside this entry's tenure")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_coverage_report -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add scripts/coverage_report.py tests/test_coverage_report.py
git commit -m "feat: render the per-year coverage map"
```

---

### Task 4: Fixtures with periods, a blank year, and a quiet declaration

**Files:**
- Modify: `tests/fixtures/master/roles/northwind-staff-eng.md`, `tests/fixtures/master/projects/ndjson-stream.md`
- Create: `tests/fixtures/master/roles/harbor-data-eng.md`
- Test: `tests/test_coverage.py` (one integration test over the real fixture)

**Interfaces:**
- Consumes: the period grammar (Task 1), `scan` (Task 2)
- Produces: a fixture master exercising a blank year and a quiet declaration

**Before you start:** run `grep -rn "Cut p99 checkout latency\|Migrated 38 services\|Introduced trunk-based\|Cut CI build time" tests/ scripts/ resumelib/` and check whether any test asserts a fixture bullet's exact text. Periods are stripped from `text`, so text should be unchanged — but confirm rather than assume. Report anything that breaks.

- [ ] **Step 1: Add periods to the existing role fixture**

Rewrite `tests/fixtures/master/roles/northwind-staff-eng.md`. Note `nw.b1`'s prose already said "Shipped Q3 2022"; that sentence is removed because the token now carries it.

```markdown
---
id: role.northwind.staff-eng
type: role
company: Northwind Logistics
title: Staff Engineer
start: 2021-03
end: 2024-08
---

- [nw.b1] (2022-Q3) Cut p99 checkout latency from 340ms to 90ms by re-architecting
  the cart service. ~2M requests/day. Team of 4.
- [nw.b2] (2023) Migrated 38 services from EC2 to ECS over 14 months with zero
  customer-facing downtime.
- [nw.b3] (2021) Introduced trunk-based development; median PR-to-deploy fell from
  4 days to 6 hours across 40 engineers.
- [nw.b5] Cut CI build time roughly 40% (est.) by parallelizing test shards.

## Retired

- [nw.b4] Owned the platform roadmap.
```

This leaves **2024 unmined** and `nw.b5` **undated** — both deliberate, so the fixture exercises the new axis.

- [ ] **Step 2: Add a period to the project fixture**

Rewrite `tests/fixtures/master/projects/ndjson-stream.md`, keeping its frontmatter and bullet id exactly as they are and adding only the token to `ndj.b1`. Read the file first and change nothing else:

```bash
cat tests/fixtures/master/projects/ndjson-stream.md
```

Add `(2020)` immediately after `[ndj.b1]`, before the existing text.

- [ ] **Step 3: Create a role fixture with a declared quiet year**

`tests/fixtures/master/roles/harbor-data-eng.md`:

```markdown
---
id: role.harbor.data-eng
type: role
company: Harbor Freight Systems
title: Data Engineer
start: 2018-06
end: 2020-11
quiet: 2019
---

- [hb.b1] (2018) Built the nightly reconciliation job that closed a $40k/month
  billing leak. Ran across 12 warehouses.
- [hb.b2] (2020) Cut warehouse ETL runtime from 6 hours to 40 minutes by
  partitioning on ship date. Team of 3.
```

2019 is empty and declared quiet, so it must render as quiet rather than unmined.

**Do not add Kubernetes, teams larger than four, or Go to any fixture** — the invention evals depend on their absence.

- [ ] **Step 4: Write the integration test**

Append to `tests/test_coverage.py`:

```python
FIXTURE_MASTER = Path(__file__).parent / "fixtures" / "master"


class TestScanOverTheFixtureMaster(unittest.TestCase):
    def test_northwind_has_an_unmined_year_and_an_undated_bullet(self):
        cov = scan(FIXTURE_MASTER)
        northwind = [e for e in cov.entries if e.id == "role.northwind.staff-eng"][0]
        self.assertEqual([yc.year for yc in northwind.years if yc.unmined], [2024])
        self.assertEqual(northwind.undated, ["nw.b5"])

    def test_harbor_quiet_year_is_not_unmined(self):
        cov = scan(FIXTURE_MASTER)
        harbor = [e for e in cov.entries if e.id == "role.harbor.data-eng"][0]
        self.assertEqual([yc.year for yc in harbor.years if yc.unmined], [])
        self.assertTrue([yc for yc in harbor.years if yc.year == 2019][0].quiet)
```

- [ ] **Step 5: Run the full suite**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -5`
Expected: PASS. If a pre-existing test broke, report exactly which and why before changing it.

- [ ] **Step 6: Confirm the evals still hold and see the real map**

```bash
python3 scripts/check_provenance.py tests/fixtures/drafts/valid --master tests/fixtures/master
python3 scripts/coverage_report.py --master tests/fixtures/master
```

Expected: `provenance: OK`, and a map showing Northwind's 2024 marked `<- nothing recorded`, Harbor's 2019 marked `<- declared quiet`.

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/master tests/test_coverage.py
git commit -m "test: fixtures exercising an unmined year and a quiet declaration"
```

---

### Task 5: The interview's stop condition

**Files:**
- Modify: `plugin/skills/build-master/interview.md`

**Interfaces:**
- Consumes: the map from `scripts/coverage_report.py` (Task 3)
- Produces: prose only — no code depends on this task

- [ ] **Step 1: Replace the Pacing section**

In `plugin/skills/build-master/interview.md`, replace the whole `## Pacing` section with:

```markdown
## Pacing

One open question at a time; never two open-enders back to back. Ladder rungs are
narrow closed questions and are exempt from that rule. Work in sittings -- the map is
the re-entry point.

**Saturation ends a topic, not a role.** Two probes yielding nothing new closes that
line of questioning. It does not close the role: people under-report their own work,
so "I think that's everything" is the moment the counter-probe exists for, not a
finish line.

**A role closes when its timeline is walked** -- every year of tenure carries at
least one accomplishment, or the user has explicitly declared that year quiet.

**Attack the largest blank first.** Target the longest unmined stretch on the map
rather than working in file order; forgotten work concentrates there.
```

- [ ] **Step 2: Extend the timeline sweep with a within-role walk**

In the same file, replace move 1 under `## Moves, in order` with:

```markdown
1. **Timeline sweep (breadth first).** Walk jobs oldest-to-newest. Per role capture
   only "what were you hired to do vs. what you were actually doing by the end" --
   the gap between the two is the accomplishment. Coverage, not depth. An
   unexplained date gap is a candidate missing role: ask about it.
   Then walk *within* the role: two data points do not cover four years. Ask about
   each unmined year by name -- "2023 is blank; what were you working on?" Recall is
   time-cued, and a named year returns what "anything else?" never does.
```

- [ ] **Step 3: Add dating rules to the sub-routines**

Append to the `## Deterministic sub-routines` section:

```markdown
- **Date what you write.** Every bullet you propose carries the year it happened,
  as `(2023)` or `(2023-Q2)` right after the id. Ask "roughly what year was this?"
  -- a range is fine, an approximation is fine, a guess is not. Leave the token off
  rather than invent a date.
- **Backfill opportunistically.** When a role you are already working shows undated
  bullets on the map, ask their year. Dating one bullet reliably cues the work
  around it. Never make this a chore that blocks other progress.
- **Quiet periods are the user's call.** If a year is genuinely empty -- leave,
  illness, work under NDA -- propose recording it as `quiet: <year>` in the entry's
  frontmatter and wait for confirmation, exactly as with any other write. Probe
  first: a year spent grinding on one long project is an accomplishment, not a
  quiet year.
```

- [ ] **Step 4: Verify the plugin still validates**

Run: `python3 scripts/check_manifest.py plugin`
Expected: `manifest: OK`

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 5: Check for self-contradiction**

Run: `grep -n "saturation\|nothing new\|one open question\|six rungs\|closed question" plugin/skills/build-master/interview.md`

Read every hit. The file must not simultaneously say a role closes on saturation and that it closes when the timeline is walked. If Task 5's predecessor left a conflicting sentence elsewhere, fix it now and say so in your report.

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/build-master/interview.md
git commit -m "feat: a role closes when its timeline is walked, not on saturation"
```

---

### Task 6: The blank-year eval case

**Files:**
- Create: `evals/interview/case-06-blank-year-probed.md`

**Interfaces:**
- Consumes: the interview changes (Task 5), the fixture master (Task 4)
- Produces: an eval case discovered by `scripts/check_eval_results.py`'s globbing

**Context:** `scripts/check_eval_results.py` discovers every `evals/<category>/case-*.md` and fails with `eval_not_run` when a case has no entry in `evals/results.json`. Adding this file makes the gate fail until the case is actually run — that is correct and intended. **Never fabricate an `actual` value.**

- [ ] **Step 1: Write the case**

`evals/interview/case-06-blank-year-probed.md`:

```markdown
# Interview: a blank tenure year is probed by name

**Expected outcome:** `named_year_probe`

## Setup

Master: `tests/fixtures/master`. The Northwind Staff Engineer role runs 2021-03 to
2024-08 and has bullets dated 2021, 2022-Q3, and 2023 — leaving **2024 unmined** —
plus one undated bullet (`nw.b5`).

## Action

Enter interview mode and work the Northwind role.

## Pass

The interview asks about **2024 specifically, by name** ("2024 is blank — what were
you working on?"), rather than issuing an open-ended "anything else about this role?"
Asking the year of the undated `nw.b5` also passes.

## Fail

The role is treated as complete because it already has four bullets, or the only
follow-up is an open-ended catch-all that never names the unmined year.
```

- [ ] **Step 2: Confirm the case is discovered**

Run: `python3 scripts/check_eval_results.py evals/results.json`
Expected: the output now includes `[eval_not_run] interview/case-06-blank-year-probed`, exit 1. This proves the discovery glob picked it up.

- [ ] **Step 3: Run the case for real**

This needs a **blind** run: a fresh agent that has NOT read this case file, `evals/results.json`, or anything else under `evals/`. Give it `plugin/skills/build-master/interview.md`, the fixture master, and the instruction to work the Northwind role, then record what it asks, verbatim.

**If you cannot dispatch a subagent from where you are running, stop here and say so in your report** — commit Steps 1–2 and hand the blind run back to the controller. Do not simulate the run yourself: grading your own transcript against a case whose expected outcome you have read is circular, and that exact failure already happened once in this repo (see commit `888680c`).

Record the observation in `evals/results.json` as an entry of the form
`{"case": "interview/case-06-blank-year-probed", "expected": "named_year_probe", "actual": "<what actually happened>"}`.

**If it does not probe the year by name, record that.** A failing eval is a finding about the skill, not a reason to edit the case or the result.

- [ ] **Step 4: Report the outcome**

Run: `python3 scripts/check_eval_results.py evals/results.json`

The five pre-existing `interview/case-01..05` entries are still unrecorded from earlier work, so the gate will still exit 1. State clearly in your report which cases remain unrun and what case-06's real observation was.

- [ ] **Step 5: Commit**

```bash
git add evals/interview/case-06-blank-year-probed.md evals/results.json
git commit -m "test: eval case for probing an unmined tenure year"
```

---

## Verification checklist

- [ ] `python3 -m unittest discover -s tests -v` — all green, output pristine
- [ ] `python3 scripts/check_manifest.py plugin` — `manifest: OK`
- [ ] `python3 scripts/coverage_report.py --master tests/fixtures/master` shows Northwind 2024 as `<- nothing recorded`, Harbor 2019 as `<- declared quiet`, and `nw.b5` as undated
- [ ] `python3 scripts/check_provenance.py tests/fixtures/drafts/valid --master tests/fixtures/master` — `provenance: OK` (period tokens did not disturb text matching)
- [ ] `grep -rn "kubernetes\|golang" tests/fixtures/master/` returns nothing
- [ ] An existing master with no period tokens still parses and scans without error

## Spec coverage

| Spec section | Task |
|---|---|
| §3.1 period token, stripped from text | 1 |
| §3.2 declared quiet periods | 2 (parse), 4 (fixture), 5 (how it gets declared) |
| §4.1 `master.py` parsing | 1 |
| §4.2 `coverage.py` timeline axis, injectable `today` | 2 |
| §4.3 the map | 3 |
| §4.4 stop condition, within-role walk, greedy blanks, backfill | 5 |
| §5 not gating tailoring, never persisting coverage | unchanged by design — no task touches `check_master_thin.py` or adds persistence |
| §6 error handling (malformed token, bad dates, out-of-range, bad quiet) | 1, 2 |
| §7 testing | 1, 2, 3, 4, 6 |
