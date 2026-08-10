"""Mechanics of the batch tailoring loop.

Batching exists so the user answers each question once rather than once per
job. That collapse is pure text grouping, so it lives here with tests instead
of in a skill file where it would be re-derived, differently, every run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_ROUNDS = 2
_PUNCT_RE = re.compile(r"[^a-z0-9+#]+")


@dataclass(frozen=True)
class Gap:
    job_slug: str
    requirement: str


@dataclass
class GapQuestion:
    requirement: str
    job_slugs: list = field(default_factory=list)


def normalize_requirement(text: str) -> str:
    return _PUNCT_RE.sub(" ", text.lower()).strip()


def group_gaps(gaps) -> list:
    """Collapse the same requirement raised by several jobs into one question,
    preserving first-seen order for both questions and their jobs."""
    questions = {}
    for gap in gaps:
        key = normalize_requirement(gap.requirement)
        if not key:
            continue
        question = questions.setdefault(
            key, GapQuestion(requirement=gap.requirement.strip()))
        if gap.job_slug not in question.job_slugs:
            question.job_slugs.append(gap.job_slug)
    return list(questions.values())


def next_round(round_index: int, new_questions: int,
               max_rounds: int = MAX_ROUNDS) -> bool:
    """A round that surfaced nothing new ends the batch; so does the cap.

    The cap matters because a reviewer can always find one more thing to ask.
    Unresolved gaps are reported, not looped on."""
    if new_questions <= 0:
        return False
    return round_index < max_rounds
