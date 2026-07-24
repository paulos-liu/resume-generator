"""Score the master resume for coverage: breadth, depth, section completeness.

The deterministic floor under the interview's "how robust is this master?"
judgement. It never persists -- the map is rendered from a live scan each time, so
coverage state cannot drift from the master it describes. The angle axis (can a
bullet be re-told for a different job?) is a model judgement made during the
interview, not computed here.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

from resumelib.master import Entry, load_entries

MIN_BULLETS = 3          # a substantive role carries at least this many accomplishments
GAP_MONTHS = 6           # an unexplained employment gap wider than this is flagged
EXPECTED_SECTIONS = ("role", "skill", "education")

YEAR_MIN_BULLETS = 1     # every year of tenure carries at least one accomplishment
QUIET_YEAR_RE = re.compile(r"^\d{4}$")

METRIC_RE = re.compile(r"\d|%|\$")
_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})")


def has_metric(text: str) -> bool:
    """True when a bullet carries a number, percentage, or dollar figure.

    Near-mechanical by design: a qualitative delta ("doubled") reads as a metric to
    a human but not here, and that is fine -- the scan flags candidates for the
    interview to probe, it does not grade prose.
    """
    return bool(METRIC_RE.search(text))


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


@dataclass
class EntryCoverage:
    id: str
    type: str
    label: str
    bullet_count: int
    unquantified: list = field(default_factory=list)  # live bullet ids lacking a number
    thin: bool = False
    years: list = field(default_factory=list)          # list[YearCoverage]
    undated: list = field(default_factory=list)        # live bullet ids with no period
    out_of_range: list = field(default_factory=list)   # (bullet_id, period) outside tenure


def _label(entry: Entry) -> str:
    if entry.type == "role":
        label = " ".join(p for p in (entry.meta.get("company", ""),
                                     entry.meta.get("title", "")) if p).strip()
        return label or entry.id
    return entry.meta.get("name") or entry.id


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


def entry_coverage(entry: Entry, today=None) -> EntryCoverage:
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


def missing_sections(entries, expected=EXPECTED_SECTIONS):
    present = {entry.type for entry in entries}
    return [section for section in expected if section not in present]


@dataclass
class Coverage:
    entries: list = field(default_factory=list)          # list[EntryCoverage]
    gaps: list = field(default_factory=list)             # list[(prev_end, next_start)]
    missing_sections: list = field(default_factory=list)


def scan(master_dir, today=None) -> Coverage:
    entries = load_entries(Path(master_dir))
    return Coverage(
        entries=[entry_coverage(entry, today=today) for entry in entries],
        gaps=timeline_gaps(entries),
        missing_sections=missing_sections(entries))
