"""Parse master resume entries.

An entry is a Markdown file with YAML-ish frontmatter and bullets of the form
`- [bullet.id] text`, optionally wrapped across lines. Bullets appearing under a
`## Retired` heading are retired: still resolvable so old citations do not dangle,
but not valid as a source for new drafts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

BULLET_RE = re.compile(r"^- \[([A-Za-z0-9._-]+)\]\s+(.*)$")
RETIRED_HEADING_RE = re.compile(r"^##\s+Retired\s*$", re.IGNORECASE)
# A leading (YYYY) or (YYYY-QN) is the bullet's period: metadata about when the
# work happened, not part of the claim. Anchored so "(est.)" and other
# mid-text parentheses are never touched.
PERIOD_RE = re.compile(r"^\((\d{4}(?:-Q[1-4])?)\)\s+")


@dataclass
class Bullet:
    id: str
    text: str
    retired: bool = False
    period: str | None = None


@dataclass
class Entry:
    id: str
    type: str
    path: Path
    meta: dict = field(default_factory=dict)
    bullets: list = field(default_factory=list)


def split_frontmatter(raw: str) -> tuple[dict, str]:
    """Return (meta, body). Supports only `key: value` scalar lines.

    Public because check_manifest.py validates skill and agent frontmatter with
    the same parser.
    """
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, parts[2]


def _parse_bullets(body: str) -> list:
    bullets: list = []
    retired = False
    # The bullet a continuation line may still attach to. Cleared by the blank
    # line or heading that closes the bullet, because an entry file's prose
    # contains markdown sub-lists whose wrapped lines are indented exactly like
    # a bullet's own continuation. Without the boundary those paragraphs glue
    # themselves onto the last bullet and print on the generated CV.
    open_bullet = None
    for line in body.splitlines():
        if RETIRED_HEADING_RE.match(line):
            retired = True
            open_bullet = None
            continue
        if line.startswith("## "):
            retired = False
            open_bullet = None
            continue
        if not line.strip():
            open_bullet = None
            continue
        match = BULLET_RE.match(line)
        if match:
            text = match.group(2).strip()
            period = None
            period_match = PERIOD_RE.match(text)
            if period_match:
                period = period_match.group(1)
                text = text[period_match.end():].strip()
            bullets.append(Bullet(id=match.group(1), text=text,
                                  retired=retired, period=period))
            open_bullet = bullets[-1]
        elif open_bullet is not None and line.startswith("  "):
            # Continuation of the previous bullet's wrapped text.
            open_bullet.text += " " + line.strip()
        else:
            open_bullet = None
    return bullets


def load_entries(master_dir: Path) -> list:
    entries = []
    for path in sorted(Path(master_dir).rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(raw)
        if "id" not in meta:
            continue  # not an entry file (e.g. known-gaps.md)
        entries.append(Entry(id=meta["id"], type=meta.get("type", ""), path=path,
                             meta=meta, bullets=_parse_bullets(body)))
    return entries


def load_bullets(master_dir: Path) -> dict:
    return {b.id: b for e in load_entries(master_dir) for b in e.bullets}
