# career-ops Integration and Batch Tailoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect career-ops as the discovery/scoring/tracking front end by generating its `cv.md` from `master/` and importing scored postings into `library/`, and add a batch mode that tailors many jobs at once while asking each question only once.

**Architecture:** Four deterministic Python scripts in `scripts/` backed by pure functions in `resumelib/`, plus one new plugin skill. No code is added to career-ops; it stays a clean upstream clone. Facts cross out as a generated `cv.md`, jobs cross in as a `library/<slug>/job.md`.

**Tech Stack:** Python 3.9+ standard library only. `unittest`. No dependencies.

## Global Constraints

- Python 3.9+ standard library only. No new dependencies, ever.
- `build-master` remains the only writer to `master/`. No script in this plan writes to `master/`.
- Bullet IDs are append-only. Nothing here allocates or renumbers an ID.
- Test fixtures use the invented persona already in `tests/fixtures/`. Never the user's real name, employers, or dates.
- Scripts exit 0 when clean and 1 when any finding is present, printing `[kind] detail` per finding — match `scripts/check_provenance.py`.
- Parsing logic lives in `resumelib/`; `scripts/*.py` are thin CLI wrappers. Follow the existing import shim: `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` with `# noqa: E402` on the `resumelib` imports.
- Every task ends with the full suite green: `python3 -m unittest discover -s tests` and `python3 scripts/check_manifest.py plugin`.

## Deviation from the spec

The spec put `redact:` blocks in role frontmatter. `resumelib/master.py:split_frontmatter` parses only flat `key: value` scalars and is shared with `check_manifest.py`, so a nested YAML list cannot be represented without changing a parser three other checks depend on.

This plan uses a single `master/redactions.md` instead. It has no frontmatter, so `load_entries` skips it exactly as it already skips `known-gaps.md`. The semantics the spec specified are unchanged — redactions were always applied globally rather than per-role — and a central file matches global scope better than per-role declarations would. Task 6 updates the spec to match.

## File Structure

**Create:**
- `master/redactions.md` — the withheld-term store. No frontmatter, so it is not an entry.
- `resumelib/redactions.py` — parse and apply the store.
- `resumelib/cvexport.py` — render `master/` entries into career-ops `cv.md`.
- `resumelib/batch.py` — gap dedup and round termination.
- `scripts/check_redactions.py` — flag withheld terms in library artifacts.
- `scripts/export_cv_md.py` — write and verify `cv.md`.
- `scripts/import_job.py` — career-ops report → `library/<slug>/job.md`.
- `plugin/skills/batch-tailor/SKILL.md` — the batch loop.
- `evals/batch/case-01-shared-gap-asked-once.md` — the loop's model-dependent behaviour.
- `scripts/sync_shared.py` — allowlisted copy of the shared layer to the public tool repo.
- `tests/test_redactions.py`, `tests/test_cvexport.py`, `tests/test_import_job.py`, `tests/test_batch.py`, `tests/test_sync_shared.py`
- `tests/fixtures/master/redactions.md`, `tests/fixtures/career-ops/` (fixture report + JD)

**Modify:**
- `tests/test_plugin_shape.py` — add `batch-tailor` to `REQUIRED_SKILLS`, and wiring tests for the `setup` career-ops section.
- `plugin/skills/setup/SKILL.md` — optional career-ops onboarding, after the privacy gate.
- `evals/README.md` — add the `batch` category.
- `README.md` — the paths table and a career-ops section.
- `docs/superpowers/specs/2026-08-05-career-ops-integration-design.md` — record the redaction-store deviation.

---

### Task 1: Redaction store and `check_redactions.py`

Ships a complete safety feature on its own: withheld terms become machine-readable and enforceable over library artifacts, independent of anything career-ops.

**Files:**
- Create: `master/redactions.md`
- Modify: `AGENTS.md` (invariant 1 carve-out)
- Create: `resumelib/redactions.py`
- Create: `scripts/check_redactions.py`
- Create: `tests/fixtures/master/redactions.md`
- Test: `tests/test_redactions.py`

**Interfaces:**
- Consumes: `resumelib.draft.Finding` (existing dataclass with `.kind` and `.detail`).
- Produces:
  - `Redaction(term: str, replacement: str | None)` — frozen dataclass
  - `load_redactions(master_dir: Path) -> list[Redaction]`
  - `find_terms(text: str, redactions: list[Redaction]) -> list[Redaction]` — matches present in `text`, case-insensitive
  - `apply_redactions(text: str, redactions: list[Redaction]) -> tuple[str, list[Redaction]]` — returns substituted text and the matched redactions that have no replacement
  - `check(library_dir: Path, master_dir: Path) -> list[Finding]` in `scripts/check_redactions.py`

- [ ] **Step 1: Write the fixture redaction store**

Create `tests/fixtures/master/redactions.md`:

```markdown
# Redactions

Terms withheld from generated artifacts. `- term => replacement` substitutes on
export; `- term` alone has no replacement and fails the export closed.

- Vandelay Industries => a regulated enterprise customer
- Project Halberd
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_redactions.py`:

```python
import unittest
from pathlib import Path

from resumelib.redactions import (
    Redaction, apply_redactions, find_terms, load_redactions,
)
from scripts.check_redactions import check

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MASTER = FIXTURES / "master"


class TestLoad(unittest.TestCase):
    def test_parses_term_and_replacement(self):
        redactions = load_redactions(MASTER)
        self.assertIn(
            Redaction("Vandelay Industries", "a regulated enterprise customer"),
            redactions)

    def test_term_without_arrow_has_no_replacement(self):
        redactions = load_redactions(MASTER)
        self.assertIn(Redaction("Project Halberd", None), redactions)

    def test_missing_store_is_empty_not_an_error(self):
        self.assertEqual(load_redactions(FIXTURES / "master-thin"), [])

    def test_store_is_not_loaded_as_a_master_entry(self):
        # It has no frontmatter id, so load_entries must ignore it the same way
        # it ignores known-gaps.md. Otherwise its lines would reach cv.md.
        from resumelib.master import load_entries
        paths = [e.path.name for e in load_entries(MASTER)]
        self.assertNotIn("redactions.md", paths)


class TestApply(unittest.TestCase):
    def setUp(self):
        self.redactions = load_redactions(MASTER)

    def test_substitutes_a_declared_replacement(self):
        text, blocked = apply_redactions(
            "Shipped for Vandelay Industries.", self.redactions)
        self.assertEqual(text, "Shipped for a regulated enterprise customer.")
        self.assertEqual(blocked, [])

    def test_matches_case_insensitively(self):
        text, _ = apply_redactions(
            "Shipped for vandelay industries.", self.redactions)
        self.assertEqual(text, "Shipped for a regulated enterprise customer.")

    def test_term_with_no_replacement_is_reported_not_substituted(self):
        text, blocked = apply_redactions("Ran Project Halberd.", self.redactions)
        self.assertEqual(text, "Ran Project Halberd.")
        self.assertEqual([r.term for r in blocked], ["Project Halberd"])

    def test_untouched_text_passes_through(self):
        text, blocked = apply_redactions("Cut latency 73%.", self.redactions)
        self.assertEqual(text, "Cut latency 73%.")
        self.assertEqual(blocked, [])

    def test_find_terms_reports_matches_without_substituting(self):
        found = find_terms("Shipped for Vandelay Industries.", self.redactions)
        self.assertEqual([r.term for r in found], ["Vandelay Industries"])


class TestCheck(unittest.TestCase):
    def _library(self, body):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        (tmp / "draft.md").write_text(body, encoding="utf-8")
        return tmp

    def test_clean_draft_has_no_findings(self):
        lib = self._library("- Cut latency 73%.\n")
        self.assertEqual(check(lib, MASTER), [])

    def test_redacted_term_in_draft_is_a_finding(self):
        lib = self._library("- Shipped for Vandelay Industries.\n")
        findings = check(lib, MASTER)
        self.assertEqual([f.kind for f in findings], ["redacted_term"])
        self.assertIn("Vandelay Industries", findings[0].detail)

    def test_cover_letter_is_checked_too(self):
        lib = self._library("- Cut latency 73%.\n")
        (lib / "cover-letter.md").write_text(
            "I ran Project Halberd.\n", encoding="utf-8")
        findings = check(lib, MASTER)
        self.assertEqual([f.kind for f in findings], ["redacted_term"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_redactions -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resumelib.redactions'`

