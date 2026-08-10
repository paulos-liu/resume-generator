#!/usr/bin/env python3
"""Flag withheld terms in a library application's generated artifacts.

Reports, never rewrites. Whether to name a withheld term on a document that
reaches an employer is the user's decision; this check only guarantees the
decision is made deliberately rather than by a draft nobody re-read.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402
from resumelib.redactions import find_terms, load_redactions  # noqa: E402

ARTIFACT_GLOBS = ("draft.md", "cover-letter*.md", "outreach*.md")


def check(library_dir: Path, master_dir: Path) -> list:
    redactions = load_redactions(master_dir)
    if not redactions:
        return []
    findings = []
    library_dir = Path(library_dir)
    for glob in ARTIFACT_GLOBS:
        for path in sorted(library_dir.glob(glob)):
            text = path.read_text(encoding="utf-8")
            for redaction in find_terms(text, redactions):
                findings.append(Finding(
                    "redacted_term",
                    f"{path.name} names {redaction.term!r}, which master/"
                    f"{'redactions.md'} withholds"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path)
    parser.add_argument("--master", type=Path, default=Path("master"))
    args = parser.parse_args()

    findings = check(args.library, args.master)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} redaction finding(s).")
        return 1
    print("redactions: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
