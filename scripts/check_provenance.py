#!/usr/bin/env python3
"""Verify every drafted bullet cites a live master bullet.

Exit 0 when clean, 1 when any finding is present. This check is mechanical on
purpose: it is the one defense against invention that involves no model judgment.

Two independent things are verified, because either one alone is not enough:

1. Every entry in sources.json cites a live (non-retired, existing) master ID,
   and does not silently upgrade an estimated master figure to a hard number.
2. Every bullet actually printed in draft.md has a corresponding sources.json
   entry. Without this second pass, a drafted bullet that sources.json simply
   omits is invisible -- the sidecar would validate itself in a circle.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import (  # noqa: E402
    Finding,
    load_draft_bullets,
    load_sources,
    normalize_bullet_text,
)
from resumelib.master import load_bullets  # noqa: E402

ESTIMATE_MARKER = "(est.)"


def _resolve(target: Path) -> tuple:
    """Return (sources_path, library_dir) for either a library dir or a
    sources.json path handed directly (kept for the existing test/CLI
    interface)."""
    target = Path(target)
    if target.is_dir():
        return target / "sources.json", target
    return target, target.parent


def check(target: Path, master_dir: Path) -> list:
    sources_path, library_dir = _resolve(target)
    master = load_bullets(master_dir)
    sources = load_sources(sources_path)
    findings = []

    for bullet in sources:
        if not bullet.source:
            findings.append(Finding("uncited", f"no source cited: {bullet.text!r}"))
            continue
        for source_id in bullet.source:
            if source_id not in master:
                findings.append(Finding(
                    "unknown_source",
                    f"cites {source_id}, which is not in the master: {bullet.text!r}"))
                continue
            master_bullet = master[source_id]
            if master_bullet.retired:
                findings.append(Finding(
                    "retired_source",
                    f"cites retired bullet {source_id}: {bullet.text!r}"))
            elif (ESTIMATE_MARKER in master_bullet.text
                  and ESTIMATE_MARKER not in bullet.text):
                findings.append(Finding(
                    "estimate_upgraded",
                    f"drops the {ESTIMATE_MARKER} marker carried by {source_id}: "
                    f"{bullet.text!r}"))

    # Cross-check against the actual drafted resume. A missing draft.md is
    # itself a finding, not a reason to skip this pass silently -- that
    # silent skip is exactly the bug this check exists to close.
    draft_path = library_dir / "draft.md"
    if not draft_path.is_file():
        findings.append(Finding(
            "missing_draft",
            f"no draft.md found next to {sources_path} -- cannot verify that "
            "every drafted bullet is cited"))
        return findings

    cited_texts = {normalize_bullet_text(b.text) for b in sources}
    for bullet_text in load_draft_bullets(draft_path):
        if normalize_bullet_text(bullet_text) not in cited_texts:
            findings.append(Finding(
                "uncited",
                f"drafted bullet has no matching sources.json entry: {bullet_text!r}"))

    # The reverse direction (a sources.json entry with no matching draft
    # bullet) is stale bookkeeping, not a safety problem -- nothing false
    # reached the reader. It is deliberately not reported here: this script's
    # only lever is a hard pass/fail exit code, and flagging stale sidecar
    # entries as a build-breaking finding would train editors to "fix" it by
    # padding draft.md back out, or to ignore the gate. If stale-entry
    # detection becomes valuable, it should get its own non-fatal warning
    # channel rather than share exit-code semantics with unsupported claims.

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
