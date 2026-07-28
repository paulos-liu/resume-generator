#!/usr/bin/env python3
"""Report which matched requirements' vocabulary actually surfaces in the draft.

The screening layer between a submitted resume and a human — an applicant
tracking system, or a recruiter keyword-skimming a stack — matches words, not
meaning. A draft can cite the right master bullet for a requirement and still
never use the job's own term for it, and that gap is invisible to both
provenance and hard-rule checks.

Deterministic view over requirements.md and draft.md. For every requirement
that HAS a master match, it reports whether the requirement's content words
appear in the draft. Requirements marked NO MATCH are listed but never counted
against the draft: they are honest gaps, and honestly absent beats plausibly
stretched — pressuring the draft to name them would be pressure to invent.

This is a report, not a gate (compare coverage_report.py, not check_*.py). A
matched bullet can be deliberately dropped for the length budget, which makes
its missing keyword a selection decision, not an error. The tailor-resume
skill decides what to do with each MISSING row; exit code is always 0.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

NO_MATCH = "NO MATCH"

REQUIREMENT_RE = re.compile(r"^-\s*\[(must|nice)\]\s*(.+)$")
# The match column is separated by an em dash or a double hyphen; split on the
# LAST separator so requirement text may itself contain a dash.
SEPARATOR_RE = re.compile(r"\s(?:—|--)\s(?=[^—]*$)")

# Words that carry no screening weight. Small on purpose: over-filtering makes
# terms silently unmatchable, and a stopword list is not the place for judgment.
STOPWORDS = frozenset((
    "and", "the", "with", "for", "from", "into", "over", "across", "of", "in",
    "on", "to", "a", "an", "or", "at", "by", "as", "using", "experience",
    "knowledge", "ability", "skills", "strong", "work", "working",
))

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9.+#/-]*")


@dataclass
class Requirement:
    priority: str          # "must" | "nice"
    text: str
    matched: bool          # False when the match column says NO MATCH
    missing: list = field(default_factory=list)
    present: list = field(default_factory=list)

    @property
    def status(self) -> str:
        if not self.matched:
            return "GAP"
        if not self.missing:
            return "FULL"
        return "PARTIAL" if self.present else "MISSING"


def _terms(text: str) -> list:
    return [t for t in TOKEN_RE.findall(text.lower())
            if len(t) >= 3 and t not in STOPWORDS]


def _term_in(term: str, draft_lower: str) -> bool:
    """Word-boundary match, tolerating a trailing plural either way."""
    stem = term[:-1] if term.endswith("s") else term
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(stem)}s?(?![a-z0-9])",
                          draft_lower))


def parse_requirements(requirements_path: Path) -> list:
    requirements = []
    for line in Path(requirements_path).read_text(encoding="utf-8").splitlines():
        match = REQUIREMENT_RE.match(line.strip())
        if not match:
            continue
        priority, rest = match.groups()
        parts = SEPARATOR_RE.split(rest, maxsplit=1)
        text = parts[0].strip()
        match_column = parts[1].strip() if len(parts) > 1 else ""
        requirements.append(Requirement(
            priority=priority, text=text,
            matched=match_column.upper() != NO_MATCH))
    return requirements


def scan(requirements_path: Path, draft_path: Path) -> list:
    draft_lower = Path(draft_path).read_text(encoding="utf-8").lower()
    requirements = parse_requirements(requirements_path)
    for requirement in requirements:
        if not requirement.matched:
            continue
        for term in _terms(requirement.text):
            bucket = (requirement.present if _term_in(term, draft_lower)
                      else requirement.missing)
            bucket.append(term)
    return requirements


def render(requirements: list) -> str:
    lines = ["KEYWORD COVERAGE", ""]
    for requirement in requirements:
        row = f"[{requirement.priority}] {requirement.status:<7} {requirement.text}"
        if requirement.status in ("PARTIAL", "MISSING"):
            row += f"  (draft never says: {', '.join(requirement.missing)})"
        lines.append(row)
    gaps = sum(1 for r in requirements if not r.matched)
    misses = sum(1 for r in requirements
                 if r.matched and r.status in ("PARTIAL", "MISSING"))
    lines += ["", f"{len(requirements)} requirement(s): "
              f"{misses} with vocabulary missing from the draft, "
              f"{gaps} honest gap(s) (not counted against the draft)."]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library_dir", type=Path,
                        help="library/<application> directory")
    args = parser.parse_args()

    print(render(scan(args.library_dir / "requirements.md",
                      args.library_dir / "draft.md")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
