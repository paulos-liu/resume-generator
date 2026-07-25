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


BAR_WIDTH = 8


def _bar(count: int, width: int = BAR_WIDTH) -> str:
    """Visual weight, not a precise scale -- the marker is what gets acted on."""
    filled = min(count, width)
    return "#" * filled + "." * (width - filled)


def render(coverage: Coverage) -> str:
    lines = ["MASTER COVERAGE", "", "Roles & projects"]
    if not coverage.entries:
        lines.append("  (none yet)")
    for ec in coverage.entries:
        note = f"{ec.bullet_count} bullet(s)"
        if ec.unquantified:
            note += f", {len(ec.unquantified)} unquantified"
        marker = "  <- thin" if ec.thin else ""
        tenure = f" ({ec.start} -> {ec.end or 'now'})" if ec.start else ""
        lines.append(f"  {ec.label}{tenure}: {note}{marker}")
        # Before the year rows, not after: an undated bullet counts toward no
        # year, so these are the explanation for markers printed below them.
        if ec.undated:
            lines.append(f"    {len(ec.undated)} undated bullet(s): "
                         + ", ".join(ec.undated))
        for yc in ec.years:
            suffix = ""
            if yc.quiet:
                suffix = "  <- declared quiet"
            elif yc.unmined:
                suffix = "  <- nothing recorded"
                if ec.undated:
                    suffix += f" ({len(ec.undated)} undated bullet(s) unplaced)"
            lines.append(f"    {yc.year} {_bar(yc.bullet_count)}  "
                         f"{yc.bullet_count} bullet(s){suffix}")
        for bullet_id, period in ec.out_of_range:
            lines.append(f"    {bullet_id} dated {period}, outside this entry's tenure")
        for value in ec.bad_quiet:
            lines.append(f"    quiet value {value!r} not understood (bare years only)")
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
