#!/usr/bin/env python3
"""Validate the plugin manifest and every skill/agent frontmatter block.

Frontmatter errors otherwise fail silently by disabling a skill at load time,
which is very hard to notice and very easy to misdiagnose.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402
from resumelib.master import split_frontmatter  # noqa: E402

NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
RESERVED = ("anthropic", "claude")
XML_RE = re.compile(r"<[^>]+>")


def _check_frontmatter(path: Path, findings: list) -> None:
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    name = meta.get("name", "")
    description = meta.get("description", "")

    if not NAME_RE.match(name):
        findings.append(Finding(
            "bad_name", f"{path}: name {name!r} must be 1-64 chars of [a-z0-9-]"))
    if any(word in name.lower() for word in RESERVED):
        findings.append(Finding(
            "reserved_word", f"{path}: name {name!r} contains a reserved word"))
    if not description.strip():
        findings.append(Finding("empty_description", f"{path}: description is empty"))
    elif len(description) > 1024:
        findings.append(Finding(
            "long_description", f"{path}: description is {len(description)} chars (max 1024)"))
    for field_name, value in (("name", name), ("description", description)):
        if XML_RE.search(value):
            findings.append(Finding(
                "xml_in_frontmatter", f"{path}: {field_name} contains an XML tag"))


def check(plugin_dir: Path) -> list:
    plugin_dir = Path(plugin_dir)
    findings = []

    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        findings.append(Finding("missing_manifest", f"{manifest} does not exist"))
    else:
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(Finding("bad_manifest", f"{manifest}: {exc}"))
            data = {}
        for key in ("name", "description", "version"):
            if not data.get(key):
                findings.append(Finding("missing_field", f"{manifest}: missing {key!r}"))

    for path in sorted(plugin_dir.glob("skills/*/SKILL.md")):
        _check_frontmatter(path, findings)
    for path in sorted(plugin_dir.glob("agents/*.md")):
        _check_frontmatter(path, findings)

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin", type=Path, nargs="?", default=Path("plugin"))
    args = parser.parse_args()

    findings = check(args.plugin)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} manifest finding(s).")
        return 1
    print("manifest: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
