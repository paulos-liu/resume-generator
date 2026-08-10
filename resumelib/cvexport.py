"""Render master entries into career-ops' cv.md format.

cv.md is a build artifact, never authored. It exists so career-ops scores the
user against facts that provably came from master/, with no second CV to drift.

Extraction is an allowlist: only parsed bullets are emitted, so master's prose
commentary -- confirmations, scope notes, private context -- is excluded by
construction rather than by a blocklist somebody has to remember to update.
"""

from __future__ import annotations

import hashlib
import re

from resumelib.draft import Finding
from resumelib.redactions import apply_redactions

DIGEST_RE = re.compile(r"<!--\s*master-sha256:\s*([0-9a-f]{64})\s*-->")

CONTACT_FIELDS = (("location", "Location"), ("email", "Email"),
                  ("linkedin", "LinkedIn"), ("github", "GitHub"))


def _emitted_bullets(entries: list, redactions: list) -> tuple:
    """Return (by_entry_id, findings). Retired bullets are skipped; a bullet
    naming a withheld term with no replacement is a blocking finding."""
    by_entry = {}
    findings = []
    for entry in entries:
        texts = []
        for bullet in entry.bullets:
            if bullet.retired:
                continue
            text, blocked = apply_redactions(bullet.text, redactions)
            for redaction in blocked:
                findings.append(Finding(
                    "blocked_term",
                    f"{bullet.id} names {redaction.term!r}, withheld with no "
                    f"replacement declared in master/redactions.md"))
            texts.append(text)
        by_entry[entry.id] = texts
    return by_entry, findings


def _dates(meta: dict) -> str:
    start, end = meta.get("start", ""), meta.get("end", "")
    if not start:
        return end
    return f"{start} to {end}" if end else f"{start} to Present"


def _education_line(meta: dict, redactions: list) -> tuple:
    """Render one education entry from its frontmatter.

    Education is the one entry type whose facts live entirely in frontmatter --
    a degree is a field, not an accomplishment -- so the bullets-only path drops
    it and the CV ships with no degree on it. Redactions still apply: this text
    reaches career-ops exactly as bullet text does, so it goes through the same
    fail-closed check rather than around it.
    """
    parts = [meta.get("degree") or meta.get("name", "")]
    if meta.get("institution"):
        parts.append(meta["institution"])
    line = ", ".join(p for p in parts if p)
    if meta.get("minor"):
        line += f" (Minor: {meta['minor']})"
    tail = [v for v in (meta.get("location"), _dates(meta)) if v]
    if tail:
        line += " -- " + ", ".join(tail)
    return apply_redactions(line, redactions)


def _render_document(entries: list, redactions: list) -> tuple:
    """Build the CV body -- everything render_cv emits except the trailing
    digest comment. Returns (body, findings); body is "" when findings is
    non-empty, mirroring render_cv's fail-closed contract."""
    by_entry, findings = _emitted_bullets(entries, redactions)
    if findings:
        return "", findings  # fail closed: emit nothing rather than a leak

    contact = next((e for e in entries if e.type == "contact"), None)
    roles = sorted((e for e in entries if e.type == "role"),
                   key=lambda e: e.meta.get("start", ""), reverse=True)
    skills = [e for e in entries if e.type == "skill"]
    education = [e for e in entries if e.type == "education"]
    projects = [e for e in entries if e.type == "project"]

    lines = []
    # `name:` is the entry's descriptive label throughout this schema (e.g.
    # "Contact details"), not the candidate's name. Only an explicit
    # `full_name:` is trusted as a person's name; `name:` is a fallback for
    # fixtures/older data that happen to use it as one, never a label source.
    name = None
    if contact:
        name = contact.meta.get("full_name") or contact.meta.get("name")
    lines.append(f"# CV -- {name}" if name else "# CV")
    lines.append("")
    if contact:
        for key, label in CONTACT_FIELDS:
            if contact.meta.get(key):
                lines.append(f"**{label}:** {contact.meta[key]}")
        lines.append("")

    lines.append("## Work Experience")
    lines.append("")
    for role in roles:
        heading = role.meta.get("company", role.id)
        if role.meta.get("location"):
            heading += f" -- {role.meta['location']}"
        lines.append(f"### {heading}")
        lines.append("")
        lines.append(f"**{role.meta.get('title', '')}**")
        dates = _dates(role.meta)
        if dates:
            lines.append(dates)
        lines.append("")
        for text in by_entry.get(role.id, []):
            lines.append(f"- {text}")
        lines.append("")

    for heading, group in (("Projects", projects), ("Skills", skills),
                           ("Education", education)):
        emitted = [t for e in group for t in by_entry.get(e.id, [])]
        if group is education:
            # Frontmatter fallback, per entry: an education entry with bullets
            # keeps them, one without still gets its degree on the page.
            for entry in education:
                if by_entry.get(entry.id):
                    continue
                line, blocked = _education_line(entry.meta, redactions)
                for redaction in blocked:
                    findings.append(Finding(
                        "blocked_term",
                        f"{entry.id} names {redaction.term!r}, withheld with no "
                        f"replacement declared in master/redactions.md"))
                if line:
                    emitted.append(line)
            if findings:
                return "", findings  # same fail-closed contract as bullets
        if not emitted:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        lines.extend(f"- {text}" for text in emitted)
        lines.append("")

    return "\n".join(lines), []


def bullet_digest(entries: list, redactions: list) -> str:
    """SHA-256 over render_cv's output with the digest line itself removed.

    Covering the whole rendered body (not just bullet text) means frontmatter
    that reaches cv.md -- title, company, dates, the contact name -- moves the
    digest too.

    Hashes the rendered body alone; the redaction store is deliberately not
    folded in. It doesn't need to be: a newly withheld term with no
    replacement already invalidates any prior digest on its own, because
    _render_document collapses the body to "" whenever a bullet names a
    blocked term, and "" cannot collide with any real document's hash. Folding
    the store in on top of that (an earlier version of this function did)
    produced false positives instead: declaring, editing, or removing a
    redaction term that matches no emitted bullet changed the digest even
    though the rendered body was byte-identical, so --check and import_job.py
    reported a current cv.md as stale.
    """
    body, _ = _render_document(entries, redactions)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def render_cv(entries: list, redactions: list) -> tuple:
    body, findings = _render_document(entries, redactions)
    if findings:
        return "", findings  # fail closed: emit nothing rather than a leak
    digest = bullet_digest(entries, redactions)
    return f"{body}\n<!-- master-sha256: {digest} -->\n", []


def cv_staleness(entries: list, redactions: list, cv_path) -> str:
    """Compare a cv.md on disk against master/ without duplicating the digest
    comparison at each call site. cv_path is a pathlib.Path. Returns "" when
    current, else one of "missing", "no_digest", "stale"."""
    if not cv_path.exists():
        return "missing"
    match = DIGEST_RE.search(cv_path.read_text(encoding="utf-8"))
    if not match:
        return "no_digest"
    if match.group(1) != bullet_digest(entries, redactions):
        return "stale"
    return ""
