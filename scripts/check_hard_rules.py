#!/usr/bin/env python3
"""Enforce every rule in preferences/hard-rules.md against a draft.

All checks are decided by parsing. The tense check is deliberately conservative:
it flags a bullet only when its first word is a known present-tense verb, which
keeps false positives near zero at the cost of missing subtler violations.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402
from resumelib.rules import Rules, load_rules  # noqa: E402

FIRST_PERSON_RE = re.compile(r"\b(I|me|my|mine|we|our|us)\b")


def _content_lines(text: str) -> list:
    return [line for line in text.splitlines() if line.strip()]


def check(draft_path: Path, rules: Rules) -> list:
    text = Path(draft_path).read_text(encoding="utf-8")
    findings = []

    lines = _content_lines(text)
    if rules.max_lines and len(lines) > rules.max_lines:
        findings.append(Finding(
            "over_budget",
            f"draft is {len(lines)} lines, budget is {rules.max_lines}"))

    for word in rules.banned_words:
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            findings.append(Finding("banned_word", f"banned word: {word!r}"))

    for word in rules.filler_adverbs:
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            findings.append(Finding("filler_adverb", f"filler adverb: {word!r}"))

    if rules.ban_first_person:
        for match in FIRST_PERSON_RE.finditer(text):
            findings.append(Finding("first_person", f"first person: {match.group(0)!r}"))

    present = {verb.lower() for verb in rules.present_tense_verbs}
    for line in lines:
        if not line.lstrip().startswith("- "):
            continue
        words = line.lstrip()[2:].split()
        if words and words[0].lower() in present:
            findings.append(Finding(
                "present_tense", f"bullet opens in present tense: {words[0]!r}"))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("--rules", type=Path, default=Path("preferences/hard-rules.md"))
    args = parser.parse_args()

    findings = check(args.draft, load_rules(args.rules))
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} hard-rule finding(s).")
        return 1
    print("hard rules: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