- [ ] **Step 4: Implement `resumelib/redactions.py`**

```python
"""Terms withheld from generated artifacts.

`master/redactions.md` records phrases the user has decided not to publish
without deciding case by case -- a customer name, a project codename. It has no
frontmatter, so `load_entries` skips it exactly as it skips known-gaps.md, and
its lines can never be mistaken for master bullets.

Two verbs, one store. Export *substitutes* (a generated cv.md must never carry a
withheld term into a third-party model). Drafts are only *reported* on, because
naming a term on a real resume is the user's decision to make, not a script's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

STORE_NAME = "redactions.md"
LINE_RE = re.compile(r"^-\s+(.+?)(?:\s+=>\s+(.*))?$")


@dataclass(frozen=True)
class Redaction:
    term: str
    replacement: str | None = None


def load_redactions(master_dir: Path) -> list:
    path = Path(master_dir) / STORE_NAME
    if not path.exists():
        return []
    redactions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = LINE_RE.match(line.strip())
        if not match:
            continue
        term = match.group(1).strip()
        replacement = (match.group(2) or "").strip() or None
        redactions.append(Redaction(term=term, replacement=replacement))
    return redactions


def _pattern(term: str) -> re.Pattern:
    return re.compile(re.escape(term), re.IGNORECASE)


def find_terms(text: str, redactions: list) -> list:
    return [r for r in redactions if _pattern(r.term).search(text)]


def apply_redactions(text: str, redactions: list) -> tuple:
    """Substitute every declared replacement. Return (text, blocked), where
    blocked lists matched redactions that have no replacement -- the caller
    must fail rather than emit them."""
    blocked = []
    for redaction in find_terms(text, redactions):
        if redaction.replacement is None:
            blocked.append(redaction)
            continue
        text = _pattern(redaction.term).sub(redaction.replacement, text)
    return text, blocked
```

- [ ] **Step 5: Implement `scripts/check_redactions.py`**

```python
#!/usr/bin/env python3
"""Flag withheld terms in a library application's generated artifacts.

Reports, never rewrites. Whether to name a withheld term on a document that
reaches an employer is the user's decision; this check only guarantees the
decision is made deliberately rather than by a draft nobody re-read.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402
from resumelib.redactions import find_terms, load_redactions  # noqa: E402

ARTIFACT_GLOBS = ("draft.md", "cover-letter*.md", "outreach*.md")


def check(library_dir: Path, master_dir: Path) -> list:
    redactions = load_redactions(master_dir)
    if not redactions:
        return []
    findings = []
    library_dir = Path(library_dir)
    for glob in ARTIFACT_GLOBS:
        for path in sorted(library_dir.glob(glob)):
            text = path.read_text(encoding="utf-8")
            for redaction in find_terms(text, redactions):
                findings.append(Finding(
                    "redacted_term",
                    f"{path.name} names {redaction.term!r}, which master/"
                    f"{'redactions.md'} withholds"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path)
    parser.add_argument("--master", type=Path, default=Path("master"))
    args = parser.parse_args()

    findings = check(args.library, args.master)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} redaction finding(s).")
        return 1
    print("redactions: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_redactions -v`
Expected: PASS, 12 tests

- [ ] **Step 7: Amend AGENTS.md invariant 1**

`build-master` is the only writer to `master/`, and the next step writes there. Add the carve-out to invariant 1 in `AGENTS.md`, immediately after the existing sentences:

```markdown
   The one exception is `master/redactions.md`, which records terms withheld
   from generated artifacts. It can only subtract from what gets emitted, never
   add a claim, so the reason for this rule — no unconfirmed fact reaching
   `master/` — does not apply. Adding a term when the user says "do not name X"
   is still `build-master`'s job.
```

`tests/test_docs.py` asserts AGENTS.md states the sole-writer rule; run it after editing.

- [ ] **Step 8: Create the real redaction store**

Create `master/redactions.md` with this header and **one entry**:

```markdown
# Redactions

Terms withheld from generated artifacts. `- term => replacement` substitutes on
export; `- term` alone has no replacement and fails the export closed.

This file has no frontmatter on purpose: `load_entries` skips it, so its lines
can never be read as master bullets.
```

For the entry: read the role entry under `master/roles/` whose prose carries a
**Customer naming** note, and transcribe the customer it says must not be named
in a draft, with a generic replacement of the same scope. Add no other terms —
new entries are the user's call.

**Do not paste that term into any file under `docs/`, `tests/`, or a commit
message.** `docs/` is shared, and a plan that spelled the term out would publish
exactly what this feature exists to contain. `master/` is the only place it
belongs. The fixture store already exercises the machinery with an invented
term, so nothing shared needs the real one.

- [ ] **Step 9: Run the full suite and commit**

Run: `python3 -m unittest discover -s tests` and `python3 scripts/check_manifest.py plugin`
Expected: both pass

```bash
git add AGENTS.md master/redactions.md resumelib/redactions.py \
        scripts/check_redactions.py tests/test_redactions.py \
        tests/fixtures/master/redactions.md
git commit -m "feat: machine-readable withheld terms, enforced over library artifacts"
```

The commit message must not name the withheld term either.

---

### Task 2: `export_cv_md.py`

