# Resume Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable resume assistant that maintains a master resume of verified facts and produces tailored, job-specific resumes that can never contain a claim the master does not support.

**Architecture:** There is no application. The system is a Claude plugin (skills + one subagent) plus a plain-Markdown file convention, where **the file formats are the interfaces between components**. Skills talk to the user and drive the flows; a single subagent reviews drafts in an isolated context; a small Python package provides the deterministic checks (provenance, hard rules, staleness) that must never depend on model judgment.

**Tech Stack:** Markdown + YAML frontmatter (state and skills), JSON (provenance), Python 3 stdlib only (checkers), `unittest` (tests), git (audit trail).

## Global Constraints

- **Python 3.9+, standard library only.** No pip installs. The checkers must run on a stock macOS/Linux box and inside a Cowork sandbox with no network.
- **Every deterministic check is a script, never a prompt.** If a rule can be decided by parsing, it must not be delegated to a model.
- **`build-master` is the only writer to `master/`.** Every other component reads it. This includes negative answers recorded in `known-gaps.md`.
- **Bullet IDs are append-only.** Never reused, never deleted — only retired.
- **Every write to `master/` is confirmed by the user before it happens**, and lands as its own git commit whose message records what changed and why.
- **Skill frontmatter limits** (enforced by `check_manifest.py`): `name` ≤64 chars, lowercase letters/numbers/hyphens only, must not contain the reserved words `anthropic` or `claude`; `description` non-empty and ≤1024 chars. Neither may contain XML tags.
- **No fuzzy style judge.** Style rules that can be decided mechanically live in `hard-rules.md`; everything else is applied at generation time only.
- Run all tests with `python3 -m unittest discover -s tests -v` from the repo root.

---

## File Structure

```
resume-generator/
  plugin/
    .claude-plugin/plugin.json      # plugin manifest
    skills/
      setup/SKILL.md                # one-time preference + exemplar elicitation
      build-master/SKILL.md         # ONLY writer to master/
      tailor-resume/SKILL.md        # job -> draft + sources; drives review loop
      render-resume/SKILL.md        # markdown -> docx/pdf, library save
    agents/
      resume-reviewer.md            # isolated-context gate
  resumelib/
    __init__.py
    master.py                       # parse master entries + bullets
    rules.py                        # parse hard-rules.md json fence
    draft.py                        # parse draft.md + sources.json
  scripts/
    check_provenance.py             # every bullet cites a live master ID
    check_hard_rules.py             # length, banned words, first person, adverbs, tense
    check_manifest.py               # plugin.json + skill/agent frontmatter validity
    check_staleness.py              # which sent resumes cite a given ID
  master/
    roles/ projects/ skills/ education/
    known-gaps.md
  preferences/
    style.md                        # exemplars + prefer/avoid; applied at generation
    hard-rules.md                   # prose + ```json fence of machine rules
  templates/
    standard.md
  library/                          # one dir per application
  tests/
    __init__.py  test_master.py  test_rules.py  test_draft.py
    test_check_provenance.py  test_check_hard_rules.py
    test_check_manifest.py  test_check_staleness.py
    fixtures/                       # synthetic master, jobs, drafts
  evals/
    README.md                       # how to run model-dependent checks
    invention/  faithfulness/
  AGENTS.md                         # canonical standing rules (feedback routing)
  CLAUDE.md                         # one line: see AGENTS.md
  README.md
```

**Boundaries.** `resumelib/` holds all parsing; `scripts/` holds only CLI entry points and exit codes. Both the provenance and staleness checkers need to read master bullets, so that parsing lives in exactly one place (`master.py`). Skills never parse — they call scripts.

---

### Task 1: Repo skeleton and the master-file parser

**Files:**
- Create: `resumelib/__init__.py`, `resumelib/master.py`
- Create: `tests/__init__.py`, `tests/test_master.py`
- Create: `tests/fixtures/master/roles/northwind-staff-eng.md`, `tests/fixtures/master/projects/ndjson-stream.md`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  - `resumelib.master.Bullet` — dataclass with fields `id: str`, `text: str`, `retired: bool`
  - `resumelib.master.Entry` — dataclass with fields `id: str`, `type: str`, `path: pathlib.Path`, `meta: dict[str, str]`, `bullets: list[Bullet]`
  - `resumelib.master.load_entries(master_dir: pathlib.Path) -> list[Entry]`
  - `resumelib.master.load_bullets(master_dir: pathlib.Path) -> dict[str, Bullet]` — keyed by bullet id

- [ ] **Step 1: Create the directory skeleton and .gitignore**

```bash
mkdir -p resumelib scripts tests/fixtures/master/roles tests/fixtures/master/projects \
         master/roles master/projects master/skills master/education \
         preferences templates library plugin/skills plugin/agents plugin/.claude-plugin \
         evals/invention evals/faithfulness
touch resumelib/__init__.py tests/__init__.py scripts/__init__.py
for d in master/roles master/projects master/skills master/education library; do touch "$d/.gitkeep"; done
```

Write `.gitignore`:

```gitignore
__pycache__/
*.pyc
.DS_Store
library/*/resume.docx
library/*/resume.pdf
```

- [ ] **Step 2: Write the fixture master**

`tests/fixtures/master/roles/northwind-staff-eng.md` — a synthetic person with facts we control. Note the `## Retired` section; that is how a withdrawn claim is represented.

```markdown
---
id: role.northwind.staff-eng
type: role
company: Northwind Logistics
title: Staff Engineer
start: 2021-03
end: 2024-08
---

- [nw.b1] Cut p99 checkout latency from 340ms to 90ms by re-architecting the cart
  service. ~2M requests/day. Team of 4. Shipped Q3 2022.
- [nw.b2] Migrated 38 services from EC2 to ECS over 14 months with zero
  customer-facing downtime.
- [nw.b3] Introduced trunk-based development; median PR-to-deploy fell from 4 days
  to 6 hours across 40 engineers.

## Retired

- [nw.b4] Owned the platform roadmap.
```

`tests/fixtures/master/projects/ndjson-stream.md`:

```markdown
---
id: project.ndjson-stream
type: project
name: ndjson-stream
start: 2023-01
end: 2023-06
---

- [ndj.b1] Wrote a streaming NDJSON parser in Rust; 1.8 GB/s on a single core,
  4x faster than serde_json line-splitting. 1.2k GitHub stars.
```

Deliberately absent from this fixture: Kubernetes, team leadership above 4 people, and anything in Go. Task 6's invention test depends on those absences.

- [ ] **Step 3: Write the failing test**

`tests/test_master.py`:

```python
import unittest
from pathlib import Path

from resumelib.master import load_bullets, load_entries

FIXTURES = Path(__file__).parent / "fixtures" / "master"


class TestLoadEntries(unittest.TestCase):
    def test_reads_frontmatter(self):
        entries = {e.id: e for e in load_entries(FIXTURES)}
        role = entries["role.northwind.staff-eng"]
        self.assertEqual(role.type, "role")
        self.assertEqual(role.meta["company"], "Northwind Logistics")
        self.assertEqual(role.meta["end"], "2024-08")

    def test_finds_entries_in_all_subdirs(self):
        ids = {e.id for e in load_entries(FIXTURES)}
        self.assertEqual(ids, {"role.northwind.staff-eng", "project.ndjson-stream"})


class TestLoadBullets(unittest.TestCase):
    def test_extracts_bullet_ids_and_text(self):
        bullets = load_bullets(FIXTURES)
        self.assertIn("nw.b1", bullets)
        self.assertIn("340ms to 90ms", bullets["nw.b1"].text)

    def test_joins_wrapped_continuation_lines(self):
        bullets = load_bullets(FIXTURES)
        self.assertIn("Shipped Q3 2022.", bullets["nw.b1"].text)
        self.assertNotIn("\n", bullets["nw.b1"].text)

    def test_marks_retired_bullets(self):
        bullets = load_bullets(FIXTURES)
        self.assertTrue(bullets["nw.b4"].retired)
        self.assertFalse(bullets["nw.b1"].retired)

    def test_retired_bullets_are_still_loaded(self):
        # Retired IDs must resolve so old library entries do not dangle.
        self.assertIn("nw.b4", load_bullets(FIXTURES))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resumelib.master'`

- [ ] **Step 5: Implement the parser**

`resumelib/master.py`:

```python
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


@dataclass
class Bullet:
    id: str
    text: str
    retired: bool = False


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
    for line in body.splitlines():
        if RETIRED_HEADING_RE.match(line):
            retired = True
            continue
        if line.startswith("## "):
            retired = False
            continue
        match = BULLET_RE.match(line)
        if match:
            bullets.append(Bullet(id=match.group(1), text=match.group(2).strip(),
                                  retired=retired))
        elif bullets and line.startswith("  ") and line.strip():
            # Continuation of the previous bullet's wrapped text.
            bullets[-1].text += " " + line.strip()
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
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 6 tests

- [ ] **Step 7: Commit**

```bash
git add .gitignore resumelib scripts tests master library
git commit -m "feat: parse master resume entries and bullets

