#!/usr/bin/env python3
"""Verify a tailored draft carries a durable, current, clean review record.

render-resume must refuse to render a draft that has not passed review -- but
"has it passed review" is not observable from a fresh session unless the
review left a record. This script is that record's writer (`record`) and its
verifier (`check`); both share this module so they can never disagree about
`review.json`'s shape.

`check` is a hard failure (exit 1) in three cases, all mechanically decidable:
review.json is absent, its verdict is not clean, or its recorded hash of
draft.md no longer matches the file on disk (the draft was edited by hand, or
by the review loop, after the review that verdict describes).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402

REVIEW_FILENAME = "review.json"
DRAFT_FILENAME = "draft.md"


def _draft_hash(draft_path: Path) -> str:
    return hashlib.sha256(draft_path.read_bytes()).hexdigest()


def record(library_dir: Path, findings: list) -> dict:
    """Write review.json for the draft currently in library_dir.

    `findings` is the raw JSON list resume-reviewer returned (dicts with at
    least "kind" and "detail"). An empty list is a clean verdict.
    """
    library_dir = Path(library_dir)
    draft_path = library_dir / DRAFT_FILENAME
    review = {
        "verdict": "clean" if not findings else "unresolved",
        "findings": findings,
        "draft_sha256": _draft_hash(draft_path),
    }
    (library_dir / REVIEW_FILENAME).write_text(
        json.dumps(review, indent=2) + "\n", encoding="utf-8")
    return review


def check(library_dir: Path) -> list:
    library_dir = Path(library_dir)
    review_path = library_dir / REVIEW_FILENAME
    if not review_path.exists():
        return [Finding(
            "missing_review",
            f"{library_dir}: no review.json -- this draft has no durable record "
            "of ever having been reviewed")]

    try:
        data = json.loads(review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [Finding("bad_review", f"{review_path}: not valid JSON ({exc})")]

    draft_path = library_dir / DRAFT_FILENAME
    if not draft_path.exists():
        return [Finding("missing_draft", f"{draft_path} does not exist")]

    findings = data.get("findings", [])
    verdict = data.get("verdict")
    if verdict != "clean" or findings:
        return [Finding(
            "unresolved_review",
            f"review verdict is {verdict!r} with {len(findings)} outstanding "
            "finding(s); the review loop has not reached clean")]

    current_hash = _draft_hash(draft_path)
    recorded_hash = data.get("draft_sha256")
    if recorded_hash != current_hash:
        return [Finding(
            "stale_review",
            f"{draft_path} has changed since the recorded clean review "
            f"(recorded {str(recorded_hash)[:12]}..., current {current_hash[:12]}...); "
            "re-review before rendering")]

    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library_dir", type=Path,
                        help="library/<application> directory")
    parser.add_argument(
        "--record", type=Path, metavar="FINDINGS_JSON", default=None,
        help="write review.json from a JSON file of reviewer findings, "
             "instead of checking")
    args = parser.parse_args()

    if args.record is not None:
        findings = json.loads(args.record.read_text(encoding="utf-8"))
        review = record(args.library_dir, findings)
        print(f"review.json written: verdict={review['verdict']}")
        return 0

    findings = check(args.library_dir)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} review finding(s). Do not render.")
        return 1
    print("review: OK (clean, current)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