**Files:**
- Create: `resumelib/cvexport.py`
- Create: `scripts/export_cv_md.py`
- Test: `tests/test_cvexport.py`

**Interfaces:**
- Consumes: `resumelib.master.Entry`, `load_entries`; `resumelib.redactions.Redaction`, `load_redactions`, `apply_redactions`; `resumelib.draft.Finding`.
- Produces:
  - `render_cv(entries: list[Entry], redactions: list[Redaction]) -> tuple[str, list[Finding]]`
  - `bullet_digest(entries: list[Entry], redactions: list[Redaction]) -> str` — SHA-256 hex over emitted bullet texts joined by `\n`
  - `DIGEST_RE: re.Pattern` matching `<!-- master-sha256: <hex> -->`
  - `career_ops_root(flag: Path | None) -> Path` in `scripts/export_cv_md.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cvexport.py`:

```python
import unittest
from pathlib import Path

from resumelib.cvexport import DIGEST_RE, bullet_digest, render_cv
from resumelib.master import load_entries
from resumelib.redactions import Redaction, load_redactions

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MASTER = FIXTURES / "master"


class TestRender(unittest.TestCase):
    def setUp(self):
        self.entries = load_entries(MASTER)
        self.redactions = load_redactions(MASTER)
        self.text, self.findings = render_cv(self.entries, self.redactions)

    def test_renders_without_findings(self):
        self.assertEqual(self.findings, [])

    def test_emits_a_bullet(self):
        self.assertIn(
            "Migrated 38 services from EC2 to ECS over 14 months", self.text)

    def test_strips_the_period_token(self):
        self.assertNotIn("(2023) Migrated 38 services", self.text)

    def test_excludes_retired_bullets(self):
        # nw.b4 lives under ## Retired.
        self.assertNotIn("Owned the platform roadmap", self.text)

    def test_excludes_bullet_ids(self):
        self.assertNotIn("[nw.b2]", self.text)

    def test_keeps_an_estimate_marker(self):
        # Vaguer is not safer: a qualifier dropped here inflates the fit score.
        self.assertIn("(est.)", self.text)

    def test_has_no_professional_summary(self):
        # A summary is synthesized prose; this export only emits master bullets.
        self.assertNotIn("Professional Summary", self.text)

    def test_orders_roles_most_recent_first(self):
        self.assertLess(self.text.index("Northwind"), self.text.index("Harbor"))

    def test_emits_the_work_experience_heading(self):
        self.assertIn("## Work Experience", self.text)


def _first_live_bullet(entries):
    for entry in entries:
        for bullet in entry.bullets:
            if not bullet.retired:
                return bullet
    raise AssertionError("fixture master has no live bullets")


class TestRedactionInRender(unittest.TestCase):
    def test_declared_term_is_substituted(self):
        entries = load_entries(MASTER)
        _first_live_bullet(entries).text = "Shipped for Vandelay Industries."
        text, findings = render_cv(entries, load_redactions(MASTER))
        self.assertIn("a regulated enterprise customer", text)
        self.assertNotIn("Vandelay Industries", text)
        self.assertEqual(findings, [])

    def test_term_without_a_replacement_fails_closed(self):
        entries = load_entries(MASTER)
        _first_live_bullet(entries).text = "Ran Project Halberd."
        text, findings = render_cv(entries, load_redactions(MASTER))
        self.assertEqual([f.kind for f in findings], ["blocked_term"])
        self.assertIn("Project Halberd", findings[0].detail)
        self.assertEqual(text, "")


class TestDigest(unittest.TestCase):
    def test_digest_is_stable(self):
        entries = load_entries(MASTER)
        redactions = load_redactions(MASTER)
        self.assertEqual(bullet_digest(entries, redactions),
                         bullet_digest(load_entries(MASTER), redactions))

    def test_digest_changes_when_a_bullet_changes(self):
        entries = load_entries(MASTER)
        before = bullet_digest(entries, [])
        _first_live_bullet(entries).text += " And more."
        self.assertNotEqual(before, bullet_digest(entries, []))

    def test_rendered_output_carries_a_matching_digest(self):
        entries = load_entries(MASTER)
        redactions = load_redactions(MASTER)
        text, _ = render_cv(entries, redactions)
        match = DIGEST_RE.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), bullet_digest(entries, redactions))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_cvexport -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resumelib.cvexport'`

- [ ] **Step 3: Implement `resumelib/cvexport.py`**

```python
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
from pathlib import Path

from resumelib.draft import Finding
from resumelib.master import Entry
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


def bullet_digest(entries: list, redactions: list) -> str:
    by_entry, _ = _emitted_bullets(entries, redactions)
    joined = "\n".join(t for entry in entries for t in by_entry.get(entry.id, []))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def render_cv(entries: list, redactions: list) -> tuple:
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
    name = contact.meta.get("name", "CV") if contact else "CV"
    lines.append(f"# CV -- {name}")
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
        if not emitted:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        lines.extend(f"- {text}" for text in emitted)
        lines.append("")

    lines.append(f"<!-- master-sha256: {bullet_digest(entries, redactions)} -->")
    lines.append("")
    return "\n".join(lines), []
```

