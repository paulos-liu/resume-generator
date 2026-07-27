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

FIRST_PERSON_RE = re.compile(r"\b(I|me|my|mine|we|our|us)\b", re.IGNORECASE)

# A bare "I" is ambiguous: the pronoun, or the level in "Software Engineer I".
# Flagging the numeral would force anyone whose title carries a level to write
# around it, and a promotion sequence (I -> II -> III) is usually the clearest
# seniority signal a resume has -- losing that to a false positive is the wrong
# trade. Only "I" needs disambiguating: "II" and "III" never match the pronoun
# pattern, because \bI\b cannot match where another I follows. The preceding
# word settles it, since the pronoun does not follow a job-title noun.
LEVEL_NOUNS = frozenset((
    "engineer", "developer", "analyst", "scientist", "designer", "architect",
    "manager", "consultant", "associate", "specialist", "administrator",
    "programmer", "technician", "level", "grade", "tier", "band",
))
_WORD_BEFORE_RE = re.compile(r"([A-Za-z]+)\W*$")


def _is_job_level(text: str, match) -> bool:
    """True when this match is a job level ("Engineer I"), not the pronoun."""
    if match.group(0) != "I":
        return False
    before = _WORD_BEFORE_RE.search(text[:match.start()])
    return bool(before) and before.group(1).lower() in LEVEL_NOUNS


STREET_SUFFIXES = (
    "Ave|Avenue|St|Street|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court|"
    "Pl|Place|Ter|Terrace|Cir|Circle|Hwy|Highway|Pkwy|Parkway|Sq|Square"
)
STREET_ADDRESS_RE = re.compile(
    rf"\b\d{{1,6}}\s+(?:[\w.'-]+\s+){{0,4}}(?:{STREET_SUFFIXES})\b", re.IGNORECASE)

SKILLS_HEADING = "skills"


def _content_lines(text: str) -> list:
    return [line for line in text.splitlines() if line.strip()]


def _is_prose_line(line: str) -> bool:
    """True for header/contact lines -- not bullets, not headings.

    The street-address check looks only at these. A street address only ever
    appears in the contact block, and confining the match there keeps bullet
    text like "built a 3 way merge tool" from tripping the suffix list.
    """
    stripped = line.lstrip()
    return bool(stripped) and not stripped.startswith(("- ", "#"))


def _skills_section_has_content(lines: list) -> bool:
    in_skills = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            in_skills = stripped.lstrip("#").strip().lower() == SKILLS_HEADING
        elif in_skills:
            return True
    return False


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
            if _is_job_level(text, match):
                continue
            findings.append(Finding("first_person", f"first person: {match.group(0)!r}"))

    present = {verb.lower() for verb in rules.present_tense_verbs}
    for line in lines:
        if not line.lstrip().startswith("- "):
            continue
        words = line.lstrip()[2:].split()
        if words and words[0].lower() in present:
            findings.append(Finding(
                "present_tense", f"bullet opens in present tense: {words[0]!r}"))

    if rules.ban_street_address:
        for line in lines:
            if not _is_prose_line(line):
                continue
            match = STREET_ADDRESS_RE.search(line)
            if match:
                findings.append(Finding(
                    "street_address",
                    f"street address in contact block: {match.group(0)!r} "
                    "-- use city and state only"))

    if rules.required_link_hosts:
        lowered = text.lower()
        if not any(host.lower() in lowered for host in rules.required_link_hosts):
            findings.append(Finding(
                "missing_profile_link",
                "no profile link; expected one of: "
                + ", ".join(rules.required_link_hosts)))

    if rules.require_skills_line and not _skills_section_has_content(lines):
        findings.append(Finding(
            "missing_skills_line", "no Skills section with content"))

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
