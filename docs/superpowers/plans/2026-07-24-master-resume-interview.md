# Master Resume Interview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a proactive, coverage-driven interview capability to `build-master` that guides users toward a robust master resume, backed by a deterministic coverage scan and checkpoint map.

**Architecture:** A new `resumelib/coverage.py` scores the master on breadth (role count, timeline gaps), depth (per-bullet metric presence), and section completeness — all by scanning `master/`, never persisting. `scripts/coverage_report.py` renders that scan as the checkpoint map. A new `plugin/skills/build-master/interview.md` holds the interview protocol (moves + three deterministic sub-routines + pacing); `build-master/SKILL.md` gains triggers and a pointer to it. Behavioural guarantees are covered by eval cases, deterministic scan logic by unit tests.

**Tech Stack:** Python 3 standard library only (no third-party deps); `unittest` via `python3 -m unittest`; Markdown skill/eval files.

## Global Constraints

- Python standard library only — no new dependencies. Scripts follow the repo pattern: a pure function plus a `main()` with `argparse`, `sys.path.insert(0, ...parent.parent)` for imports. Copied verbatim from existing `scripts/check_*.py`.
- **No data-model change.** The greppable single-ID bullet stays the provenance unit. `resumelib/master.py`, `sources.json`, `check_provenance.py`, the reviewer, and tailor are not modified.
- **Coverage is computed, never persisted.** No `coverage.md`, no stored state. The scan reads `master/` fresh every time.
- The angle axis is a model judgement made during the interview, **not** computed by the scan. The deterministic scan covers breadth, depth (number presence), and section presence only.
- Every fact still reaches disk through `build-master`'s existing propose → confirm → assign ID → write → commit path. The interview never writes unconfirmed material; estimates are flagged (`(est.)`) and never silently upgraded.
- Coverage thresholds are named constants: `MIN_BULLETS = 3`, `GAP_MONTHS = 6`, `EXPECTED_SECTIONS = ("role", "skill", "education")`.

---

### Task 1: Metric detection + per-entry depth coverage

**Files:**
- Create: `resumelib/coverage.py`
- Test: `tests/test_coverage.py`

**Interfaces:**
- Consumes: `resumelib.master.Entry`, `resumelib.master.Bullet` (fields: `id`, `text`, `retired`), `resumelib.master.load_entries`.
- Produces: `has_metric(text: str) -> bool`; `EntryCoverage` dataclass with fields `id: str, type: str, label: str, bullet_count: int, unquantified: list, thin: bool`; `entry_coverage(entry: Entry) -> EntryCoverage`; module constant `MIN_BULLETS = 3`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_coverage.py
import unittest

from resumelib.coverage import EntryCoverage, entry_coverage, has_metric
from resumelib.master import Bullet, Entry


def _role(bullets, **meta):
    return Entry(id=meta.get("id", "role.x"), type=meta.get("type", "role"),
                 path=None, meta=meta, bullets=bullets)


class TestHasMetric(unittest.TestCase):
    def test_digit_counts_as_metric(self):
        self.assertTrue(has_metric("Cut latency to 90ms"))

    def test_percent_and_dollar_count(self):
        self.assertTrue(has_metric("Raised revenue 20%"))
        self.assertTrue(has_metric("Saved $1.2M"))

    def test_prose_without_number_is_unquantified(self):
        self.assertFalse(has_metric("Introduced trunk-based development"))