Note: education entries in `master/` currently carry no bullets, so the Education
section is emitted only once one exists. That is deliberate — this export never
invents a line.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_cvexport -v`
Expected: PASS, 14 tests

- [ ] **Step 5: Implement `scripts/export_cv_md.py`**

```python
#!/usr/bin/env python3
"""Generate career-ops' cv.md from master/, and verify it is not stale.

This script is the only writer to cv.md, mirroring the rule that makes
build-master the only writer to master/. Hand-editing cv.md creates the second
source of truth this whole integration exists to prevent.

    python3 scripts/export_cv_md.py                # write cv.md
    python3 scripts/export_cv_md.py --check        # exit 1 if stale
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.cvexport import DIGEST_RE, bullet_digest, render_cv  # noqa: E402
from resumelib.master import load_entries  # noqa: E402
from resumelib.redactions import load_redactions  # noqa: E402

DEFAULT_ROOT = Path("~/Projects/career-ops").expanduser()


def career_ops_root(flag: Path = None) -> Path:
    if flag:
        return Path(flag).expanduser()
    env = os.environ.get("CAREER_OPS_ROOT")
    if env:
        return Path(env).expanduser()
    return DEFAULT_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=Path("master"))
    parser.add_argument("--career-ops", type=Path, default=None)
    parser.add_argument("--check", action="store_true",
                        help="verify cv.md matches master/ without writing")
    args = parser.parse_args()

    entries = load_entries(args.master)
    redactions = load_redactions(args.master)
    target = career_ops_root(args.career_ops) / "cv.md"

    if args.check:
        if not target.exists():
            print(f"[missing_cv] {target} does not exist; run without --check")
            return 1
        match = DIGEST_RE.search(target.read_text(encoding="utf-8"))
        if not match:
            print(f"[no_digest] {target} carries no master-sha256 comment; "
                  "it was hand-edited or predates this script")
            return 1
        expected = bullet_digest(entries, redactions)
        if match.group(1) != expected:
            print(f"[stale_cv] {target} was built from a different master/; "
                  "re-run export_cv_md.py")
            return 1
        print("cv.md: current")
        return 0

    text, findings = render_cv(entries, redactions)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} finding(s); cv.md not written.")
        return 1

    if not target.parent.exists():
        print(f"[no_career_ops] {target.parent} does not exist")
        return 1
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Add CLI tests**

Append to `tests/test_cvexport.py`:

```python
class TestCli(unittest.TestCase):
    def _run(self, *args):
        import subprocess
        root = Path(__file__).resolve().parent.parent
        return subprocess.run(
            [sys.executable, "scripts/export_cv_md.py", *args],
            cwd=root, capture_output=True, text=True)

    def test_writes_then_checks_clean(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        written = self._run("--master", str(MASTER), "--career-ops", str(tmp))
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
        self.assertTrue((tmp / "cv.md").exists())

        checked = self._run("--master", str(MASTER), "--career-ops", str(tmp),
                            "--check")
        self.assertEqual(checked.returncode, 0, checked.stdout)

    def test_check_fails_on_a_hand_edited_cv(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        self._run("--master", str(MASTER), "--career-ops", str(tmp))
        (tmp / "cv.md").write_text("# CV -- edited by hand\n", encoding="utf-8")
        checked = self._run("--master", str(MASTER), "--career-ops", str(tmp),
                            "--check")
        self.assertEqual(checked.returncode, 1)
        self.assertIn("no_digest", checked.stdout)
```

Add `import sys` to the file's imports.

- [ ] **Step 7: Run the full suite and commit**

Run: `python3 -m unittest discover -s tests`
Expected: PASS

```bash
git add resumelib/cvexport.py scripts/export_cv_md.py tests/test_cvexport.py
git commit -m "feat: generate career-ops cv.md from master, with a staleness digest"
```

---

### Task 3: `import_job.py`

**Files:**
- Create: `scripts/import_job.py`
- Create: `tests/fixtures/career-ops/reports/012-initech-2026-08-05.md`
- Create: `tests/fixtures/career-ops/jds/initech-platform.md`
- Test: `tests/test_import_job.py`

**Interfaces:**
- Consumes: `career_ops_root` from `scripts/export_cv_md.py`; `bullet_digest`, `DIGEST_RE` for the staleness gate.
- Produces: `slugify(text: str) -> str`; `parse_report(path: Path) -> dict` with keys `company`, `title`, `score`, `jd_path`; `missing_fields(report: dict) -> list[str]`; `import_job(report_num, career_ops, library, today) -> tuple[Path, list[Finding]]`.

- [ ] **Step 1: Write the fixtures**

Create `tests/fixtures/career-ops/jds/initech-platform.md`:

```markdown
Platform Engineering, Level 4.

4+ years of software engineering experience. Experience with micro service
design patterns. Object-oriented coding in Java, C++, C#, Go or similar.
```

Create `tests/fixtures/career-ops/reports/012-initech-2026-08-05.md`:

```markdown
# 012 - Initech - Staff Platform Engineer

**Company:** Initech
**Title:** Staff Platform Engineer
**Score:** 4.3
**Source:** local:jds/initech-platform.md

## A. Fit

Strong backend alignment.
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_import_job.py`:

```python
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.import_job import import_job, missing_fields, parse_report, slugify

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CAREER_OPS = FIXTURES / "career-ops"
MASTER = FIXTURES / "master"


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(slugify("Staff Platform Engineer"),
                         "staff-platform-engineer")

    def test_drops_punctuation(self):
        self.assertEqual(slugify("Sr. Engineer, Platform"),
                         "sr-engineer-platform")


class TestParseReport(unittest.TestCase):
    def test_reads_the_header_fields(self):
        report = parse_report(CAREER_OPS / "reports" / "012-initech-2026-08-05.md")
        self.assertEqual(report["company"], "Initech")
        self.assertEqual(report["title"], "Staff Platform Engineer")
        self.assertEqual(report["score"], "4.3")
        self.assertEqual(report["jd_path"], "jds/initech-platform.md")

    def test_a_complete_report_is_missing_nothing(self):
        report = parse_report(CAREER_OPS / "reports" / "012-initech-2026-08-05.md")
        self.assertEqual(missing_fields(report), [])

    def test_names_what_a_changed_format_dropped(self):
        self.assertEqual(missing_fields({"company": "Initech"}),
                         ["title", "score", "jd_path"])


class TestImport(unittest.TestCase):
    def setUp(self):
        self.library = Path(tempfile.mkdtemp())

    def test_writes_job_md_with_provenance(self):
        path, findings = import_job(
            "012", CAREER_OPS, self.library, today="2026-08-05")
        self.assertEqual(findings, [])
        self.assertEqual(path.parent.name,
                         "2026-08-05-initech-staff-platform-engineer")
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Initech"))
        self.assertIn("career-ops report 012", text)
        self.assertIn("score 4.3", text)
        self.assertIn("micro service design patterns", text)

    def test_refuses_to_overwrite_an_existing_application(self):
        import_job("012", CAREER_OPS, self.library, today="2026-08-05")
        _, findings = import_job("012", CAREER_OPS, self.library,
                                 today="2026-08-05")
        self.assertEqual([f.kind for f in findings], ["already_imported"])

    def test_unknown_report_is_a_finding(self):
        _, findings = import_job("999", CAREER_OPS, self.library,
                                 today="2026-08-05")
        self.assertEqual([f.kind for f in findings], ["no_report"])


class TestStalenessGate(unittest.TestCase):
    def test_refuses_when_cv_is_stale(self):
        career_ops = Path(tempfile.mkdtemp())
        (career_ops / "reports").mkdir()
        (career_ops / "jds").mkdir()
        for src in (CAREER_OPS / "reports").glob("*.md"):
            (career_ops / "reports" / src.name).write_text(
                src.read_text(encoding="utf-8"), encoding="utf-8")
        for src in (CAREER_OPS / "jds").glob("*.md"):
            (career_ops / "jds" / src.name).write_text(
                src.read_text(encoding="utf-8"), encoding="utf-8")
        (career_ops / "cv.md").write_text("# CV -- hand written\n",
                                          encoding="utf-8")
        library = Path(tempfile.mkdtemp())
        result = subprocess.run(
            [sys.executable, "scripts/import_job.py", "012",
             "--career-ops", str(career_ops), "--library", str(library),
             "--master", str(MASTER)],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("stale", result.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_import_job -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.import_job'`

- [ ] **Step 4: Implement `scripts/import_job.py`**

```python
#!/usr/bin/env python3
"""Import a scored career-ops posting into library/ as job.md.