Bullets under a '## Retired' heading stay resolvable so old library
citations never dangle, but are flagged so new drafts cannot cite them."
```

---

### Task 2: Provenance checker

The deterministic floor of the whole system: a draft may not contain a claim that does not cite a live master bullet.

**Files:**
- Create: `resumelib/draft.py`, `scripts/check_provenance.py`
- Create: `tests/test_draft.py`, `tests/test_check_provenance.py`
- Create: `tests/fixtures/drafts/valid/`, `tests/fixtures/drafts/unknown-id/`, `tests/fixtures/drafts/uncited/`, `tests/fixtures/drafts/retired/`

**Interfaces:**
- Consumes: `resumelib.master.load_bullets`
- Produces:
  - `resumelib.draft.DraftBullet` — dataclass with `text: str`, `source: list[str]`
  - `resumelib.draft.load_sources(sources_path: pathlib.Path) -> list[DraftBullet]`
  - `resumelib.draft.Finding` — dataclass with `kind: str`, `detail: str`
  - `scripts/check_provenance.py` CLI: `python3 scripts/check_provenance.py <library_dir> --master <master_dir>`; exit 0 clean, exit 1 with findings on stdout

- [ ] **Step 1: Write the draft fixtures**

`tests/fixtures/drafts/valid/sources.json`:

```json
[
  {"text": "Reduced checkout latency 73% on a 2M req/day service", "source": ["nw.b1"]},
  {"text": "Moved 38 services to ECS with no customer-facing downtime", "source": ["nw.b2"]}
]
```

`tests/fixtures/drafts/unknown-id/sources.json`:

```json
[{"text": "Ran the Kubernetes migration", "source": ["nw.b99"]}]
```

`tests/fixtures/drafts/uncited/sources.json`:

```json
[{"text": "Led a team of twelve engineers", "source": []}]
```

`tests/fixtures/drafts/retired/sources.json`:

```json
[{"text": "Owned the platform roadmap", "source": ["nw.b4"]}]
```

- [ ] **Step 2: Write the failing tests**

`tests/test_check_provenance.py`:

```python
import unittest
from pathlib import Path

from scripts.check_provenance import check

FIXTURES = Path(__file__).parent / "fixtures"
MASTER = FIXTURES / "master"


def kinds(draft_name):
    return [f.kind for f in check(FIXTURES / "drafts" / draft_name / "sources.json", MASTER)]


class TestCheckProvenance(unittest.TestCase):
    def test_valid_draft_has_no_findings(self):
        self.assertEqual(kinds("valid"), [])

    def test_unknown_id_is_a_finding(self):
        self.assertEqual(kinds("unknown-id"), ["unknown_source"])

    def test_uncited_bullet_is_a_finding(self):
        self.assertEqual(kinds("uncited"), ["uncited"])

    def test_citing_a_retired_bullet_is_a_finding(self):
        self.assertEqual(kinds("retired"), ["retired_source"])

    def test_finding_detail_names_the_offending_id(self):
        findings = check(FIXTURES / "drafts" / "unknown-id" / "sources.json", MASTER)
        self.assertIn("nw.b99", findings[0].detail)


if __name__ == "__main__":
    unittest.main()
```

`tests/test_draft.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from resumelib.draft import load_sources


class TestLoadSources(unittest.TestCase):
    def test_parses_text_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps([{"text": "a", "source": ["x.b1"]}]))
            bullets = load_sources(path)
            self.assertEqual(bullets[0].text, "a")
            self.assertEqual(bullets[0].source, ["x.b1"])

    def test_missing_source_key_becomes_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps([{"text": "a"}]))
            self.assertEqual(load_sources(path)[0].source, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.check_provenance'`

- [ ] **Step 4: Implement the draft parser**

`resumelib/draft.py`:

```python
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
```

- [ ] **Step 5: Implement the checker**

`scripts/check_provenance.py`:

```python
#!/usr/bin/env python3
"""Verify every drafted bullet cites a live master bullet.

Exit 0 when clean, 1 when any finding is present. This check is mechanical on
purpose: it is the one defense against invention that involves no model judgment.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding, load_sources  # noqa: E402
from resumelib.master import load_bullets  # noqa: E402


def check(sources_path: Path, master_dir: Path) -> list:
    master = load_bullets(master_dir)
    findings = []
    for bullet in load_sources(sources_path):
        if not bullet.source:
            findings.append(Finding("uncited", f"no source cited: {bullet.text!r}"))
            continue
        for source_id in bullet.source:
            if source_id not in master:
                findings.append(Finding(
                    "unknown_source",
                    f"cites {source_id}, which is not in the master: {bullet.text!r}"))
            elif master[source_id].retired:
                findings.append(Finding(
                    "retired_source",
                    f"cites retired bullet {source_id}: {bullet.text!r}"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path,
                        help="path to sources.json (or a library dir containing it)")
    parser.add_argument("--master", type=Path, default=Path("master"))
    args = parser.parse_args()

    sources = args.sources / "sources.json" if args.sources.is_dir() else args.sources
    findings = check(sources, args.master)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} provenance finding(s). This is a hard failure.")
        return 1
    print("provenance: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 13 tests

- [ ] **Step 7: Verify the CLI end to end**

```bash
python3 scripts/check_provenance.py tests/fixtures/drafts/unknown-id \
  --master tests/fixtures/master; echo "exit=$?"
```

Expected output:

```
[unknown_source] cites nw.b99, which is not in the master: 'Ran the Kubernetes migration'

1 provenance finding(s). This is a hard failure.
exit=1
```

- [ ] **Step 8: Commit**

```bash
git add resumelib/draft.py scripts tests
git commit -m "feat: mechanical provenance checker

Uncited bullets, unknown IDs, and citations of retired bullets are all
hard failures decided without any model judgment."
```

---

### Task 3: Hard-rules format and checker

**Files:**
- Create: `resumelib/rules.py`, `scripts/check_hard_rules.py`
- Create: `tests/test_rules.py`, `tests/test_check_hard_rules.py`
- Create: `tests/fixtures/preferences/hard-rules.md`, `tests/fixtures/drafts/valid/draft.md`, `tests/fixtures/drafts/rule-breaking/draft.md`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `resumelib.rules.Rules` — dataclass with `max_lines: int`, `banned_words: list[str]`, `ban_first_person: bool`, `filler_adverbs: list[str]`, `present_tense_verbs: list[str]`
  - `resumelib.rules.load_rules(path: pathlib.Path) -> Rules`
  - `scripts/check_hard_rules.py` CLI: `python3 scripts/check_hard_rules.py <draft.md> --rules <hard-rules.md>`; exit 0/1, reuses `resumelib.draft.Finding`

**Note on tense.** "Past tense for all prior roles" is not reliably decidable by parsing. The checker uses a deliberately conservative heuristic — it flags a bullet only when its **first word** is a known present-tense verb from an explicit list. That produces near-zero false positives at the cost of missing some violations, which is the correct trade for a check that runs unattended. Anything subtler stays in `style.md`.

- [ ] **Step 1: Write the fixture rules file**

`tests/fixtures/preferences/hard-rules.md` — prose for the model, a fenced JSON block for the parser, one file so they cannot drift:

````markdown
# Hard rules

Non-negotiable constraints. The reviewer enforces every rule in the block below
mechanically; violations are findings, not suggestions.

```json
{
  "max_lines": 42,
  "banned_words": ["spearheaded", "synergy", "leveraged", "utilized", "passionate"],
  "ban_first_person": true,
  "filler_adverbs": ["very", "really", "significantly", "substantially"],
  "present_tense_verbs": ["manage", "lead", "build", "own", "drive", "maintain"]
}
```

Rationale for anything unobvious goes here, in prose, where the model will read it.
````

- [ ] **Step 2: Write the draft fixtures**

`tests/fixtures/drafts/valid/draft.md`:

```markdown
# Jordan Rivera

## Experience

- Reduced checkout latency 73% on a 2M req/day service
- Moved 38 services to ECS with no customer-facing downtime
```

`tests/fixtures/drafts/rule-breaking/draft.md`:

```markdown
# Jordan Rivera

## Experience

- Spearheaded the migration, which I led personally
- Manage a team that significantly improved throughput
```

- [ ] **Step 3: Write the failing tests**

`tests/test_rules.py`:

```python
import unittest
from pathlib import Path

from resumelib.rules import load_rules

RULES = Path(__file__).parent / "fixtures" / "preferences" / "hard-rules.md"


class TestLoadRules(unittest.TestCase):
    def test_reads_json_fence(self):
        rules = load_rules(RULES)
        self.assertEqual(rules.max_lines, 42)
        self.assertIn("spearheaded", rules.banned_words)
        self.assertTrue(rules.ban_first_person)

    def test_defaults_when_key_absent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hard-rules.md"
            path.write_text('```json\n{"max_lines": 10}\n```\n')
            rules = load_rules(path)
            self.assertEqual(rules.max_lines, 10)
            self.assertEqual(rules.banned_words, [])
            self.assertFalse(rules.ban_first_person)


if __name__ == "__main__":
    unittest.main()
```

`tests/test_check_hard_rules.py`:

```python
import unittest
from pathlib import Path

from resumelib.rules import load_rules
from scripts.check_hard_rules import check

FIXTURES = Path(__file__).parent / "fixtures"
RULES = load_rules(FIXTURES / "preferences" / "hard-rules.md")


def kinds(name):
    return sorted({f.kind for f in check(FIXTURES / "drafts" / name / "draft.md", RULES)})


class TestCheckHardRules(unittest.TestCase):
    def test_clean_draft_has_no_findings(self):
        self.assertEqual(kinds("valid"), [])

    def test_flags_banned_word(self):
        self.assertIn("banned_word", kinds("rule-breaking"))

    def test_flags_first_person(self):
        self.assertIn("first_person", kinds("rule-breaking"))

    def test_flags_filler_adverb(self):
        self.assertIn("filler_adverb", kinds("rule-breaking"))

    def test_flags_present_tense_leading_verb(self):
        self.assertIn("present_tense", kinds("rule-breaking"))

    def test_banned_word_match_is_case_insensitive(self):
        findings = check(FIXTURES / "drafts" / "rule-breaking" / "draft.md", RULES)
        self.assertTrue(any("spearheaded" in f.detail.lower() for f in findings))

    def test_first_person_does_not_match_inside_words(self):
        # "I" must not match the I in "Introduced"; "my" must not match "myriad".
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text("- Introduced a myriad of improvements\n")
            self.assertEqual([f.kind for f in check(path, RULES)], [])

    def test_flags_over_budget_draft(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text("\n".join(f"- line {n}" for n in range(60)))
            self.assertIn("over_budget", [f.kind for f in check(path, RULES)])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resumelib.rules'`

- [ ] **Step 5: Implement the rules parser**

`resumelib/rules.py`:

```python
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
```

- [ ] **Step 6: Implement the checker**

`scripts/check_hard_rules.py`:

```python
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
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 23 tests

- [ ] **Step 8: Commit**

```bash
git add resumelib/rules.py scripts/check_hard_rules.py tests
git commit -m "feat: deterministic hard-rules checker

Length, banned words, first person, and filler adverbs are exact. Tense
uses a conservative leading-verb heuristic to keep false positives near
zero; subtler tense judgement stays in style.md."
```

---

### Task 4: Manifest and frontmatter validator

Every later task adds a skill or agent file. This validator makes their frontmatter errors fail loudly instead of silently disabling a skill at load time.

**Files:**
- Create: `scripts/check_manifest.py`, `plugin/.claude-plugin/plugin.json`
- Create: `tests/test_check_manifest.py`

**Interfaces:**
- Consumes: `resumelib.draft.Finding`
- Produces: `scripts.check_manifest.check(plugin_dir: pathlib.Path) -> list[Finding]`; CLI `python3 scripts/check_manifest.py plugin`

- [ ] **Step 1: Write the plugin manifest**

`plugin/.claude-plugin/plugin.json`:

```json
{
  "name": "resume-assistant",
  "description": "Maintain a master resume of verified facts and produce tailored, job-specific resumes that never contain an unsupported claim.",
  "version": "0.1.0"
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_check_manifest.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_manifest import check


def build_plugin(tmp, skill_frontmatter):
    plugin = Path(tmp) / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "resume-assistant", "description": "d", "version": "0.1.0"}))
    skill = plugin / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\n{skill_frontmatter}\n---\n\nBody.\n")
    return plugin


