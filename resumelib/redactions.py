"""Terms withheld from generated artifacts.

`master/redactions.md` records phrases the user has decided not to publish
without deciding case by case -- a customer name, a project codename. It has no
frontmatter, so `load_entries` skips it exactly as it skips known-gaps.md, and
its lines can never be mistaken for master bullets.

Two verbs, one store. Export *substitutes* (a generated cv.md must never carry a
withheld term into a third-party model). Drafts are only *reported* on, because
naming a term on a real resume is the user's decision to make, not a script's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

STORE_NAME = "redactions.md"
LINE_RE = re.compile(r"^-\s+(.+?)(?:\s+=>\s+(.*))?$")


@dataclass(frozen=True)
class Redaction:
    term: str
    replacement: str | None = None


def load_redactions(master_dir: Path) -> list:
    path = Path(master_dir) / STORE_NAME
    if not path.exists():
        return []
    redactions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = LINE_RE.match(line.strip())
        if not match:
            continue
        term = match.group(1).strip()
        replacement = (match.group(2) or "").strip() or None
        redactions.append(Redaction(term=term, replacement=replacement))
    return redactions


def _pattern(term: str) -> re.Pattern:
    """Match `term` literally, anchored to a word boundary on each end that
    begins or ends with an alphanumeric character.

    Without this, a short term (three letters, say) matches as a substring of
    any longer word that happens to contain it, and the export then fails
    closed on prose that never named the withheld thing. A term with leading
    or trailing punctuation (already unlikely to appear mid-word) is left to
    match as a plain substring, since `\\b` only means something at a
    word/non-word transition.
    """
    escaped = re.escape(term)
    prefix = r"\b" if term[:1].isalnum() else ""
    suffix = r"\b" if term[-1:].isalnum() else ""
    return re.compile(prefix + escaped + suffix, re.IGNORECASE)


def find_terms(text: str, redactions: list) -> list:
    return [r for r in redactions if _pattern(r.term).search(text)]


def apply_redactions(text: str, redactions: list) -> tuple:
    """Substitute every declared replacement. Return (text, blocked), where
    blocked lists matched redactions that have no replacement -- the caller
    must fail rather than emit them."""
    blocked = []
    for redaction in find_terms(text, redactions):
        if redaction.replacement is None:
            blocked.append(redaction)
            continue
        text = _pattern(redaction.term).sub(redaction.replacement, text)
    return text, blocked