Only the posting crosses. The evaluation report stays in career-ops: it is a
scouting note, and library/ holds claims the user may have to defend.

    python3 scripts/import_job.py 012
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.cvexport import DIGEST_RE, bullet_digest  # noqa: E402
from resumelib.draft import Finding  # noqa: E402
from resumelib.master import load_entries  # noqa: E402
from resumelib.redactions import load_redactions  # noqa: E402
from scripts.export_cv_md import career_ops_root  # noqa: E402

FIELD_RE = re.compile(r"^\*\*(Company|Title|Score|Source):\*\*\s*(.+)$")
LOCAL_RE = re.compile(r"^local:(.+)$")


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return text.strip("-")


def parse_report(path: Path) -> dict:
    report = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = FIELD_RE.match(line.strip())
        if not match:
            continue
        key, value = match.group(1).lower(), match.group(2).strip()
        report[key] = value
    source = report.pop("source", "")
    local = LOCAL_RE.match(source)
    report["jd_path"] = local.group(1) if local else source
    return report


def missing_fields(report: dict) -> list:
    """Upstream owns the report format and may change it. Name what is missing
    rather than crashing on a KeyError three frames later."""
    return [f for f in ("company", "title", "score", "jd_path") if not report.get(f)]


def import_job(report_num: str, career_ops: Path, library: Path,
               today: str) -> tuple:
    career_ops, library = Path(career_ops), Path(library)
    matches = sorted((career_ops / "reports").glob(f"{report_num}-*.md"))
    if not matches:
        return Path(), [Finding(
            "no_report", f"no report {report_num} under {career_ops}/reports")]
    report = parse_report(matches[0])
    missing = missing_fields(report)
    if missing:
        return Path(), [Finding(
            "unreadable_report",
            f"{matches[0]} is missing {', '.join(missing)}; career-ops may have "
            "changed its report format")]

    slug = f"{today}-{slugify(report['company'])}-{slugify(report['title'])}"
    target_dir = library / slug
    if target_dir.exists():
        return target_dir, [Finding(
            "already_imported", f"{target_dir} already exists; delete it to "
            "re-import, or tailor the existing application")]

    jd_path = career_ops / report["jd_path"]
    if not jd_path.exists():
        return Path(), [Finding(
            "no_jd", f"report {report_num} points at {jd_path}, which is missing")]

    header = (f"# {report['company']} — {report['title']}. Captured {today} "
              f"from career-ops report {report_num} (score {report['score']}), "
              f"{report['jd_path']}.")
    target_dir.mkdir(parents=True)
    job = target_dir / "job.md"
    job.write_text(f"{header}\n\n{jd_path.read_text(encoding='utf-8')}",
                   encoding="utf-8")
    return job, []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--career-ops", type=Path, default=None)
    parser.add_argument("--library", type=Path, default=Path("library"))
    parser.add_argument("--master", type=Path, default=Path("master"))
    args = parser.parse_args()

    career_ops = career_ops_root(args.career_ops)

    # A score computed against a stale cv.md is not evidence about the current
    # master, so importing on the strength of it would be importing a guess.
    cv = career_ops / "cv.md"
    entries = load_entries(args.master)
    expected = bullet_digest(entries, load_redactions(args.master))
    match = DIGEST_RE.search(cv.read_text(encoding="utf-8")) if cv.exists() else None
    if not match or match.group(1) != expected:
        print(f"[stale_cv] {cv} does not match master/; "
              "run scripts/export_cv_md.py and re-score before importing")
        return 1

    path, findings = import_job(args.report, career_ops, args.library,
                                today=datetime.date.today().isoformat())
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        return 1
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_import_job -v`
Expected: PASS, 9 tests

- [ ] **Step 6: Run the full suite and commit**

Run: `python3 -m unittest discover -s tests`

```bash
git add scripts/import_job.py tests/test_import_job.py tests/fixtures/career-ops
git commit -m "feat: import a scored career-ops posting into library/"
```

---

### Task 4: `resumelib/batch.py`

The batch loop's mechanics, extracted so the skill file stays thin. Invariant 5: if it can be parsed, it is not a judgement call.

**Files:**
- Create: `resumelib/batch.py`
- Test: `tests/test_batch.py`

**Interfaces:**
- Produces:
  - `Gap(job_slug: str, requirement: str)` — frozen dataclass
  - `GapQuestion(requirement: str, job_slugs: list[str])`
  - `normalize_requirement(text: str) -> str`
  - `group_gaps(gaps) -> list[GapQuestion]`
  - `next_round(round_index: int, new_questions: int, max_rounds: int = 2) -> bool`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_batch.py`:

```python
import unittest

from resumelib.batch import (
    Gap, group_gaps, next_round, normalize_requirement,
)


class TestNormalize(unittest.TestCase):
    def test_case_and_whitespace_are_ignored(self):
        self.assertEqual(normalize_requirement("  Kubernetes   Operations "),
                         normalize_requirement("kubernetes operations"))

    def test_trailing_punctuation_is_ignored(self):
        self.assertEqual(normalize_requirement("Kubernetes."),
                         normalize_requirement("Kubernetes"))

    def test_distinct_requirements_stay_distinct(self):
        self.assertNotEqual(normalize_requirement("Kubernetes"),
                            normalize_requirement("Kafka"))


class TestGroup(unittest.TestCase):
    def test_same_requirement_across_jobs_is_one_question(self):
        questions = group_gaps([
            Gap("2026-08-05-acme-swe", "Kubernetes"),
            Gap("2026-08-05-globex-swe", "kubernetes "),
        ])
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].job_slugs,
                         ["2026-08-05-acme-swe", "2026-08-05-globex-swe"])

    def test_keeps_the_first_spelling_for_the_question_text(self):
        questions = group_gaps([
            Gap("a", "Kubernetes operations"),
            Gap("b", "kubernetes operations"),
        ])
        self.assertEqual(questions[0].requirement, "Kubernetes operations")

    def test_distinct_requirements_stay_separate(self):
        questions = group_gaps([Gap("a", "Kubernetes"), Gap("a", "Kafka")])
        self.assertEqual(len(questions), 2)

    def test_a_job_listed_twice_appears_once(self):
        questions = group_gaps([Gap("a", "Kubernetes"), Gap("a", "kubernetes")])
        self.assertEqual(questions[0].job_slugs, ["a"])

    def test_no_gaps_is_no_questions(self):
        self.assertEqual(group_gaps([]), [])


class TestTermination(unittest.TestCase):
    def test_stops_when_a_round_produces_nothing_new(self):
        self.assertFalse(next_round(round_index=1, new_questions=0))

    def test_continues_when_questions_remain_and_rounds_are_left(self):
        self.assertTrue(next_round(round_index=1, new_questions=3))

    def test_stops_at_the_round_cap(self):
        self.assertFalse(next_round(round_index=2, new_questions=3))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_batch -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resumelib.batch'`

