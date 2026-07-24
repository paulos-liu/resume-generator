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