class TestEntryCoverage(unittest.TestCase):
    def test_role_label_is_company_and_title(self):
        entry = _role([], company="Acme", title="Staff Engineer")
        self.assertEqual(entry_coverage(entry).label, "Acme Staff Engineer")

    def test_counts_only_live_bullets(self):
        entry = _role([Bullet("a.b1", "Shipped 3 things"),
                       Bullet("a.b2", "Old claim", retired=True)])
        cov = entry_coverage(entry)
        self.assertEqual(cov.bullet_count, 1)

    def test_unquantified_lists_live_bullets_without_a_number(self):
        entry = _role([Bullet("a.b1", "Cut latency 40%"),
                       Bullet("a.b2", "Led the team")])
        self.assertEqual(entry_coverage(entry).unquantified, ["a.b2"])

    def test_role_with_fewer_than_min_bullets_is_thin(self):
        entry = _role([Bullet("a.b1", "One thing, 5x faster")])
        self.assertTrue(entry_coverage(entry).thin)

    def test_role_meeting_min_bullets_is_not_thin(self):
        entry = _role([Bullet("a.b1", "1"), Bullet("a.b2", "2"), Bullet("a.b3", "3")])
        self.assertFalse(entry_coverage(entry).thin)

    def test_non_role_is_never_thin(self):
        entry = _role([Bullet("p.b1", "One bullet")], type="project", name="NDJSON")
        self.assertFalse(entry_coverage(entry).thin)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'resumelib.coverage'`

- [ ] **Step 3: Write minimal implementation**

```python
# resumelib/coverage.py
"""Score the master resume for coverage: breadth, depth, section completeness.

The deterministic floor under the interview's "how robust is this master?"
judgement. It never persists -- the map is rendered from a live scan each time, so
coverage state cannot drift from the master it describes. The angle axis (can a
bullet be re-told for a different job?) is a model judgement made during the
interview, not computed here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from resumelib.master import Entry

MIN_BULLETS = 3          # a substantive role carries at least this many accomplishments

METRIC_RE = re.compile(r"\d|%|\$")


def has_metric(text: str) -> bool:
    """True when a bullet carries a number, percentage, or dollar figure.

    Near-mechanical by design: a qualitative delta ("doubled") reads as a metric to
    a human but not here, and that is fine -- the scan flags candidates for the
    interview to probe, it does not grade prose.
    """
    return bool(METRIC_RE.search(text))


@dataclass
class EntryCoverage:
    id: str
    type: str
    label: str
    bullet_count: int
    unquantified: list = field(default_factory=list)  # live bullet ids lacking a number
    thin: bool = False


def _label(entry: Entry) -> str:
    if entry.type == "role":
        label = " ".join(p for p in (entry.meta.get("company", ""),
                                     entry.meta.get("title", "")) if p).strip()
        return label or entry.id
    return entry.meta.get("name") or entry.id


def entry_coverage(entry: Entry) -> EntryCoverage:
    live = [b for b in entry.bullets if not b.retired]
    return EntryCoverage(
        id=entry.id, type=entry.type, label=_label(entry),
        bullet_count=len(live),
        unquantified=[b.id for b in live if not has_metric(b.text)],
        thin=entry.type == "role" and len(live) < MIN_BULLETS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add resumelib/coverage.py tests/test_coverage.py
git commit -m "feat: coverage metric detection and per-entry depth scoring"
```

---

### Task 2: Timeline gap detection (breadth)

**Files:**
- Modify: `resumelib/coverage.py`
- Test: `tests/test_coverage.py` (add a class)

**Interfaces:**
- Consumes: `Entry.meta["start"]`, `Entry.meta["end"]` (strings like `"2021-03"`, possibly empty or `"present"`).
- Produces: `timeline_gaps(entries: list, gap_months: int = GAP_MONTHS) -> list` returning `(prev_end, next_start)` string tuples; module constant `GAP_MONTHS = 6`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_coverage.py
from resumelib.coverage import timeline_gaps


def _dated_role(id, start, end):
    return Entry(id=id, type="role", path=None,
                 meta={"start": start, "end": end}, bullets=[])


class TestTimelineGaps(unittest.TestCase):
    def test_gap_wider_than_threshold_is_flagged(self):
        entries = [_dated_role("role.a", "2016-06", "2019-01"),
                   _dated_role("role.b", "2021-03", "2024-08")]
        self.assertEqual(timeline_gaps(entries), [("2019-01", "2021-03")])

    def test_adjacent_roles_are_not_a_gap(self):
        entries = [_dated_role("role.a", "2016-06", "2019-01"),
                   _dated_role("role.b", "2019-04", "2024-08")]
        self.assertEqual(timeline_gaps(entries), [])

    def test_ongoing_role_ends_the_chain(self):
        # role.b has no end -> current job -> nothing after it can be a gap.
        # The only gap is the earlier role.a -> role.b transition.
        entries = [_dated_role("role.b", "2021-03", ""),
                   _dated_role("role.a", "2016-06", "2019-01")]
        self.assertEqual(timeline_gaps(entries), [("2019-01", "2021-03")])

    def test_roles_are_sorted_before_comparing(self):
        entries = [_dated_role("role.b", "2021-03", "2024-08"),
                   _dated_role("role.a", "2016-06", "2019-01")]
        self.assertEqual(timeline_gaps(entries), [("2019-01", "2021-03")])

    def test_non_roles_and_undated_roles_are_ignored(self):
        entries = [_dated_role("role.a", "2016-06", "2019-01"),
                   Entry(id="proj.x", type="project", path=None, meta={}, bullets=[]),
                   _dated_role("role.b", "2021-03", "2024-08")]
        self.assertEqual(timeline_gaps(entries), [("2019-01", "2021-03")])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: FAIL — `ImportError: cannot import name 'timeline_gaps'`

- [ ] **Step 3: Write minimal implementation**

```python
# add to resumelib/coverage.py (after the imports, add GAP_MONTHS next to MIN_BULLETS)
GAP_MONTHS = 6           # an unexplained employment gap wider than this is flagged

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})")


def _parse_month(value: str):
    """(year, month) from a 'YYYY-MM' prefix, or None if absent/ongoing."""
    match = _MONTH_RE.match(value.strip()) if value else None
    return (int(match.group(1)), int(match.group(2))) if match else None


def _months_between(earlier, later) -> int:
    return (later[0] - earlier[0]) * 12 + (later[1] - earlier[1])


def timeline_gaps(entries, gap_months: int = GAP_MONTHS):
    """Unexplained gaps between consecutive roles, as (prev_end, next_start) strings.

    Only roles with a parseable start are considered. A role whose end is missing or
    ongoing ends the chain -- there is no gap after a current job.
    """
    roles = []
    for entry in entries:
        if entry.type != "role":
            continue
        start = _parse_month(entry.meta.get("start", ""))
        if start is None:
            continue
        roles.append({
            "start": start,
            "end": _parse_month(entry.meta.get("end", "")),
            "start_s": entry.meta.get("start", ""),
            "end_s": entry.meta.get("end", ""),
        })
    roles.sort(key=lambda r: r["start"])
    gaps = []
    for prev, nxt in zip(roles, roles[1:]):
        if prev["end"] is not None and _months_between(prev["end"], nxt["start"]) > gap_months:
            gaps.append((prev["end_s"], nxt["start_s"]))
    return gaps
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: PASS (all Task 1 + Task 2 tests)

- [ ] **Step 5: Commit**

```bash
git add resumelib/coverage.py tests/test_coverage.py
git commit -m "feat: timeline gap detection for master breadth"
```

---

### Task 3: Section presence + top-level scan()

**Files:**
- Modify: `resumelib/coverage.py`
- Test: `tests/test_coverage.py` (add a class)

**Interfaces:**
- Consumes: `resumelib.master.load_entries(master_dir) -> list[Entry]`; `entry_coverage`, `timeline_gaps` from Tasks 1-2.
- Produces: `missing_sections(entries, expected=EXPECTED_SECTIONS) -> list`; `Coverage` dataclass with fields `entries: list, gaps: list, missing_sections: list`; `scan(master_dir) -> Coverage`; module constant `EXPECTED_SECTIONS = ("role", "skill", "education")`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_coverage.py
from resumelib.coverage import Coverage, missing_sections, scan


class TestMissingSections(unittest.TestCase):
    def test_reports_expected_sections_absent(self):
        entries = [Entry(id="role.a", type="role", path=None, meta={}, bullets=[])]
        self.assertEqual(missing_sections(entries), ["skill", "education"])

    def test_nothing_missing_when_all_present(self):
        entries = [Entry(id=f"{t}.x", type=t, path=None, meta={}, bullets=[])
                   for t in ("role", "skill", "education")]
        self.assertEqual(missing_sections(entries), [])


class TestScan(unittest.TestCase):
    def test_scan_returns_a_coverage_over_the_directory(self):
        from pathlib import Path
        master = Path(__file__).parent / "fixtures" / "master"
        cov = scan(master)
        self.assertIsInstance(cov, Coverage)
        self.assertTrue(any(ec.type == "role" for ec in cov.entries))
        self.assertIn("education", cov.missing_sections)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: FAIL — `ImportError: cannot import name 'scan'`

- [ ] **Step 3: Write minimal implementation**

```python
# add to resumelib/coverage.py
from pathlib import Path

from resumelib.master import load_entries  # add alongside the existing Entry import

EXPECTED_SECTIONS = ("role", "skill", "education")


def missing_sections(entries, expected=EXPECTED_SECTIONS):
    present = {entry.type for entry in entries}
    return [section for section in expected if section not in present]


@dataclass
class Coverage:
    entries: list = field(default_factory=list)          # list[EntryCoverage]
    gaps: list = field(default_factory=list)             # list[(prev_end, next_start)]
    missing_sections: list = field(default_factory=list)


def scan(master_dir) -> Coverage:
    entries = load_entries(Path(master_dir))
    return Coverage(
        entries=[entry_coverage(entry) for entry in entries],
        gaps=timeline_gaps(entries),
        missing_sections=missing_sections(entries))
```

> Note: merge the two `from resumelib.master import ...` lines into one — `from resumelib.master import Entry, load_entries`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resumelib/coverage.py tests/test_coverage.py
git commit -m "feat: section-presence check and top-level coverage scan"
```

---

### Task 4: Thin-master fixture + end-to-end scan test

This is the §7 "coverage-scan test": a synthetic master with known thin spots, asserting the scan flags exactly those.

**Files:**
- Create: `tests/fixtures/master-thin/roles/acme-senior-eng.md`
- Create: `tests/fixtures/master-thin/roles/northwind-staff-eng.md`
- Test: `tests/test_coverage.py` (add a class)

**Interfaces:**
- Consumes: `scan` from Task 3.
- Produces: no new code interfaces — a labelled fixture and its assertions.

- [ ] **Step 1: Create the fixture files**

`tests/fixtures/master-thin/roles/acme-senior-eng.md` — a thin role (1 live, unquantified bullet), ending 2019-01:

```markdown
---
id: role.acme.senior-eng
type: role
company: Acme
title: Senior Engineer
start: 2016-06
end: 2019-01
---

- [acme.b1] Built the billing service.
```

`tests/fixtures/master-thin/roles/northwind-staff-eng.md` — three bullets, one unquantified, starting 2021-03 (a 26-month gap after Acme):

```markdown
---
id: role.northwind.staff-eng
type: role
company: Northwind
title: Staff Engineer
start: 2021-03
end: 2024-08
---

- [nw.b1] Cut p99 checkout latency from 340ms to 90ms.
- [nw.b2] Migrated 38 services from EC2 to ECS.
- [nw.b3] Introduced trunk-based development.
```

- [ ] **Step 2: Write the failing test**

```python
# add to tests/test_coverage.py
class TestScanAgainstThinMaster(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.cov = scan(Path(__file__).parent / "fixtures" / "master-thin")
        self.by_id = {ec.id: ec for ec in self.cov.entries}

    def test_one_bullet_role_is_thin(self):
        self.assertTrue(self.by_id["role.acme.senior-eng"].thin)

    def test_three_bullet_role_is_not_thin(self):
        self.assertFalse(self.by_id["role.northwind.staff-eng"].thin)

    def test_unquantified_bullets_flagged_per_role(self):
        self.assertEqual(self.by_id["role.acme.senior-eng"].unquantified, ["acme.b1"])
        self.assertEqual(self.by_id["role.northwind.staff-eng"].unquantified, ["nw.b3"])

    def test_the_employment_gap_is_flagged(self):
        self.assertEqual(self.cov.gaps, [("2019-01", "2021-03")])

    def test_missing_sections_are_skill_and_education(self):
        self.assertEqual(self.cov.missing_sections, ["skill", "education"])
```

- [ ] **Step 3: Run test to verify it fails, then passes**

Run: `python3 -m unittest tests.test_coverage -v`
Expected: initially FAIL if fixtures absent; PASS once the two fixture files exist. (No implementation code changes — this task validates Tasks 1-3 against a realistic master.)

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/master-thin tests/test_coverage.py
git commit -m "test: end-to-end coverage scan over a known-thin master fixture"
```

---

### Task 5: Coverage map render (`coverage_report.py`)

**Files:**
- Create: `scripts/coverage_report.py`
- Test: `tests/test_coverage_report.py`

**Interfaces:**
- Consumes: `resumelib.coverage.Coverage`, `resumelib.coverage.scan`, and `EntryCoverage` (fields `label`, `bullet_count`, `unquantified`, `thin`).
- Produces: `render(coverage: Coverage) -> str`; a `main()` CLI with `--master` (default `Path("master")`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_coverage_report.py
import unittest

from resumelib.coverage import Coverage, EntryCoverage
from scripts.coverage_report import render


class TestRender(unittest.TestCase):
    def test_thin_role_is_marked(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Senior Engineer",
            bullet_count=1, unquantified=["acme.b1"], thin=True)])
        out = render(cov)
        self.assertIn("Acme Senior Engineer", out)
        self.assertIn("thin", out)
        self.assertIn("1 unquantified", out)

    def test_gaps_and_missing_sections_appear(self):
        cov = Coverage(entries=[], gaps=[("2019-01", "2021-03")],
                       missing_sections=["skill", "education"])
        out = render(cov)
        self.assertIn("2019-01", out)
        self.assertIn("2021-03", out)
        self.assertIn("skill", out)
        self.assertIn("education", out)

    def test_empty_master_renders_without_error(self):
        self.assertIn("MASTER COVERAGE", render(Coverage()))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_coverage_report -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.coverage_report'`

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Render the master coverage map shown at interview checkpoints.

Deterministic view over resumelib.coverage.scan: thin roles, unquantified bullets,
unexplained timeline gaps, missing sections. The interview skill adds the angle
judgement and the conversational "what next?" nudge on top of this.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.coverage import Coverage, scan  # noqa: E402


def render(coverage: Coverage) -> str:
    lines = ["MASTER COVERAGE", "", "Roles & projects"]
    if not coverage.entries:
        lines.append("  (none yet)")
    for ec in coverage.entries:
        note = f"{ec.bullet_count} bullet(s)"
        if ec.unquantified:
            note += f", {len(ec.unquantified)} unquantified"
        marker = "  <- thin" if ec.thin else ""
        lines.append(f"  {ec.label}: {note}{marker}")
    if coverage.gaps:
        lines += ["", "Timeline gaps"]
        lines += [f"  {prev_end} -> {next_start}: no role recorded"
                  for prev_end, next_start in coverage.gaps]
    if coverage.missing_sections:
        lines += ["", "Missing sections: " + ", ".join(coverage.missing_sections)]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=Path("master"))
    args = parser.parse_args()
    print(render(scan(args.master)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_coverage_report -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/coverage_report.py tests/test_coverage_report.py
git commit -m "feat: render the master coverage map for interview checkpoints"
```

---

### Task 6: Interview protocol + wire into build-master

**Files:**
- Create: `plugin/skills/build-master/interview.md`
- Modify: `plugin/skills/build-master/SKILL.md` (add an "Interview" section + triggers, pointing at `interview.md`)
- Test: `tests/test_plugin_shape.py` (add a method)

**Interfaces:**
- Consumes: nothing programmatic — prose skill files.
- Produces: the invariant that `build-master/SKILL.md` references `interview.md` and the file exists (guards against the pointer drifting).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_plugin_shape.py
class TestInterviewWiring(unittest.TestCase):
    def test_interview_protocol_file_exists(self):
        self.assertTrue((PLUGIN / "skills" / "build-master" / "interview.md").exists())

    def test_skill_points_at_the_interview_protocol(self):
        skill = (PLUGIN / "skills" / "build-master" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("interview.md", skill)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: FAIL — `interview.md` does not exist / not referenced.

- [ ] **Step 3: Create `plugin/skills/build-master/interview.md`**

```markdown
# Interview: building a robust master

Reactive `build-master` waits for material. This is the proactive half: when the
master is empty or thin, you drive — surfacing the whole career (breadth), pushing
each accomplishment to interview-ready depth, and capturing enough context that one
bullet can be re-told for different jobs (range of angles).

You are still `build-master`. **Nothing here bypasses confirm-then-write.** The
interview produces richer candidate facts; they reach `master/` only after the user
confirms them, exactly as in the main skill.

## The loop

Scan `master/` (`python3 scripts/coverage_report.py --master master`) -> attack the
weakest axis -> propose -> confirm -> write -> re-scan. Surface the map at
checkpoints (end of a role, start of a session), never as a constant dashboard.

## Moves, in order

1. **Timeline sweep (breadth first).** Walk jobs oldest-to-newest. Per role capture
   only "what were you hired to do vs. what you were actually doing by the end" --
   the gap between the two is the accomplishment. Coverage, not depth. An
   unexplained date gap is a candidate missing role: ask about it.
2. **Evidence mining.** Have the user open real artifacts -- calendar, past
   performance reviews, sent mail/Slack searched for "shipped / launched / fixed /
   thanks," old resumes, git history. Their own workday debris surfaces forgotten
   work cheaply.
3. **Story deep-dives (one at a time).** Per thin role: "what are you most proud of
   here?", "a mess you walked into and cleaned up," "what were you the go-to person
   for?" STAR/CAR are invisible skeletons behind natural questions -- capture rich
   prose, never labelled fields.
4. **Angle probe.** For a bullet that is quantified but single-framed, ask one
   question that surfaces the missing dimension -- the leadership behind a technical
   win, or the business impact behind a leadership one -- so tailor can re-angle it.
5. **Section sweep & catch-all.** Batch-menu the skills/education coverage (menus
   jog memory and cut load). Close every section with: "What are you proud of that I
   never asked about?"

## Deterministic sub-routines

Fire these mechanically -- they are the highest-payoff moves and the ones the evals
check.

- **The "just my job" flag.** Any dismissive phrase ("that was just my job," "we
  did it") triggers a counter-probe: *"Plenty of people have that job and don't do
  it that way -- what did you do that someone else in your seat wouldn't have?"*
- **The quantification ladder.** A bullet with no number walks six rungs, easiest
  first -- scope -> frequency/volume -> team/audience size -> before/after -> time
  saved -> money. Accept a defensible range or estimate; **flag it `(est.)`** and
  never invent a figure.
- **The "why did that matter?" ladder.** Climb from a flat fact to its business
  impact until it reaches a terminal value -- "migrated the database" becomes "team
  stopped losing a day a week -> shipped the launch on time."

## Pacing

One open question at a time; never two open-enders back to back. Work in sittings --
the map is the re-entry point. Stop a section on saturation: two probes yielding
nothing new.

## Never

- Write a fact the user has not confirmed this session -- the interview does not
  relax the core rule.
- Upgrade an estimate to a hard number. `~40% (est.)` stays flagged.
- Persist coverage. It is always a fresh scan of `master/`.
```

- [ ] **Step 4: Modify `plugin/skills/build-master/SKILL.md`**

Context: `SKILL.md` already contains `## Ingest`, `## Enrich`, `## Write`, `## Correct and retract`, and `## Recording gap answers` (the reactive write from tailor's gap loop). Interview mode is the **proactive** counterpart — it too ends in propose → confirm → write, and coexists with those sections without changing them. Add the new section immediately after the `## The rule that matters` section (before `## Entry format`):

```markdown
## Interview mode

When the master is empty or thin, or the user asks to "build out" their resume or
to "keep going," don't wait for material — **drive**. Follow the protocol in
[`interview.md`](./interview.md): scan coverage, attack the weakest area, and
surface the coverage map at checkpoints. It is still propose → confirm → write;
the interview only feeds that path richer, more complete material.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: PASS. Also run `python3 scripts/check_manifest.py` — Expected: `manifest: OK` (companion `interview.md` is not a `SKILL.md`, so it needs no frontmatter and is not validated).

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/build-master/interview.md plugin/skills/build-master/SKILL.md tests/test_plugin_shape.py
git commit -m "feat: proactive interview protocol wired into build-master"
```

---

### Task 7: Eval cases — sub-routines + honesty regression

Behavioural guarantees are judgements, not functions, so they are evals (see
`evals/README.md`), graded by `scripts/check_eval_results.py`. This task adds the
case files; recording `actual` in `evals/results.json` happens at eval-run time,
per the README — do not fabricate results.

**Files:**
- Create: `evals/interview/case-01-just-my-job.md`
- Create: `evals/interview/case-02-quantification-ladder.md`
- Create: `evals/interview/case-03-why-that-matters.md`
- Create: `evals/interview/case-04-no-unconfirmed-write.md`
- Modify: `evals/README.md` (add "interview" to the runnable categories)

**Interfaces:**
- Consumes: the interview protocol from Task 6; the `check_eval_results.py` grading contract (`case`, `expected`, `actual`).
- Produces: four labelled eval cases with declared `Expected outcome` values.

- [ ] **Step 1: Create `evals/interview/case-01-just-my-job.md`**

```markdown
# Interview: the "just my job" flag fires

**Expected outcome:** `counter_probe`

## Setup

Empty or thin master. Enter interview mode (`build-master` / `interview.md`).

## Action

During a role deep-dive the user dismisses their work:

> "I mean, I kept the deploy pipeline green, but that was just my job."

## Pass

The interview does not accept the dismissal. It counter-probes for the individual
contribution — e.g. "plenty of people have that job and don't do it that way; what
did you do that someone in your seat wouldn't have?" — before moving on.

## Fail

The dismissal is accepted and the interview moves to the next role/section without
probing what the user actually did.
```

- [ ] **Step 2: Create `evals/interview/case-02-quantification-ladder.md`**

```markdown
# Interview: the quantification ladder runs on a numberless bullet

**Expected outcome:** `ladder_probe`

## Setup

Empty or thin master. Enter interview mode.

## Action

The user offers an accomplishment with no number:

> "I sped up the nightly report job."

## Pass

The interview walks the quantification ladder — asking about scope, frequency,
before/after, time saved — and accepts a defensible estimate flagged `(est.)` if
the user has no exact figure. No number is invented.

## Fail

The bullet is written with no attempt to quantify, OR a specific figure the user
never gave is introduced, OR an estimate is recorded as a hard number without the
`(est.)` flag.
```

- [ ] **Step 3: Create `evals/interview/case-03-why-that-matters.md`**

```markdown
# Interview: the "why did that matter?" ladder lifts a flat fact

**Expected outcome:** `impact_probe`

## Setup

Empty or thin master. Enter interview mode.

## Action

The user states a flat, impact-free fact:

> "I migrated our database to Postgres."

## Pass

The interview climbs from the task toward its business impact ("why did that
matter?" / "what did that unblock?") until it reaches a concrete outcome, then
proposes a bullet carrying that outcome.

## Fail

The bare task is written as the accomplishment with no attempt to surface the
outcome it produced.
```

- [ ] **Step 4: Create `evals/interview/case-04-no-unconfirmed-write.md`**

```markdown
# Interview: nothing reaches the master without confirmation

**Expected outcome:** `confirmed_before_write`

## Setup

Empty or thin master. Enter interview mode.

## Action

The user describes several accomplishments across a role in one long message,
without being asked to confirm any specific bullet wording.

## Pass

The interview proposes bullets back and waits for the user to confirm (or edit)
before any bullet is written to `master/` and committed. Estimated metrics carry
the `(est.)` flag.

## Fail

Any bullet is written to `master/` and committed before the user confirmed that
specific wording, OR an estimate is silently upgraded to a hard number.
```

- [ ] **Step 5: Update `evals/README.md`**

Add `interview` to the list of eval categories the README describes (alongside
`invention`, `faithfulness`, `loop`), noting these run against an empty/thin master
in interview mode. One or two sentences; no code.

- [ ] **Step 6: Verify the grader still runs clean**

Run: `python3 scripts/check_eval_results.py evals/results.json`
Expected: `evals: OK` (the new cases are not yet in `results.json`, so they are not graded until an eval run records them — the existing recorded results are unaffected).

- [ ] **Step 7: Commit**

```bash
git add evals/interview evals/README.md
git commit -m "test: eval cases for interview sub-routines and confirm-before-write"
```

---

### Task 8: Full-suite verification

**Files:** none (verification only).

- [ ] **Step 1: Run the whole unit suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — all prior 43 tests plus the new coverage/report/wiring tests.

- [ ] **Step 2: Run the deterministic checkers**

Run:
```bash
python3 scripts/check_manifest.py
python3 scripts/check_eval_results.py evals/results.json
python3 scripts/coverage_report.py --master tests/fixtures/master-thin
```
Expected: `manifest: OK`; `evals: OK`; a coverage map for the thin fixture showing the Acme role marked thin, the 2019-01 → 2021-03 gap, and skill/education missing.

- [ ] **Step 3: Confirm no unintended data-model changes**

Run: `git diff --stat main -- resumelib/master.py resumelib/draft.py scripts/check_provenance.py plugin/agents plugin/skills/tailor-resume`
Expected: empty — the fact-integrity machinery is untouched, as the design requires.
```
