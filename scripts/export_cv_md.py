#!/usr/bin/env python3
"""Generate career-ops' cv.md from master/, and verify it is not stale.

This script is the only writer to cv.md, mirroring the rule that makes
build-master the only writer to master/. Hand-editing cv.md creates the second
source of truth this whole integration exists to prevent.

    python3 scripts/export_cv_md.py                # write cv.md
    python3 scripts/export_cv_md.py --check        # exit 1 if stale
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.cvexport import cv_staleness, render_cv  # noqa: E402
from resumelib.master import load_entries  # noqa: E402
from resumelib.redactions import load_redactions  # noqa: E402

DEFAULT_ROOT = Path("~/Projects/career-ops").expanduser()


def career_ops_root(flag: Path = None) -> Path:
    if flag:
        return Path(flag).expanduser()
    env = os.environ.get("CAREER_OPS_ROOT")
    if env:
        return Path(env).expanduser()
    return DEFAULT_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=Path("master"))
    parser.add_argument("--career-ops", type=Path, default=None)
    parser.add_argument("--check", action="store_true",
                        help="verify cv.md matches master/ without writing")
    args = parser.parse_args()

    entries = load_entries(args.master)
    redactions = load_redactions(args.master)
    target = career_ops_root(args.career_ops) / "cv.md"

    # --check is a superset of the write path: it runs the same render, so it
    # can never report "current" about a file the write path would refuse to
    # produce.
    text, findings = render_cv(entries, redactions)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")

    if args.check:
        if findings:
            print(f"\n{len(findings)} finding(s); cv.md would not be written.")
            return 1
        reason = cv_staleness(entries, redactions, target)
        if reason == "missing":
            print(f"[missing_cv] {target} does not exist; run without --check")
            return 1
        if reason == "no_digest":
            print(f"[no_digest] {target} carries no master-sha256 comment; "
                  "it was hand-edited or predates this script")
            return 1
        if reason == "stale":
            print(f"[stale_cv] {target} was built from a different master/; "
                  "re-run export_cv_md.py")
            return 1
        print("cv.md: current")
        return 0

    if findings:
        print(f"\n{len(findings)} finding(s); cv.md not written.")
        if target.exists():
            stub = ("# CV\n\nExport blocked: a newly withheld term has no "
                     "replacement declared in master/redactions.md. The "
                     "previous cv.md has been replaced with this stub so a "
                     "leaking export cannot linger on disk.\n")
            target.write_text(stub, encoding="utf-8")
            print(f"replaced {target} with a refusal stub")
        return 1

    if not target.parent.exists():
        print(f"[no_career_ops] {target.parent} does not exist")
        return 1
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
