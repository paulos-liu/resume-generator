"""Parse a tailored draft's provenance sidecar."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DraftBullet:
    text: str
    source: list = field(default_factory=list)


@dataclass
class Finding:
    kind: str
    detail: str


def load_sources(sources_path: Path) -> list:
    data = json.loads(Path(sources_path).read_text(encoding="utf-8"))
    return [DraftBullet(text=item.get("text", ""), source=list(item.get("source", [])))
            for item in data]


def load_draft_bullets(draft_path: Path) -> list:
    """Extract the text of every `- ` list-item bullet in a drafted resume.

    Only top-level `- ` lines count as claims; headings, the contact line, and
    blank lines are not bullets. A bullet's text may wrap across following
    lines that are indented and not themselves a new bullet or heading,
    mirroring how resumelib.master parses wrapped master bullets.
    """
    bullets: list = []
    for line in Path(draft_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        elif (bullets and line.strip() and line[:1].isspace()
              and not line.lstrip().startswith(("- ", "#"))):
            bullets[-1] += " " + line.strip()
    return bullets


def normalize_bullet_text(text: str) -> str:
    """Collapse whitespace so wrapped/reflowed bullet text compares equal."""
    return " ".join(text.split())