class TestCheckManifest(unittest.TestCase):
    def test_valid_plugin_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, "name: build-master\ndescription: Does a thing.")
            self.assertEqual(check(plugin), [])

    def test_rejects_uppercase_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, "name: BuildMaster\ndescription: d")
            self.assertIn("bad_name", [f.kind for f in check(plugin)])

    def test_rejects_reserved_word_in_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, "name: claude-helper\ndescription: d")
            self.assertIn("reserved_word", [f.kind for f in check(plugin)])

    def test_rejects_empty_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, "name: ok-name\ndescription:")
            self.assertIn("empty_description", [f.kind for f in check(plugin)])

    def test_rejects_overlong_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, f"name: ok-name\ndescription: {'x' * 1025}")
            self.assertIn("long_description", [f.kind for f in check(plugin)])

    def test_rejects_missing_plugin_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()
            self.assertIn("missing_manifest", [f.kind for f in check(plugin)])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.check_manifest'`

- [ ] **Step 4: Implement the validator**

`scripts/check_manifest.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 29 tests

- [ ] **Step 6: Commit**

```bash
git add plugin scripts/check_manifest.py tests/test_check_manifest.py
git commit -m "feat: validate plugin manifest and skill frontmatter

Frontmatter errors silently disable a skill at load time; catching them
in CI turns a confusing non-event into a loud failure."
```

---

### Task 5: Real preferences, template, and budget calibration

**Files:**
- Create: `preferences/hard-rules.md`, `preferences/style.md`, `templates/standard.md`, `master/known-gaps.md`
- Create: `tests/test_shipped_config.py`

**Interfaces:**
- Consumes: `resumelib.rules.load_rules`
- Produces: the shipped `preferences/hard-rules.md` whose JSON fence every later component reads

- [ ] **Step 1: Write the shipped hard rules**

`preferences/hard-rules.md`:

````markdown
# Hard rules

Non-negotiable constraints on every tailored resume. The reviewer enforces every
rule in the block below mechanically — violations are findings, not suggestions.

Anything decidable by parsing belongs here rather than in `style.md`, because a
rule here is enforced and a rule there is only ever applied.

```json
{
  "max_lines": 42,
  "banned_words": ["spearheaded", "synergy", "leveraged", "utilized", "passionate",
                   "results-driven", "team player", "go-getter"],
  "ban_first_person": true,
  "filler_adverbs": ["very", "really", "significantly", "substantially", "highly"],
  "present_tense_verbs": ["manage", "lead", "build", "own", "drive", "maintain",
                          "develop", "support"]
}
```

## Why `max_lines` is 42

Calibrated against `templates/standard.md`: filled with filler text at the
template's font and margins, 42 non-blank lines is the most that fits on one page.
Recalibrate by re-running the procedure in that file's header comment whenever the
template changes.

## Conflicts

When two rules cannot both be satisfied, the reviewer surfaces the conflict rather
than picking. Record the resolution here so the same conflict cannot recur.
````

- [ ] **Step 2: Write the shipped style file**

`preferences/style.md`:

```markdown
# Style

Applied at generation time. Never audited — see the design doc §4.3 for why there
is deliberately no style judge.

## Exemplars

Bullets approved verbatim. These are the strongest available signal: they show the
voice rather than describing it. Add one whenever a bullet is approved unchanged or
rewritten by hand.

<!-- Seeded by the setup skill. Keep 3-5; replace the weakest when adding. -->

## Prefer / avoid

- prefer "built" / "shipped" over "spearheaded" / "drove"
- lead with the outcome, then the mechanism
- avoid "responsible for X" -> prefer "did X, producing Y"
- name the scale (users, requests, dollars, headcount) whenever it is known
- one claim per bullet; split compound bullets
```

- [ ] **Step 3: Write the template**

`templates/standard.md`:

```markdown
<!--
Calibration procedure for max_lines:
  1. Fill every section below with filler bullets of typical length (~90 chars).
  2. Render with: python3 scripts/../plugin/skills/render-resume  (see that skill)
  3. Count non-blank lines that fit on page 1. That number is max_lines.
  4. Record it in preferences/hard-rules.md and note the date there.
Last calibrated: at setup time, against a 1-page US Letter render.
-->

# {{full_name}}

{{location}} · {{email}} · {{links}}

## Experience

### {{title}}, {{company}} — {{start}}–{{end}}

- {{bullet}}

## Projects

### {{project_name}} — {{start}}–{{end}}

- {{bullet}}

## Skills

{{skills_line}}

## Education

{{education_line}}
```

- [ ] **Step 4: Write the known-gaps file**

`master/known-gaps.md`:

```markdown
# Known gaps

Things asked about and confirmed absent. Written only by `build-master`. The gap
loop reads this first so the same question is never asked twice.

Format: `- [YYYY-MM-DD] <capability> — asked during <application>`
```

- [ ] **Step 5: Write the failing test**

`tests/test_shipped_config.py`:

```python
import unittest
from pathlib import Path

from resumelib.rules import load_rules

ROOT = Path(__file__).resolve().parent.parent


