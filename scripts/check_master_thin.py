#!/usr/bin/env python3
"""Refuse to tailor against a master resume too thin to draft from honestly.

Mirrors the threshold in tailor-resume/SKILL.md step 0: fewer than three
entries, or fewer than eight live bullets total, produces either an empty
resume or an invented one -- there simply isn't enough material to select
from. Mechanical because resumelib.coverage.scan() already computes both
counts from the master; this is arithmetic over that result, not judgment.

Deliberately takes a `Coverage`, not a directory path, so the threshold logic
is testable without fixture files on disk (see coverage_report.py for the same
pattern) and so this script and coverage_report.py can never disagree about
what "thin" means for a given master.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.coverage import Coverage, scan  # noqa: E402
from resumelib.draft import Finding  # noqa: E402

MIN_ENTRIES = 3
MIN_LIVE_BULLETS = 8


def check(coverage: Coverage) -> list:
    entry_count = len(coverage.entries)
    bullet_count = sum(ec.bullet_count for ec in coverage.entries)
    if entry_count < MIN_ENTRIES or bullet_count < MIN_LIVE_BULLETS:
        return [Finding(
            "thin_master",
            f"master has {entry_count} entries and {bullet_count} live bullet(s) "
            f"(need at least {MIN_ENTRIES} entries and {MIN_LIVE_BULLETS} live "
            "bullets); route to build-master before tailoring")]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=Path("master"))
    args = parser.parse_args()

    findings = check(scan(args.master))
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} finding(s). Do not tailor; route to build-master.")
        return 1
    print("master: OK (not thin)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
