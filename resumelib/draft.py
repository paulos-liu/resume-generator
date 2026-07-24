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