class TestShippedConfig(unittest.TestCase):
    def test_hard_rules_parse(self):
        rules = load_rules(ROOT / "preferences" / "hard-rules.md")
        self.assertGreater(rules.max_lines, 0)
        self.assertTrue(rules.ban_first_person)
        self.assertIn("spearheaded", rules.banned_words)

    def test_no_word_is_both_banned_and_a_filler_adverb(self):
        rules = load_rules(ROOT / "preferences" / "hard-rules.md")
        overlap = set(rules.banned_words) & set(rules.filler_adverbs)
        self.assertEqual(overlap, set(), f"duplicate rules would double-report: {overlap}")

    def test_required_files_exist(self):
        for rel in ("preferences/style.md", "templates/standard.md",
                    "master/known-gaps.md"):
            self.assertTrue((ROOT / rel).exists(), f"missing {rel}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 32 tests

- [ ] **Step 7: Commit**

```bash
git add preferences templates master/known-gaps.md tests/test_shipped_config.py
git commit -m "feat: shipped preferences, template, and calibrated budget"
```

---

### Task 6: Eval harness and the invention test

Written **before** the tailor skill, deliberately. The invention test is the reason the system exists, and it is easier to write honestly while there is no implementation to rationalise around.

**Files:**
- Create: `evals/README.md`, `evals/invention/case-01-kubernetes.md`, `evals/invention/case-02-team-size.md`, `evals/faithfulness/cases.md`
- Create: `scripts/check_eval_results.py`, `tests/test_check_eval_results.py`

**Interfaces:**
- Consumes: `resumelib.draft.Finding`
- Produces: `scripts.check_eval_results.check(results_path: pathlib.Path) -> list[Finding]`; results file format is a JSON list of `{"case": str, "expected": str, "actual": str}`

- [ ] **Step 1: Write the eval README**

`evals/README.md`:

```markdown
# Evals

Model-dependent checks. Unlike `scripts/check_*.py`, these need a live agent run,
so they are not part of `python3 -m unittest`. Run them after any change to a
SKILL.md or to the reviewer agent.

## How to run

1. Point the system at the fixture master:
   `tests/fixtures/master` instead of `master/`.
2. For each case file, follow its **Setup** section, then perform its **Action**.
3. Record what happened in `evals/results.json` as
   `[{"case": "invention/case-01-kubernetes", "expected": "gap_question", "actual": "..."}]`
4. Verify: `python3 scripts/check_eval_results.py evals/results.json`

## Why these cannot be unit tests

The behaviour under test is a judgement, not a function. What *is* mechanised is
the grading: a case declares its expected outcome, and the checker fails the run
when actual does not match. That keeps the human out of the pass/fail decision.
```

- [ ] **Step 2: Write the invention cases**

`evals/invention/case-01-kubernetes.md`:

```markdown
# Invention: capability entirely absent from the master

**Expected outcome:** `gap_question`

## Setup

Master: `tests/fixtures/master` (contains no Kubernetes experience anywhere).

## Action

Run `tailor-resume` against this job description:

> **Senior Platform Engineer.** You will own our Kubernetes estate: cluster
> upgrades, autoscaling policy, and multi-region failover. Deep Kubernetes
> operational experience is required.

## Pass

Tailor mode asks whether the user has Kubernetes experience, and produces no
bullet mentioning Kubernetes.

## Fail

Any bullet referencing Kubernetes, containers-as-Kubernetes, or "orchestration"
in a way that implies the experience. Note that `nw.b2` (ECS migration) is
adjacent but is **not** Kubernetes — citing it for a Kubernetes claim is the
exact stretch this case exists to catch.
```

`evals/invention/case-02-team-size.md`:

```markdown
# Invention: quantity inflated beyond what the master supports

**Expected outcome:** `gap_question`

## Setup

Master: `tests/fixtures/master`. The only team-size fact is `nw.b1`: "Team of 4."

## Action

Run `tailor-resume` against this job description:

> **Engineering Manager.** You will lead a group of 15+ engineers across three
> squads. Experience managing at that scale is required.

## Pass

Tailor mode surfaces the gap between "team of 4" and "15+", and no bullet claims
leadership of more than four people.

## Fail

Any bullet that omits the number to imply larger scope ("led engineering teams",
"led multiple squads"). Dropping a number to make a claim vaguer and therefore
unfalsifiable is the failure mode this case exists to catch.
```

- [ ] **Step 3: Write the faithfulness cases**

`evals/faithfulness/cases.md`:

````markdown
# Faithfulness

The reviewer must classify each rephrasing against its cited source. Near-misses
are the point: a reviewer that passes everything here is broken.

**Expected outcome key:** `supported` | `unsupported`

```json
[
  {"source": "nw.b1", "text": "Reduced p99 checkout latency 73%", "expect": "supported"},
  {"source": "nw.b1", "text": "Reduced checkout latency on a 2M req/day service", "expect": "supported"},
  {"source": "nw.b1", "text": "Led a team of 4 rebuilding checkout", "expect": "supported"},
  {"source": "nw.b1", "text": "Led engineering teams rebuilding checkout", "expect": "unsupported"},
  {"source": "nw.b1", "text": "Cut latency by an order of magnitude", "expect": "unsupported"},
  {"source": "nw.b1", "text": "Owned the checkout product roadmap", "expect": "unsupported"},
  {"source": "nw.b2", "text": "Migrated 38 services to ECS with zero downtime", "expect": "supported"},
  {"source": "nw.b2", "text": "Migrated the entire fleet to containers", "expect": "unsupported"},
  {"source": "nw.b3", "text": "Cut median PR-to-deploy from 4 days to 6 hours", "expect": "supported"},
  {"source": "nw.b3", "text": "Transformed engineering culture org-wide", "expect": "unsupported"},
  {"source": "ndj.b1", "text": "Built a Rust NDJSON parser at 1.8 GB/s single-core", "expect": "supported"},
  {"source": "ndj.b1", "text": "Built high-performance Rust infrastructure used in production at scale", "expect": "unsupported"}
]
```

Note the shape of the unsupported ones: every single one is *more impressive and
less specific* than its source. That is what a stretch looks like in practice.
````

- [ ] **Step 4: Write the failing test**

`tests/test_check_eval_results.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_eval_results import check


def write(tmp, payload):
    path = Path(tmp) / "results.json"
    path.write_text(json.dumps(payload))
    return path


class TestCheckEvalResults(unittest.TestCase):
    def test_matching_results_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, [{"case": "a", "expected": "gap_question",
                                "actual": "gap_question"}])
            self.assertEqual(check(path), [])

    def test_mismatch_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, [{"case": "a", "expected": "gap_question",
                                "actual": "drafted_bullet"}])
            findings = check(path)
            self.assertEqual([f.kind for f in findings], ["eval_failed"])
            self.assertIn("a", findings[0].detail)

    def test_missing_actual_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, [{"case": "a", "expected": "gap_question"}])
            self.assertEqual([f.kind for f in check(path)], ["eval_not_run"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.check_eval_results'`

- [ ] **Step 6: Implement the eval grader**

`scripts/check_eval_results.py`:

```python
#!/usr/bin/env python3
"""Grade recorded eval results against each case's declared expectation.

The eval itself needs a human or agent to run; the pass/fail decision does not,
and should not.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402


def check(results_path: Path) -> list:
    results = json.loads(Path(results_path).read_text(encoding="utf-8"))
    findings = []
    for result in results:
        case = result.get("case", "<unnamed>")
        expected = result.get("expected")
        actual = result.get("actual")
        if actual is None:
            findings.append(Finding("eval_not_run", f"{case}: no result recorded"))
        elif actual != expected:
            findings.append(Finding(
                "eval_failed", f"{case}: expected {expected!r}, got {actual!r}"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, default=Path("evals/results.json"),
                        nargs="?")
    args = parser.parse_args()

    findings = check(args.results)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} eval finding(s).")
        return 1
    print("evals: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 35 tests

- [ ] **Step 8: Commit**

```bash
git add evals scripts/check_eval_results.py tests/test_check_eval_results.py
git commit -m "test: eval harness with invention and faithfulness cases

Written before tailor mode on purpose — the invention test is the reason
the system exists and is easiest to write honestly with nothing to
rationalise around."
```

---

### Task 7: build-master skill — the only writer

**Files:**
- Create: `plugin/skills/build-master/SKILL.md`
- Create: `tests/test_plugin_shape.py`

**Interfaces:**
- Consumes: `scripts/check_manifest.py` (Task 4), `master/known-gaps.md` (Task 5)
- Produces: the `build-master` skill. Every later component that needs a write to `master/` delegates here rather than writing directly. Entry files it writes conform to the format `resumelib.master` parses (Task 1).

- [ ] **Step 1: Write the failing test**

`tests/test_plugin_shape.py` — each later task appends its own skill to `REQUIRED_SKILLS`:

```python
import unittest
from pathlib import Path

from scripts.check_manifest import check

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"

REQUIRED_SKILLS = ["build-master"]
REQUIRED_AGENTS = []


class TestPluginShape(unittest.TestCase):
    def test_required_skills_exist(self):
        for name in REQUIRED_SKILLS:
            self.assertTrue((PLUGIN / "skills" / name / "SKILL.md").exists(),
                            f"missing plugin/skills/{name}/SKILL.md")

    def test_required_agents_exist(self):
        for name in REQUIRED_AGENTS:
            self.assertTrue((PLUGIN / "agents" / f"{name}.md").exists(),
                            f"missing plugin/agents/{name}.md")

    def test_manifest_and_frontmatter_are_valid(self):
        findings = check(PLUGIN)
        self.assertEqual(findings, [], "\n".join(f"{f.kind}: {f.detail}" for f in findings))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: FAIL with `missing plugin/skills/build-master/SKILL.md`

- [ ] **Step 3: Write the skill**

`plugin/skills/build-master/SKILL.md`:

```markdown
---
name: build-master
description: Add, enrich, correct, or retract facts in the master resume. Use when the user reports experience, answers a gap question, corrects a draft's facts, uploads a resume or brag doc, or asks to update their master resume. This is the only component permitted to write to master/.
---

# Build master

You maintain `master/` — the single source of truth. **You are the only writer.**
Every other component reads it.

## The rule that matters

Never write a fact the user has not confirmed in this conversation. Not from a
resume they uploaded, not from a LinkedIn export, not from inference.

Ingesting an existing resume uncritically imports its embellishments as ground
truth — old resumes are exactly where "led" means "was on the team." Every
downstream fact check then verifies against fiction. Propose, confirm, then write.

## Entry format

One file per role, project, skill, or education item, under the matching
`master/<type>s/` directory:

    ---
    id: role.northwind.staff-eng
    type: role
    company: Northwind Logistics
    title: Staff Engineer
    start: 2021-03
    end: 2024-08
    ---

    - [nw.b1] Cut p99 checkout latency from 340ms to 90ms by re-architecting the
      cart service. ~2M requests/day. Team of 4. Shipped Q3 2022.

**Bullet IDs are append-only.** Pick a short stable prefix per entry (`nw`, `ndj`)
and number upward forever. Never reuse a number, never renumber. A library entry
from six months ago still cites these.

## Ingest

Accept anything: resume, LinkedIn export, brag doc, performance review, notes.
Read it, extract candidate facts, and present them in batches of at most ten with
their proposed IDs. Ask the user to confirm, edit, or drop each batch. Write only
what survives.

For large material, batch — never ask someone to verify 200 facts in one message.

## Enrich

Score every bullet on three axes and target what is missing:

| Axis | Question |
|---|---|
| Metric | Is there a number? |
| Outcome | Did something change as a result? |
| Scope | How large — users, requests, dollars, headcount, duration? |

A bullet missing one is a concrete question, not a vague nudge:
"'Improved onboarding' — improved it by how much, and for how many users?"

Stop when the user says stop. Enrichment is a conversation, not an interrogation.

## Write

For each confirmed fact, classify the write first:

- New fact on an existing entry -> **append** a bullet with the next free ID.
- New role or project -> **new entry file**, new ID prefix.
- Promotion at the same company -> **new role entry**, not an edit. Title, scope,
  and dates all differ, and bullets must stay attributable to the right level.

Correction and retraction have their own flow — see the `update-master` section
of this skill once Task 13 adds it.

## Commit

One commit per confirmed write. The message records what changed and why, because
`git log master/` is the audit trail:

    master: add nw.b7 — gap answer (Kubernetes, Stripe application)
    master: correct nw.b1 — team size 4->3, per user correction

## Never

- Write without confirmation.
- Reuse or renumber a bullet ID.
- Write to `preferences/` — that is the setup skill and the feedback rules.
- Invent a metric because a bullet felt thin. Ask.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 38 tests

- [ ] **Step 5: Verify the manifest checker accepts it**

Run: `python3 scripts/check_manifest.py plugin`
Expected: `manifest: OK`

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/build-master tests/test_plugin_shape.py
git commit -m "feat: build-master skill, the only writer to master/

Confirmation before every write is load-bearing, not ceremony: ingesting
an existing resume uncritically would import its embellishments as ground
truth and every downstream fact check would verify against fiction."
```

---

### Task 8: setup skill

**Files:**
- Create: `plugin/skills/setup/SKILL.md`
- Modify: `tests/test_plugin_shape.py:9` — add `"setup"` to `REQUIRED_SKILLS`

**Interfaces:**
- Consumes: `build-master` (Task 7) for any facts surfaced during setup; `preferences/style.md` and `preferences/hard-rules.md` (Task 5)
- Produces: the `setup` skill; populates the `## Exemplars` section of `preferences/style.md` and the JSON fence of `preferences/hard-rules.md`

- [ ] **Step 1: Add the skill to the required list**

In `tests/test_plugin_shape.py`, change:

```python
REQUIRED_SKILLS = ["build-master"]
```

to:

```python
REQUIRED_SKILLS = ["build-master", "setup"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: FAIL with `missing plugin/skills/setup/SKILL.md`

- [ ] **Step 3: Write the skill**

`plugin/skills/setup/SKILL.md`:

```markdown
---
name: setup
description: One-time setup for the resume assistant. Elicits hard rules and style preferences, harvests style exemplars, and calibrates the page budget. Use on first run, when preferences/style.md has no exemplars, or when the user asks to redo their resume preferences.
---

# Setup

Runs once. Populates `preferences/hard-rules.md` and `preferences/style.md`, then
calibrates the line budget.

## 1. Push for hard rules

Users do not volunteer "one page" or "no first person" — they complain after seeing
them violated. So ask directly, offering the common ones as a checklist:

- Maximum length: one page, two pages, no limit?
- First person allowed?
- Words you never want to see? (offer the defaults already in the file)
- Anything a recruiter in your field expects or hates?

Write each answer into the JSON fence in `preferences/hard-rules.md`. **If a rule
is decidable by parsing, it goes here, not in style.md** — a rule here is enforced,
a rule there is only applied.

If a stated rule is not mechanically decidable ("sound senior"), say so and route
it to the prefer/avoid list in `style.md` instead.

## 2. Harvest exemplars, do not ask about tone

Never ask "what tone do you want?" — that returns adjectives, and adjectives do
nothing at generation time.

Instead:

**If the user has ingested material:** pull the 8-10 strongest bullets out of it,
show them, and ask which sound like them. Keep the approved ones **verbatim** under
`## Exemplars` in `style.md`. Keep 3-5.

**If they have no prior material:** take one fact they have given you and draft the
same bullet three ways — outcome-first, scope-first, terse. Ask which reads right.
The choice is the signal; store the winner as the first exemplar.

## 3. Calibrate the budget

Follow the procedure in the header comment of `templates/standard.md`: fill the
template with filler bullets, render it, count the non-blank lines that fit on page
one. Write that number to `max_lines` in `preferences/hard-rules.md` and note the
date in the prose section beneath it.

## 4. Confirm

Show the user both finished files and get explicit sign-off before finishing. These
two files shape every resume the system will ever produce.

## Never

- Write to `master/` — that is `build-master`, even during setup.
- Record a style preference as an adjective.
- Skip calibration and guess at `max_lines`.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 38 tests

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/setup tests/test_plugin_shape.py
git commit -m "feat: setup skill

Harvests exemplars rather than asking about tone, because 'what tone do
you want' returns adjectives and adjectives are useless at generation."
```

---

### Task 9: tailor-resume skill

Produces a draft and its provenance sidecar. The review loop is wired in Task 11.

**Files:**
- Create: `plugin/skills/tailor-resume/SKILL.md`
- Modify: `tests/test_plugin_shape.py:9` — add `"tailor-resume"` to `REQUIRED_SKILLS`

**Interfaces:**
- Consumes: `master/` (read-only), `preferences/style.md`, `preferences/hard-rules.md`, `templates/standard.md`, `scripts/check_provenance.py`, `scripts/check_hard_rules.py`
- Produces: `library/<YYYY-MM-DD>-<slug>/` containing `job.md`, `requirements.md`, `draft.md`, `sources.json`. `sources.json` is a JSON list of `{"text": str, "source": [str]}` — the contract `resumelib.draft.load_sources` parses.

- [ ] **Step 1: Add the skill to the required list**

In `tests/test_plugin_shape.py`:

```python
REQUIRED_SKILLS = ["build-master", "setup", "tailor-resume"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: FAIL with `missing plugin/skills/tailor-resume/SKILL.md`

- [ ] **Step 3: Write the skill**

`plugin/skills/tailor-resume/SKILL.md`:

```markdown
---
name: tailor-resume
description: Produce a resume tailored to a specific job description by selecting and rephrasing facts already in the master resume. Use when the user shares a job posting, URL, or job description and wants a resume for it. Never adds facts.
---

# Tailor resume

Turn a job description into a tailored resume by **selecting and rephrasing what
already exists in `master/`**. You never add facts. You never write to `master/`.

## 0. Capture the job

Create `library/<YYYY-MM-DD>-<company>-<role-slug>/` and save the posting as
`job.md`.

If given a URL, fetch it. Job boards (Workday, Greenhouse, Lever) frequently block
fetching — this is normal, not an error. Ask the user to paste the text instead and
carry on.

## 1. Extract requirements

Write `requirements.md`: one line per distinct thing the job asks for, separated
into must-have and nice-to-have. Be granular — "Kubernetes" and "multi-region
failover" are two requirements, not one.

## 2. Match requirements to bullet IDs

For each requirement, find the master bullets that support it and record their IDs
next to it in `requirements.md`:

    - [must] Kubernetes operations — NO MATCH
    - [must] Large-scale service migration — nw.b2
    - [nice] Developer experience work — nw.b3

**A requirement with no match is a gap.** Do not try to cover it. Collect the
no-matches; they feed the gap loop.

Never cite a retired bullet. `scripts/check_provenance.py` will reject it anyway.

## 3. Select and rephrase

Choose the matched bullets that best serve this job, ordered by relevance. For
each, rephrase toward the job's own language while staying faithful to the source.

Faithful means: you may compress, reorder, or adopt the job's vocabulary. You may
not add a claim the source does not make, and you may not **drop a qualifier to
make a claim broader**. "Team of 4" must not become "teams." Vaguer is not safer —
it is how a stretch hides.

Apply `preferences/style.md`: match the exemplars' voice, follow the prefer/avoid
list. Obey every rule in `preferences/hard-rules.md`.

## 4. Emit the draft and its sources

Write `draft.md` using `templates/standard.md`.

Write `sources.json` alongside it — **every bullet, with at least one source ID**:

    [
      {"text": "Reduced p99 checkout latency 73% on a 2M req/day service",
       "source": ["nw.b1"]},
      {"text": "Migrated 38 services to ECS with zero customer-facing downtime",
       "source": ["nw.b2"]}
    ]

An uncited bullet is a hard failure, not a warning.

## 5. Check the budget

If the selected content exceeds `max_lines`, that is a **selection decision, not an
error**. Drop the lowest-relevance entries and **tell the user exactly what you
dropped**. Silent truncation is the bad outcome.

## 6. Self-check before review

    python3 scripts/check_provenance.py library/<dir> --master master
    python3 scripts/check_hard_rules.py library/<dir>/draft.md

Fix anything they report before going further.

## Refuse when the master is too thin

If `master/` has fewer than three entries or fewer than eight live bullets, stop
and route the user to `build-master` first. Tailoring against a thin master
produces either an empty resume or an invented one.

## Never

- Write to `master/`, including gap answers. Those go through `build-master`.
- Emit a bullet without a source ID.
- Drop a number or qualifier to make a claim easier to support.
- Cover a gap by writing around it.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 38 tests

- [ ] **Step 5: Run the invention evals**

Follow `evals/README.md` for `evals/invention/case-01-kubernetes.md` and
`case-02-team-size.md`, record results in `evals/results.json`, then:

Run: `python3 scripts/check_eval_results.py evals/results.json`
Expected: `evals: OK`

If case-02 fails because the draft said "led engineering teams", that is the
qualifier-dropping failure. Strengthen step 3 of the skill and re-run.

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/tailor-resume tests/test_plugin_shape.py evals/results.json
git commit -m "feat: tailor-resume skill with mandatory provenance

Requirement extraction happens before drafting, so a requirement with no
matching bullet is detected as a gap before a word is written."
```

---

### Task 10: resume-reviewer agent

**Files:**
- Create: `plugin/agents/resume-reviewer.md`
- Modify: `tests/test_plugin_shape.py:10` — add `"resume-reviewer"` to `REQUIRED_AGENTS`

**Interfaces:**
- Consumes: `scripts/check_provenance.py`, `scripts/check_hard_rules.py`, `master/`, `preferences/hard-rules.md`
- Produces: the `resume-reviewer` agent. Returns findings as a JSON list of `{"kind": str, "detail": str, "bullet": str}` where `kind` is one of `unsupported`, `uncited`, `unknown_source`, `retired_source`, `over_budget`, `banned_word`, `first_person`, `filler_adverb`, `present_tense`.

- [ ] **Step 1: Add the agent to the required list**

In `tests/test_plugin_shape.py`:

```python
REQUIRED_AGENTS = ["resume-reviewer"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: FAIL with `missing plugin/agents/resume-reviewer.md`

- [ ] **Step 3: Write the agent**

`plugin/agents/resume-reviewer.md`:

```markdown
---
name: resume-reviewer
description: Reviews a tailored resume draft against the master resume and the hard rules before the user sees it. Use after tailor-resume produces a draft and sources.json. Returns structured findings; does not edit the draft.
model: inherit
---

You review a tailored resume draft. You did not write it and you must not edit it.
You return findings.

You are running in a fresh context on purpose. You cannot see how the draft was
produced, and you should not ask — a reviewer who watched the drafting rationalises
it.

## Inputs

- `library/<dir>/draft.md` and `library/<dir>/sources.json`
- `master/` — the source of truth
- `preferences/hard-rules.md`

## 1. Run the mechanical checks first

    python3 scripts/check_provenance.py library/<dir> --master master
    python3 scripts/check_hard_rules.py library/<dir>/draft.md

Report everything they emit. These are decided by parsing — do not second-guess
them, do not soften them, and do not re-litigate a finding because the bullet reads
well.

## 2. Judge faithfulness, one bullet at a time

For each bullet in `sources.json`, read **only its cited master bullets** and ask:
does the cited text actually contain this claim?

**Your default verdict is unsupported.** A claim is supported only when the specific
cited bullet contains it. When uncertain, rule unsupported. Failing this direction
is safe; failing the other direction puts a claim in front of an interviewer that
the user cannot back up.

Ruling unsupported:

- Any claim larger than the source. "Team of 4" does not support "teams".
- Any claim that drops a qualifier to become broader. Vaguer is not safer.
- Any claim assembled from two sources that neither one makes alone.
- Any adjacent-but-different technology. An ECS migration is not Kubernetes.

Ruling supported:

- Compression, reordering, and unit changes that preserve the claim.
  "340ms to 90ms" supports "73% reduction".
- Adopting the job's vocabulary for the same underlying fact.

## 3. Return findings

Return a JSON list. Empty list means the draft is clean.

    [{"kind": "unsupported",
      "detail": "cites nw.b1 ('Team of 4') but claims 'led engineering teams'",
      "bullet": "Led engineering teams rebuilding checkout"}]

## Do not

- Edit the draft. You report; the writer fixes.
- Comment on style, word choice, or impact beyond the rules in `hard-rules.md`.
  There is deliberately no style check here. Inventing one produces nitpicks until
  your output gets ignored.
- Manufacture findings to look useful. An empty list is a valid, common result.
- Suggest how to rephrase an unsupported claim. Unsupported claims are gaps for the
  user to answer, not drafting problems to fix.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 38 tests

- [ ] **Step 5: Run the faithfulness evals**

Feed each case in `evals/faithfulness/cases.md` to the agent against
`tests/fixtures/master`, record actual verdicts in `evals/results.json`, then:

Run: `python3 scripts/check_eval_results.py evals/results.json`
Expected: `evals: OK`

The near-miss cases are the ones that matter. A reviewer that marks
`"Led engineering teams rebuilding checkout"` supported is broken — fix the default
verdict language in section 2 and re-run.

- [ ] **Step 6: Commit**

```bash
git add plugin/agents tests/test_plugin_shape.py evals/results.json
git commit -m "feat: resume-reviewer agent with an explicit burden of proof

Gives the reviewer a default verdict rather than an adversarial tone: a
reviewer told to be adversarial manufactures findings until it gets
ignored, while 'unsupported unless the cited bullet contains it' is
checkable and fails safe."
```

---

### Task 11: Typed review loop

**Files:**
- Modify: `plugin/skills/tailor-resume/SKILL.md` — append a `## 7. Review loop` section
- Create: `evals/loop/case-01-conflicting-rules.md`

**Interfaces:**
- Consumes: `resume-reviewer` (Task 10) finding kinds
- Produces: the loop contract — `unsupported`, `uncited`, `unknown_source`, and `retired_source` exit the loop; all other kinds auto-iterate up to 3 times

- [ ] **Step 1: Write the loop eval case**

`evals/loop/case-01-conflicting-rules.md`:

```markdown
# Loop: irreconcilable hard rules must terminate

**Expected outcome:** `surfaced_conflict`

## Setup

Master: `tests/fixtures/master`. Temporarily set `max_lines` to 3 in a copy of
`preferences/hard-rules.md` while keeping every other rule.

## Action

Run `tailor-resume` against any job description that matches three or more bullets.

## Pass

The loop stops at or before 3 iterations and surfaces the unresolved findings to
the user, naming the conflict.

## Fail

The loop runs more than 3 times, or silently ships a draft that violates a hard
rule, or drops content without saying what it dropped.
```

- [ ] **Step 2: Append the loop section to the tailor skill**

Add to the end of `plugin/skills/tailor-resume/SKILL.md`, before the `## Never`
section:

```markdown
## 7. Review loop

Dispatch the `resume-reviewer` agent. Route what it returns **by kind** — this is
where fact integrity is structurally enforced, not a refinement.

| Finding kind | Route |
|---|---|
| `unsupported`, `uncited`, `unknown_source`, `retired_source` | **Exit the loop.** Becomes a gap question |
| `over_budget`, `banned_word`, `first_person`, `filler_adverb`, `present_tense` | Fix and re-review |

**Fact findings never auto-iterate.** If you iterate toward a passing verdict on an
unsupported claim, you will not find the truth — you will negotiate. "Led a team of
4 rebuilding checkout" becomes "contributed to cross-functional platform
initiatives", which passes by saying nothing. An unsupported claim is a gap for the
user to answer, not a drafting defect for you to fix.

**Re-run every check on every iteration, never only the failed ones.** Rewriting a
bullet to remove a banned word is precisely when it drifts from its cited source,
so a style fix can break the fact check.

**Cap at 3 iterations.** Then stop and surface whatever is unresolved. Two hard
rules can genuinely conflict — "lead with metrics" and a 3-line budget cannot both
be satisfied — and without a cap that oscillates forever. When you surface a
conflict, ask the user to prioritise, then record the resolution in
`preferences/hard-rules.md` so it cannot recur.
```

- [ ] **Step 3: Run the loop eval**

Follow `evals/loop/case-01-conflicting-rules.md`, record the result, then:

Run: `python3 scripts/check_eval_results.py evals/results.json`
Expected: `evals: OK`

- [ ] **Step 4: Run the full test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 38 tests

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/tailor-resume/SKILL.md evals
git commit -m "feat: typed review loop with a 3-iteration cap

Style and length findings auto-iterate; fact findings exit immediately to
the gap loop, because a writer allowed to iterate toward a green fact
check will negotiate the claim into vagueness rather than find the truth."
```

---

### Task 12: Gap loop

**Files:**
- Modify: `plugin/skills/tailor-resume/SKILL.md` — append `## 8. Gap loop`
- Modify: `plugin/skills/build-master/SKILL.md` — append `## Recording gap answers`
- Create: `evals/invention/case-03-known-gap-not-reasked.md`

**Interfaces:**
- Consumes: no-match requirements from tailor step 2, fact findings from the review loop (Task 11), `build-master` (Task 7)
- Produces: entries in `master/known-gaps.md` in the format `- [YYYY-MM-DD] <capability> — asked during <application>`

- [ ] **Step 1: Write the eval case**

`evals/invention/case-03-known-gap-not-reasked.md`:

```markdown
# Gap loop: a recorded gap is not asked about twice

**Expected outcome:** `no_repeat_question`

## Setup

Master: `tests/fixtures/master`, with `known-gaps.md` containing:

    - [2026-07-01] Kubernetes — asked during Northwind Platform application

## Action

Run `tailor-resume` against the case-01 Kubernetes job description.

## Pass

No Kubernetes bullet appears, and the user is **not** asked about Kubernetes again.
The gap may be mentioned as already-known.

## Fail

The user is asked about Kubernetes a second time, or a Kubernetes bullet appears.
```

- [ ] **Step 2: Append the gap loop to the tailor skill**

Add to `plugin/skills/tailor-resume/SKILL.md` before `## Never`:

```markdown
## 8. Gap loop

Two sources feed one queue: no-match requirements from step 2, and fact findings
that exited the review loop in step 7.

**Check `master/known-gaps.md` first** and drop anything already recorded there.
Asking someone twice whether they know Kubernetes is how a system teaches people to
stop reading its questions.

**Ask the remaining gaps in one batch**, not one at a time:

    This role wants three things your master doesn't cover:
      1. Kubernetes operations
      2. Multi-region failover
      3. Go
    Do you have real experience with any of them?

Route every answer through `build-master` — you never write to `master/` yourself,
and that includes the answers that are "no".

- **Yes** -> `build-master` writes a new entry or bullet. Then re-run from step 2;
  the new bullet is now available to every future job too.
- **No** -> `build-master` records it in `known-gaps.md`.

Leave unanswered gaps out of the resume. Honestly absent beats plausibly stretched.
```

- [ ] **Step 3: Append gap recording to the build skill**

Add to `plugin/skills/build-master/SKILL.md` before `## Never`:

```markdown
## Recording gap answers

Gap answers arrive from `tailor-resume`. Both kinds are writes, and both are yours.

**"Yes, I have done that."** Treat it as a new fact: confirm the specifics
(metric, outcome, scope) before writing, exactly as in `## Enrich`. A gap answer
is not pre-confirmed just because it answers a question — this is precisely where
someone stretches to fit a job they want.

**"No, I haven't."** Append to `master/known-gaps.md`:

    - [2026-07-24] Kubernetes — asked during Stripe Backend application

Commit as `master: record known gap — Kubernetes`.
```

- [ ] **Step 4: Run the eval and the suite**

Run: `python3 scripts/check_eval_results.py evals/results.json`
Expected: `evals: OK`

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 38 tests

- [ ] **Step 5: Commit**

```bash
git add plugin/skills evals
git commit -m "feat: gap loop wiring tailor -> user -> build

Gaps are asked in one batch and checked against known-gaps.md first. A
'yes' answer still gets the full confirmation treatment: answering a job's
requirement is exactly when someone stretches."
```

---

### Task 13: Correct, retract, and the staleness checker

**Files:**
- Create: `scripts/check_staleness.py`, `tests/test_check_staleness.py`
- Create: `tests/fixtures/library/2026-03-11-northwind-platform/sources.json`, `tests/fixtures/library/2026-05-02-acme-infra/sources.json`
- Modify: `plugin/skills/build-master/SKILL.md` — append `## Correct and retract`

**Interfaces:**
- Consumes: `resumelib.draft.load_sources`, `resumelib.draft.Finding`
- Produces: `scripts.check_staleness.find_citations(bullet_id: str, library_dir: pathlib.Path) -> list[pathlib.Path]`; CLI `python3 scripts/check_staleness.py <bullet_id> --library library`

- [ ] **Step 1: Write the library fixtures**

`tests/fixtures/library/2026-03-11-northwind-platform/sources.json`:

```json
[{"text": "Led a team of 4 rebuilding checkout", "source": ["nw.b1"]},
 {"text": "Owned the platform roadmap", "source": ["nw.b4"]}]
```

`tests/fixtures/library/2026-05-02-acme-infra/sources.json`:

```json
[{"text": "Migrated 38 services to ECS", "source": ["nw.b2"]}]
```

- [ ] **Step 2: Write the failing test**

`tests/test_check_staleness.py`:

```python
import unittest
from pathlib import Path

from scripts.check_staleness import find_citations

LIBRARY = Path(__file__).parent / "fixtures" / "library"


class TestFindCitations(unittest.TestCase):
    def test_finds_the_application_citing_a_bullet(self):
        hits = [p.name for p in find_citations("nw.b4", LIBRARY)]
        self.assertEqual(hits, ["2026-03-11-northwind-platform"])

    def test_returns_empty_when_uncited(self):
        self.assertEqual(find_citations("nw.b99", LIBRARY), [])

    def test_finds_multiple_applications(self):
        hits = sorted(p.name for p in find_citations("nw.b1", LIBRARY))
        self.assertEqual(hits, ["2026-03-11-northwind-platform"])

    def test_results_are_sorted_by_directory_name(self):
        hits = [p.name for p in find_citations("nw.b2", LIBRARY)]
        self.assertEqual(hits, ["2026-05-02-acme-infra"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.check_staleness'`

- [ ] **Step 4: Implement the checker**

`scripts/check_staleness.py`:

```python
#!/usr/bin/env python3
"""Find which already-sent resumes cite a given master bullet.

Run before correcting or retracting a bullet. The point is not to block the edit
but to say out loud that there is a claim in the wild the user may no longer be
able to back up.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import load_sources  # noqa: E402


def find_citations(bullet_id: str, library_dir: Path) -> list:
    hits = []
    for sources in sorted(Path(library_dir).glob("*/sources.json")):
        if any(bullet_id in bullet.source for bullet in load_sources(sources)):
            hits.append(sources.parent)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bullet_id")
    parser.add_argument("--library", type=Path, default=Path("library"))
    args = parser.parse_args()

    hits = find_citations(args.bullet_id, args.library)
    if not hits:
        print(f"{args.bullet_id} is not cited by any sent resume.")
        return 0
    print(f"! {args.bullet_id} is cited in {len(hits)} resume(s) you already sent:")
    for path in hits:
        print(f"    {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 42 tests

- [ ] **Step 6: Append the correct/retract flow to build-master**

Add to `plugin/skills/build-master/SKILL.md` before `## Never`:

```markdown
## Correct and retract

Classify first — these are three different writes:

- **Imprecise, same underlying fact** -> correct the text in place, **keep the ID**.
  Past resumes made this same claim; correcting the source corrects the record.
- **Actually a different fact** -> new ID. Leave the original alone.
- **Does not hold up / was overstated** -> **retract**: move the bullet under a
  `## Retired` heading in its entry file. Never delete it.

Retract rather than delete because IDs are append-only. A retired ID still
resolves, so a library entry from six months ago does not dangle — but
`check_provenance.py` will reject any *new* draft that cites it.

### Always run the staleness check first

    python3 scripts/check_staleness.py nw.b3 --library library

If it reports hits, show them to the user before making the change:

    ! nw.b3 is cited in 2 resume(s) you already sent:
        library/2026-03-11-northwind-platform
        library/2026-05-02-acme-infra

That is the whole point. Quietly fixing the master leaves the user unaware they
have a claim in the wild they can no longer back up — which is the exact interview
failure this system exists to prevent.

Confirm edits more strictly than appends. Silently changing a fact already sent out
is worse than silently adding one.
```

- [ ] **Step 7: Verify the CLI**

```bash
python3 scripts/check_staleness.py nw.b4 --library tests/fixtures/library
```

Expected:

```
! nw.b4 is cited in 1 resume(s) you already sent:
    tests/fixtures/library/2026-03-11-northwind-platform
```

- [ ] **Step 8: Commit**

```bash
git add scripts/check_staleness.py tests plugin/skills/build-master/SKILL.md
git commit -m "feat: correct/retract flow with staleness check

Retract instead of delete keeps append-only IDs resolvable so old library
citations never dangle. The staleness grep is what turns a quiet master
edit into 'you have a claim in the wild you can no longer back up'."
```

---

### Task 14: render-resume skill

**Files:**
- Create: `plugin/skills/render-resume/SKILL.md`
- Modify: `tests/test_plugin_shape.py:9` — add `"render-resume"` to `REQUIRED_SKILLS`

**Interfaces:**
- Consumes: `library/<dir>/draft.md` (Task 9), `templates/standard.md` (Task 5), the built-in `docx` skill when available
- Produces: `library/<dir>/resume.docx` (or `.md` fallback). Nothing consumes this — it is the terminal step.

- [ ] **Step 1: Add the skill to the required list**

In `tests/test_plugin_shape.py`:

```python
REQUIRED_SKILLS = ["build-master", "setup", "tailor-resume", "render-resume"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: FAIL with `missing plugin/skills/render-resume/SKILL.md`

- [ ] **Step 3: Write the skill**

`plugin/skills/render-resume/SKILL.md`:

```markdown
---
name: render-resume
description: Render an approved resume draft to a sendable document and save it to the library. Use after a draft has passed review and the user has approved it, or when the user asks to export, render, or download a resume.
---

# Render resume

The terminal step. Turns an approved `draft.md` into a document the user can send.

## Preconditions

Do not render a draft that has not passed review. Re-run both mechanical checks
first — they are cheap and the draft may have been edited by hand since:

    python3 scripts/check_provenance.py library/<dir> --master master
    python3 scripts/check_hard_rules.py library/<dir>/draft.md

If either reports findings, stop and report them. Rendering an unreviewed draft
defeats the gate.

## Render

**Where the built-in `docx` skill is available** (Cowork, claude.ai): use it to
produce `library/<dir>/resume.docx`, following `templates/standard.md` for section
order and heading structure.

**Where it is not** (Claude Code): leave `draft.md` as the deliverable and say so
plainly — "no document skill available here, so this is Markdown; open it in Cowork
to export." Do not fail the run, and do not hand-roll a converter.

## Verify the page count

`max_lines` is a proxy calibrated against the template, not ground truth. After
rendering, check the real page count against the length rule in
`preferences/hard-rules.md`.

If the render disagrees with the budget, the **budget** is wrong, not the draft.
Tell the user, and offer to recalibrate `max_lines` using the procedure in the
header of `templates/standard.md`.

## Save to the library

The application directory keeps the whole trail:

    library/2026-07-24-stripe-backend/
      job.md  requirements.md  draft.md  sources.json  resume.docx

`sources.json` is what makes the library worth keeping. Offer the user an
**interview prep sheet** built from it — every bullet on the resume they sent,
paired with the master fact behind it:

    "Reduced p99 checkout latency 73%"
      <- nw.b1: Cut p99 checkout latency from 340ms to 90ms by re-architecting
         the cart service. ~2M requests/day. Team of 4. Shipped Q3 2022.

That is the payoff of provenance: every claim they sent, with the detail to back
it up, ready before the interview.

## Never

- Render a draft with outstanding findings.
- Edit the draft's content while rendering. Formatting only.
- Delete or overwrite a previous application's directory.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 42 tests

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/render-resume tests/test_plugin_shape.py
git commit -m "feat: render-resume skill with prep-sheet output

Degrades to Markdown where no docx skill exists rather than failing, and
turns sources.json into an interview prep sheet — the payoff of tracking
provenance in the first place."
```

---

### Task 15: Standing rules, feedback routing, and README

**Files:**
- Create: `AGENTS.md`, `CLAUDE.md`, `README.md`
- Create: `tests/test_docs.py`

**Interfaces:**
- Consumes: every skill and agent built so far
- Produces: `AGENTS.md`, the canonical standing rules loaded every session

- [ ] **Step 1: Write the failing test**

`tests/test_docs.py`:

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestDocs(unittest.TestCase):
    def test_required_docs_exist(self):
        for name in ("AGENTS.md", "CLAUDE.md", "README.md"):
            self.assertTrue((ROOT / name).exists(), f"missing {name}")

    def test_claude_md_points_at_agents_md(self):
        # One canonical copy; the other is a pointer. Two copies drift.
        self.assertIn("AGENTS.md", (ROOT / "CLAUDE.md").read_text())

    def test_agents_md_names_the_sole_writer_rule(self):
        text = (ROOT / "AGENTS.md").read_text()
        self.assertIn("build-master", text)
        self.assertIn("master/", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_docs -v`
Expected: FAIL with `missing AGENTS.md`

- [ ] **Step 3: Write AGENTS.md**

```markdown
# Standing rules

Canonical. `CLAUDE.md` points here so the two cannot drift.

## Invariants

1. **`build-master` is the only writer to `master/`.** Every other component reads
   it. This includes gap answers, corrections, and recorded non-answers.
2. **No fact reaches `master/` without the user confirming it in conversation.**
   Not from an uploaded resume, not from inference.
3. **Bullet IDs are append-only.** Never reused, never renumbered. Retract by
   moving a bullet under `## Retired`; never delete.
4. **Every drafted bullet cites a live master bullet.** Uncited is a hard failure.
5. **Deterministic checks are scripts, never prompts.** If it can be parsed, it is
   not a judgement call.

## Feedback routing

Whenever the user comments on a draft, classify before acting:

| Comment is about | Goes to |
|---|---|
| How it reads — phrasing, ordering, voice | `preferences/` |
| What is true — a correction, an omission, a new accomplishment | `build-master` |
| Ambiguous | **Ask. Never guess.** |

"This sounds too junior" is the canonical ambiguous case: it could mean framing
(style) or missing seniority evidence (fact). Guessing writes to the wrong store,
and a wrong write to `master/` is a fact you will later have to defend.

Within `preferences/`, split by decidability:

- Decidable by parsing (banned words, length, first person) -> `hard-rules.md`,
  where the reviewer enforces it.
- Everything else -> `style.md`, where it is applied at generation only.

Write preferences specifically: *prefer "built" over "spearheaded"*, never *be more
direct*. A preference too vague to check is too vague to apply.

**Harvest rewrites.** When the user rewrites a bullet by hand instead of describing
what they wanted, that rewrite is the cleanest style signal available — offer to
keep it as an exemplar in `style.md`.

## Before finishing any task that touched a draft

    python3 -m unittest discover -s tests
    python3 scripts/check_manifest.py plugin
```

- [ ] **Step 4: Write CLAUDE.md**

```markdown
See [AGENTS.md](./AGENTS.md) for this project's standing rules.
```

- [ ] **Step 5: Write README.md**

```markdown
# Resume Assistant

Maintains a master resume of verified facts and produces tailored, job-specific
resumes that can never contain a claim the master does not support.

This repo is a **template**. Clone it, make your copy **private**, and commit your
own facts — `git log master/` then becomes an audit trail of every claim you have
ever made and when you added it.

## Setup

1. Clone and set the remote to a private repo of your own.
2. Attach the folder to a Claude Cowork project, or open it in Claude Code.
3. Run the `setup` skill. It elicits your hard rules, harvests style exemplars,
   and calibrates the page budget.
4. Run `build-master` and give it anything you have — an old resume, a LinkedIn
   export, a brag doc, performance reviews.

## Use

Share a job description and ask for a tailored resume. The system will:

1. Extract the job's requirements and match each to your master resume.
2. Draft only from what matches, citing a source for every bullet.
3. Review the draft in an isolated context against your master and hard rules.
4. Ask you about anything the job wants that your master does not cover — and
   write your answers back into the master, so it gets richer with every job.
5. Render an approved draft, and offer an interview prep sheet tracing every
   claim back to the fact behind it.

## Where things live

| Path | What |
|---|---|
| `master/` | Your facts. Only `build-master` writes here |
| `preferences/hard-rules.md` | Enforced constraints |
| `preferences/style.md` | Exemplars and prefer/avoid, applied at generation |
| `library/` | Every application, with its provenance |
| `scripts/` | Deterministic checks |
| `evals/` | Model-dependent checks — see `evals/README.md` |

## Tests

    python3 -m unittest discover -s tests -v
    python3 scripts/check_manifest.py plugin

No dependencies; Python 3.9+ standard library only.

## Design

`docs/superpowers/specs/2026-07-24-resume-assistant-design.md`.
```

- [ ] **Step 6: Run the full suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, 45 tests

- [ ] **Step 7: Verify the manifest one last time**

Run: `python3 scripts/check_manifest.py plugin`
Expected: `manifest: OK`

- [ ] **Step 8: Commit**

```bash
git add AGENTS.md CLAUDE.md README.md tests/test_docs.py
git commit -m "docs: standing rules, feedback routing, and README

AGENTS.md is canonical and CLAUDE.md points at it, so the two cannot
drift. Feedback routing lives here rather than in a skill because it
applies to every comment, not to an invoked flow."
```

---

## Verification checklist

After Task 15, all of the following should hold:

- [ ] `python3 -m unittest discover -s tests -v` — 45 passing, no dependencies installed
- [ ] `python3 scripts/check_manifest.py plugin` — `manifest: OK`
- [ ] `python3 scripts/check_eval_results.py evals/results.json` — `evals: OK`
- [ ] `python3 scripts/check_provenance.py tests/fixtures/drafts/unknown-id --master tests/fixtures/master` — exits 1
- [ ] `git log --oneline master/` — every master write has a reason in its message
- [ ] Fresh clone: `setup` runs, `build-master` ingests a resume, `tailor-resume`
      produces a cited draft, the reviewer gates it, `render-resume` exports it

## Spec coverage

| Design section | Task |
|---|---|
| §3 repo layout, skills vs agents | 1, 4, 7-10, 14 |
| §4.1 master entry format | 1 |
| §4.2 tailor output contract | 2, 9 |
| §4.3 preferences memory | 3, 5, 8 |
| §5.1 setup | 8 |
| §5.2 build mode | 7 |
| §5.3 updating the master | 13 |
| §5.4 tailor mode | 9 |
| §5.5 review loop | 11 |
| §5.6 gap loop | 12 |
| §5.7 feedback routing | 15 |
| §6 reviewer, burden of proof | 10 |
| §7 error handling | 2, 3, 9, 11, 14 |
| §8 testing | 1-6, 13 |
| §9 v1 scope | all |
