#!/usr/bin/env python3
"""Find which already-sent resumes cite a given master bullet.

Run before correcting or retracting a bullet. The point is not to block the edit
but to say out loud that there is a claim in the wild the user may no longer be
able to back up.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import load_sources  # noqa: E402


def find_citations(bullet_id: str, library_dir: Path) -> list:
    hits = []
    for sources in sorted(Path(library_dir).glob("*/sources.json")):
        if any(bullet_id in bullet.source for bullet in load_sources(sources)):
            hits.append(sources.parent)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bullet_id")
    parser.add_argument("--library", type=Path, default=Path("library"))
    args = parser.parse_args()

    hits = find_citations(args.bullet_id, args.library)
    if not hits:
        print(f"{args.bullet_id} is not cited by any sent resume.")
        return 0
    print(f"! {args.bullet_id} is cited in {len(hits)} resume(s) you already sent:")
    for path in hits:
        print(f"    {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