- [ ] **Step 3: Implement `resumelib/batch.py`**

```python
"""Mechanics of the batch tailoring loop.

Batching exists so the user answers each question once rather than once per
job. That collapse is pure text grouping, so it lives here with tests instead
of in a skill file where it would be re-derived, differently, every run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_ROUNDS = 2
_PUNCT_RE = re.compile(r"[^a-z0-9]+")


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_batch -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Commit**

```bash
git add resumelib/batch.py tests/test_batch.py
git commit -m "feat: gap dedup and round termination for batch tailoring"
```

---

### Task 5: The `batch-tailor` skill

**Files:**
- Create: `plugin/skills/batch-tailor/SKILL.md`
- Modify: `tests/test_plugin_shape.py:11-13` (add `batch-tailor` to `REQUIRED_SKILLS`)

**Interfaces:**
- Consumes: `resumelib.batch.group_gaps`, `next_round`; `scripts/check_redactions.py`; the existing `tailor-resume` skill and `resume-reviewer` agent.

- [ ] **Step 1: Add the skill to the required list**

In `tests/test_plugin_shape.py`, change `REQUIRED_SKILLS` to:

```python
REQUIRED_SKILLS = ["build-master", "setup", "tailor-resume", "render-resume",
                   "write-cover-letter", "outreach-email", "batch-tailor"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: FAIL with `missing plugin/skills/batch-tailor/SKILL.md`

- [ ] **Step 3: Write the skill**

Create `plugin/skills/batch-tailor/SKILL.md`:

````markdown
---
name: batch-tailor
description: Tailor resumes for several jobs at once, batching every question to the user so each is asked only once. Use when the user has more than one job to tailor for, or asks to tailor a batch, or imports several postings from career-ops. Never adds facts.
---

# Batch tailor

Runs `tailor-resume` across several applications concurrently and collapses
their questions into one conversation. Adds no facts and relaxes no check —
batching changes who asks the questions, never what is enforced.

## Invariants

**Subagents never write to `master/`.** `build-master` is its only writer, and
bullet IDs are append-only: two subagents allocating `nw.b13` at once corrupts
the ID space silently, and every `sources.json` citing it afterward is
ambiguous. You collect answers; you run `build-master` yourself, serially,
between rounds.

**One subagent owns exactly one `library/<slug>/`.** No two agents write the
same file, which is why nothing here needs a lock. A subagent that strays
outside its directory is a bug.

## 1. Assemble the batch

Take the library slugs the user names. If they ask for jobs from career-ops,
import each first:

    python3 scripts/import_job.py <report-number>

Each slug must already have `job.md`. Confirm the list with the user before
spending anything.

## 2. Round 1, phase A — requirements only

Dispatch one subagent per slug, all in a single message so they run
concurrently. Each performs **steps 1–3 of `tailor-resume` only**: extract
requirements, match them to master bullet IDs, write `requirements.md`. Each
returns its no-match list.

Instruct each agent explicitly: do not draft, do not write outside
`library/<slug>/`, do not touch `master/`.

## 3. Barrier — batch the gap questions

Collapse the gaps:

```python
from resumelib.batch import Gap, group_gaps
questions = group_gaps([Gap(slug, req) for slug, req in gaps])
```

Ask the user the grouped questions in one pass, naming which jobs each affects.
Six postings wanting Kubernetes is one question.

Route every answer through `build-master`, serially. A declined question is
recorded as a non-answer so the next batch does not ask it again — without
that, batching makes repeat-asking worse rather than better.

## 4. Round 1, phase B — draft

Resume each subagent with `SendMessage` rather than spawning a fresh one: it
already read the JD and matched the requirements, and should not pay to do that
twice. Each now completes `tailor-resume` from step 4, producing `draft.md` and
`sources.json`, and runs its own checks unchanged:

    python3 scripts/check_provenance.py library/<slug> --master master
    python3 scripts/check_hard_rules.py library/<slug>
    python3 scripts/check_redactions.py library/<slug> --master master
    python3 scripts/keyword_coverage.py library/<slug>

## 5. Round 1, phase C — review

Dispatch one `resume-reviewer` per draft, concurrently.

## 6. Barrier — route the findings

Classify every finding by the table in `AGENTS.md` before acting:

| Finding is about | Goes to |
|---|---|
| How it reads — phrasing, ordering, voice | `preferences/` |
| What is true — a correction, an omission, a new accomplishment | `build-master` |
| Ambiguous | **Ask. Never guess.** |

Group the fact questions the same way as step 3 and ask them in one pass. A
finding that appears on every draft at once — a timeline hole, a missing
seniority signal — is one question.

## 7. Round 2, or stop

```python
from resumelib.batch import next_round
next_round(round_index=1, new_questions=len(questions))
```

If it returns `True`, re-draft and re-review **only** the jobs whose cited
bullets changed. If `False`, stop. Report any gap still unresolved as an open
gap rather than looping on it — a reviewer can always find one more thing to
ask.

## 8. Report

Per application: whether checks passed, which questions it raised, and anything
left open. Then hand off to `render-resume` for the ones the user approves.

A subagent that died mid-round leaves one partial directory, detectable by
shape — `requirements.md` with no `draft.md`, or a draft with no `review.json`.
Report it as incomplete and offer to resume that slug alone. Because each agent
owned one directory, no sibling application is affected.
````

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_plugin_shape -v` and `python3 scripts/check_manifest.py plugin`
Expected: both PASS

- [ ] **Step 5: Add the eval case**

The loop's judgment — is a finding fact or style, and did the shared gap collapse
into one question — needs a live agent run, so it belongs in `evals/`, not
`unittest`. Create `evals/batch/case-01-shared-gap-asked-once.md`:

```markdown
# Batch: a gap shared by two jobs is asked about once

**Expected outcome:** `one_question_two_jobs`

## Setup

Master: `tests/fixtures/master` (no Kubernetes anywhere in it).

Two library directories, each with only a `job.md`:

- `2026-08-05-acme-platform/` — a posting requiring Kubernetes and Kafka
- `2026-08-05-globex-infra/` — a posting requiring Kubernetes and Terraform

## Action

Run `batch-tailor` over both slugs.

## Pass

Kubernetes is raised **once**, naming both applications. Kafka and Terraform are
raised separately. Neither subagent writes to `master/`; the answer is written
by a single `build-master` pass between rounds.

## Fail

Kubernetes is asked about twice, or a subagent writes to `master/`, or drafting
begins before the gap questions are answered.
```

Add `batch` to the eval category list in `evals/README.md`:

```markdown
- **batch**: `batch-tailor` collapses a gap shared by several jobs into one question, and keeps every `master/` write in the main agent.
```

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/batch-tailor/SKILL.md tests/test_plugin_shape.py \
        evals/batch/case-01-shared-gap-asked-once.md evals/README.md
git commit -m "feat: batch-tailor skill, batching questions across concurrent jobs"
```

---

### Task 6: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-08-05-career-ops-integration-design.md`

- [ ] **Step 1: Update the spec to match the implementation**

In the design doc, replace the frontmatter `redact:` YAML block and the sentence beginning "`redact` blocks are collected from the frontmatter of every file under `master/`" with a description of `master/redactions.md`: a store with no frontmatter, so `load_entries` skips it as it skips `known-gaps.md`; one term per line as `- term => replacement`, or `- term` alone for a term with no replacement, which fails the export closed. Add one sentence recording why: `split_frontmatter` parses flat scalars only and is shared with `check_manifest.py`.

- [ ] **Step 2: Update the README paths table**

Add to the "Where things live" table in `README.md`:

```markdown
| `master/redactions.md` | Terms withheld from generated artifacts |
```

- [ ] **Step 3: Add a career-ops section to the README**

Insert before `## Tests`:

````markdown
## career-ops

[career-ops](https://github.com/santifer/career-ops) can front this system:
it scans public ATS boards, checks a posting is still live, and scores it
against a CV. Discovery, scoring, and tracking happen there; tailoring,
review, and rendering happen here.

No code is added to career-ops, so its `update-system.mjs` keeps working. Two
things cross, both one-way:

    python3 scripts/export_cv_md.py       # master/ -> career-ops/cv.md
    python3 scripts/import_job.py 012     # a scored report -> library/<slug>/job.md

`cv.md` is generated, never authored — `export_cv_md.py` is its only writer,
the same rule that makes `build-master` the only writer to `master/`. It
carries a digest of the master bullets it was built from; `--check` fails on
drift, and `import_job.py` refuses to import against a stale one, because a
score computed from an old CV is not evidence about the current master.

Nothing flows back into `master/` automatically. A gap career-ops surfaces is a
question for `build-master`, never a write.

Point the scripts at your clone with `--career-ops`, `CAREER_OPS_ROOT`, or the
default `~/Projects/career-ops`.
````

- [ ] **Step 4: Verify and commit**

Run: `python3 -m unittest discover -s tests` and `python3 scripts/check_manifest.py plugin`
Expected: both PASS (`tests/test_docs.py` asserts README and AGENTS.md shape)

```bash
git add README.md docs/superpowers/specs/2026-08-05-career-ops-integration-design.md
git commit -m "docs: career-ops integration, and the redaction store as built"
```

---

### Task 7: career-ops onboarding in `setup`

`setup` is the one-time onboarding skill, so connecting career-ops belongs there — optional, and only after step 0 has cleared the privacy check.

**Files:**
- Modify: `plugin/skills/setup/SKILL.md` (insert a section between `## 4. Confirm` and `## Never`)
- Modify: `tests/test_plugin_shape.py` (add a wiring test)

**Interfaces:**
- Consumes: `scripts/export_cv_md.py` from Task 2.

- [ ] **Step 1: Write the failing wiring test**

Append to `tests/test_plugin_shape.py`:

```python
class TestCareerOpsWiring(unittest.TestCase):
    """career-ops onboarding is optional, and must stay downstream of the
    privacy gate: cv.md carries the user's real employers."""

    SETUP = PLUGIN / "skills" / "setup" / "SKILL.md"

    def test_setup_offers_career_ops(self):
        text = self.SETUP.read_text(encoding="utf-8")
        self.assertIn("career-ops", text)
        self.assertIn("export_cv_md.py", text)

    def test_career_ops_section_comes_after_the_privacy_gate(self):
        text = self.SETUP.read_text(encoding="utf-8")
        self.assertLess(text.index("check_private.py"), text.index("career-ops"))

    def test_setup_marks_career_ops_optional(self):
        text = self.SETUP.read_text(encoding="utf-8")
        section = text[text.index("career-ops"):]
        self.assertIn("optional", section.lower())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_plugin_shape -v`
Expected: FAIL with `'career-ops' not found`

- [ ] **Step 3: Add the section to `setup`**

Insert between `## 4. Confirm` and `## Never` in `plugin/skills/setup/SKILL.md`:

````markdown
## 5. Offer career-ops — optional

[career-ops](https://github.com/santifer/career-ops) scans public ATS boards,
checks a posting is still live, and scores it against a CV. It is **optional**:
everything here works without it. Offer it once; if the user declines, do not
raise it again.

If they want it:

1. Clone it somewhere outside this repo:

       git clone https://github.com/santifer/career-ops.git ~/Projects/career-ops

2. Copy `config/profile.example.yml` to `config/profile.yml` there and fill in
   targets, locations, and comp range. That is search preference, not resume
   fact, so it lives there and not in `master/`.

3. Generate its CV from the master:

       python3 scripts/export_cv_md.py

   `cv.md` is generated, never authored. Tell the user plainly: editing it by
   hand creates a second source of truth, and every score after that describes
   someone the drafts cannot cite.

Do not run step 3 before the master has facts in it — `build-master` comes
first. If `master/` is still empty, note the option and stop.
````

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_plugin_shape -v` and `python3 scripts/check_manifest.py plugin`
Expected: both PASS

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/setup/SKILL.md tests/test_plugin_shape.py
git commit -m "feat: setup offers career-ops onboarding, after the privacy gate"
```

---

### Task 8: `scripts/sync_shared.py`

Copies the shared layer of this repo into the public tool repo at `~/Projects/resume-generator`, and cannot copy the private layer.

Invariant 7 says real personal data never leaves `master/`, `preferences/`, and `library/`. A hand-run `cp -r` is one flag away from publishing an employment history to a public repo, and git history cannot be un-published. So the copy is an allowlist — the same reason bullet extraction is an allowlist in Task 2, and the same shape as career-ops' own `SYSTEM_PATHS`.

**Files:**
- Create: `scripts/sync_shared.py`
- Test: `tests/test_sync_shared.py`

**Interfaces:**
- Produces: `SHARED_PATHS: tuple[str, ...]`, `PRIVATE_PATHS: tuple[str, ...]`, `plan_copies(source: Path) -> list[Path]` (repo-relative paths that would be copied), `sync(source: Path, target: Path, dry_run: bool) -> list[Path]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sync_shared.py`:

```python
import tempfile
import unittest
from pathlib import Path

from scripts.sync_shared import (
    PRIVATE_PATHS, SHARED_PATHS, plan_copies, sync,
)

ROOT = Path(__file__).resolve().parent.parent


class TestAllowlist(unittest.TestCase):
    def test_private_paths_are_not_in_the_allowlist(self):
        for private in PRIVATE_PATHS:
            self.assertNotIn(private, SHARED_PATHS)

    def test_allowlist_names_the_code_directories(self):
        for shared in ("scripts", "resumelib", "plugin", "tests", "evals",
                       "templates", "docs"):
            self.assertIn(shared, SHARED_PATHS)


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.source = Path(tempfile.mkdtemp())
        (self.source / "scripts").mkdir()
        (self.source / "scripts" / "check_x.py").write_text("x", encoding="utf-8")
        (self.source / "master" / "roles").mkdir(parents=True)
        (self.source / "master" / "roles" / "real-job.md").write_text(
            "secret", encoding="utf-8")
        (self.source / "master" / "redactions.md").write_text(
            "secret", encoding="utf-8")
        (self.source / "library" / "app").mkdir(parents=True)
        (self.source / "library" / "app" / "draft.md").write_text(
            "secret", encoding="utf-8")
        (self.source / "preferences").mkdir()
        (self.source / "preferences" / "style.md").write_text(
            "secret", encoding="utf-8")
        (self.source / "README.md").write_text("shared", encoding="utf-8")

    def test_plans_to_copy_shared_files(self):
        planned = plan_copies(self.source)
        self.assertIn(Path("scripts/check_x.py"), planned)
        self.assertIn(Path("README.md"), planned)

    def test_never_plans_a_master_file(self):
        planned = plan_copies(self.source)
        self.assertFalse([p for p in planned if p.parts[0] == "master"],
                         "master/ must never be copied to the shared repo")

    def test_never_plans_library_or_preferences(self):
        planned = plan_copies(self.source)
        for forbidden in ("library", "preferences"):
            self.assertFalse([p for p in planned if p.parts[0] == forbidden])

    def test_fixture_master_is_shared(self):
        # tests/fixtures/master uses an invented persona and must cross.
        (self.source / "tests" / "fixtures" / "master").mkdir(parents=True)
        (self.source / "tests" / "fixtures" / "master" / "redactions.md").write_text(
            "invented", encoding="utf-8")
        planned = plan_copies(self.source)
        self.assertIn(Path("tests/fixtures/master/redactions.md"), planned)


class TestSync(unittest.TestCase):
    def setUp(self):
        self.source = Path(tempfile.mkdtemp())
        (self.source / "scripts").mkdir()
        (self.source / "scripts" / "new.py").write_text("new", encoding="utf-8")
        (self.source / "master").mkdir()
        (self.source / "master" / "real.md").write_text("secret", encoding="utf-8")
        self.target = Path(tempfile.mkdtemp())

    def test_dry_run_writes_nothing(self):
        sync(self.source, self.target, dry_run=True)
        self.assertFalse((self.target / "scripts" / "new.py").exists())

    def test_copies_and_overwrites(self):
        (self.target / "scripts").mkdir()
        (self.target / "scripts" / "new.py").write_text("old", encoding="utf-8")
        sync(self.source, self.target, dry_run=False)
        self.assertEqual(
            (self.target / "scripts" / "new.py").read_text(encoding="utf-8"), "new")

    def test_does_not_create_master_in_the_target(self):
        sync(self.source, self.target, dry_run=False)
        self.assertFalse((self.target / "master" / "real.md").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_sync_shared -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.sync_shared'`

- [ ] **Step 3: Implement `scripts/sync_shared.py`**

```python
#!/usr/bin/env python3
"""Copy this repo's shared layer into the public tool repo.

Invariant 7: real personal data never leaves master/, preferences/, and
library/. Those three are the user's; everything else is the tool.

The copy set is an allowlist, never a filter. A denylist fails open -- a new
directory holding something personal would be copied by default, and a public
git history cannot be un-published. An allowlist fails closed: anything not
named here simply does not travel.

    python3 scripts/sync_shared.py --dry-run
    python3 scripts/sync_shared.py --target ~/Projects/resume-generator
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SHARED_PATHS = (
    "scripts", "resumelib", "plugin", "tests", "evals", "templates", "docs",
    "README.md", "AGENTS.md", "CLAUDE.md", ".gitignore",
)

# Named only so the allowlist can be asserted against them in tests. Nothing
# reads this to decide what to skip -- skipping is what the allowlist already
# does.
PRIVATE_PATHS = ("master", "preferences", "library", "jobs")

SKIP_NAMES = {".DS_Store", "__pycache__"}


def _walk(base: Path, entry: str) -> list:
    path = base / entry
    if path.is_file():
        return [Path(entry)]
    if not path.is_dir():
        return []
    found = []
    for child in sorted(path.rglob("*")):
        if not child.is_file():
            continue
        if SKIP_NAMES.intersection(child.parts):
            continue
        found.append(child.relative_to(base))
    return found


def plan_copies(source: Path) -> list:
    source = Path(source)
    planned = []
    for entry in SHARED_PATHS:
        planned.extend(_walk(source, entry))
    return planned


def sync(source: Path, target: Path, dry_run: bool) -> list:
    source, target = Path(source), Path(target)
    planned = plan_copies(source)
    if dry_run:
        return planned
    for relative in planned:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    return planned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--target", type=Path,
                        default=Path("~/Projects/resume-generator").expanduser())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = args.target.expanduser()
    if not target.exists():
        print(f"[no_target] {target} does not exist")
        return 1

    copied = sync(args.source, target, args.dry_run)
    verb = "would copy" if args.dry_run else "copied"
    print(f"{verb} {len(copied)} file(s) to {target}")
    print("master/, preferences/, and library/ were not read.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_sync_shared -v`
Expected: PASS, 10 tests

- [ ] **Step 5: Run the full suite and commit**

Run: `python3 -m unittest discover -s tests` and `python3 scripts/check_manifest.py plugin`

```bash
git add scripts/sync_shared.py tests/test_sync_shared.py
git commit -m "feat: allowlisted sync of the shared layer to the public tool repo"
```

---

## Manual verification

After Task 6, run against the real repos once:

1. `python3 scripts/export_cv_md.py` — inspect `~/Projects/career-ops/cv.md`. Confirm no prose commentary from `master/` reached it, no `## Retired` bullet appears, and the term in master/redactions.md is replaced by its stand-in.
2. `python3 scripts/export_cv_md.py --check` — expect `cv.md: current`.
3. In career-ops, fill `config/profile.yml` from `config/profile.example.yml`, then `node scan.mjs` and evaluate one posting.
4. `python3 scripts/import_job.py <n>` — confirm `library/<slug>/job.md` has the provenance header.
5. `/resume-assistant:batch-tailor` over two imported slugs; confirm a shared gap is asked once.
6. `python3 scripts/sync_shared.py --dry-run` — read the file list and confirm no `master/`, `preferences/`, or `library/` path appears. Then run it for real. Do not push the shared repo; that is the user's call.
