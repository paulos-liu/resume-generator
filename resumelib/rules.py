"""Parse preferences/hard-rules.md.

The file is prose for the model with one fenced ```json block of machine-readable
rules. One file, so the human-readable and machine-readable halves cannot drift.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

JSON_FENCE_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


@dataclass
class Rules:
    max_lines: int = 0
    banned_words: list = field(default_factory=list)
    ban_first_person: bool = False
    filler_adverbs: list = field(default_factory=list)
    present_tense_verbs: list = field(default_factory=list)


def load_rules(path: Path) -> Rules:
    match = JSON_FENCE_RE.search(Path(path).read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: no ```json fence found")
    data = json.loads(match.group(1))
    return Rules(
        max_lines=data.get("max_lines", 0),
        banned_words=data.get("banned_words", []),
        ban_first_person=data.get("ban_first_person", False),
        filler_adverbs=data.get("filler_adverbs", []),
        present_tense_verbs=data.get("present_tense_verbs", []),
    )
