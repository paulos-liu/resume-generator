#!/usr/bin/env python3
"""Verify every drafted bullet cites a live master bullet.

Exit 0 when clean, 1 when any finding is present. This check is mechanical on
purpose: it is the one defense against invention that involves no model judgment.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding, load_sources  # noqa: E402
from resumelib.master import load_bullets  # noqa: E402


def check(sources_path: Path, master_dir: Path) -> list:
    master = load_bullets(master_dir)
    findings = []
    for bullet in load_sources(sources_path):
        if not bullet.source:
            findings.append(Finding("uncited", f"no source cited: {bullet.text!r}"))
            continue
        for source_id in bullet.source:
            if source_id not in master:
                findings.append(Finding(
                    "unknown_source",
                    f"cites {source_id}, which is not in the master: {bullet.text!r}"))
            elif master[source_id].retired:
                findings.append(Finding(
                    "retired_source",
                    f"cites retired bullet {source_id}: {bullet.text!r}"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path,
                        help="path to sources.json (or a library dir containing it)")
    parser.add_argument("--master", type=Path, default=Path("master"))
    args = parser.parse_args()

    sources = args.sources / "sources.json" if args.sources.is_dir() else args.sources
    findings = check(sources, args.master)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} provenance finding(s). This is a hard failure.")
        return 1
    print("provenance: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
