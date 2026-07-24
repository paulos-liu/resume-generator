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
from pathlib import Path

from resumelib.master import Entry, load_entries

MIN_BULLETS = 3          # a substantive role carries at least this many accomplishments
GAP_MONTHS = 6           # an unexplained employment gap wider than this is flagged
EXPECTED_SECTIONS = ("role", "skill", "education")

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


def scan(master_dir) -> Coverage:
    entries = load_entries(Path(master_dir))
    return Coverage(
        entries=[entry_coverage(entry) for entry in entries],
        gaps=timeline_gaps(entries),
        missing_sections=missing_sections(entries))
