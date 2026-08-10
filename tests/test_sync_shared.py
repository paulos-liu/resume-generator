import os
import tempfile
import unittest
from pathlib import Path

from scripts.sync_shared import (
    PRIVATE_PATHS, SHARED_PATHS, _UPSTREAM_IDENTITY_FILES,
    _UPSTREAM_IDENTITY_KINDS, plan_copies, sync,
)


class TestAllowlist(unittest.TestCase):
    def test_private_paths_are_not_in_the_allowlist(self):
        for private in PRIVATE_PATHS:
            self.assertNotIn(private, SHARED_PATHS)

    def test_allowlist_names_the_code_directories(self):
        for shared in ("scripts", "resumelib", "plugin", "tests", "evals",
                       "templates", "docs"):
            self.assertIn(shared, SHARED_PATHS)

    def test_upstream_identity_allowance_is_pinned(self):
        """`_UPSTREAM_IDENTITY_FILES` and `_UPSTREAM_IDENTITY_KINDS` are a
        deliberate, narrow carve-out in the publish-time scan -- correct as
        implemented, but nothing else in this suite would notice it growing.
        `test_upstream_repo_identity_files_are_not_flagged` and
        `test_upstream_identity_allowance_does_not_cover_other_files`/`_kinds`
        below exercise an unrelated path (`docs/note.md`) and an unrelated
        kind (`employer`), so adding a third file to the path tuple, or
        `contact_email`/`contact_linkedin` to the kind tuple, would break none
        of them -- a silent widening of a privacy exemption would pass this
        whole suite. This test pins both tuples to their exact current
        contents so any change to either is a deliberate, visible edit to
        this test, not an invisible one. The values are not sacred -- if the
        allowance genuinely needs to grow, update this test along with it and
        say why; do not delete this test as "brittle" without replacing what
        it guards."""
        self.assertEqual(
            _UPSTREAM_IDENTITY_FILES,
            (Path("scripts/check_private.py"), Path("tests/test_check_private.py")))
        self.assertEqual(
            _UPSTREAM_IDENTITY_KINDS, ("contact_name", "contact_github"))


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

    def test_symlink_to_private_file_is_not_planned(self):
        # A symlink under an allowlisted directory that resolves to a real
        # private file must not smuggle that file's bytes into the plan
        # under an innocuous path.
        (self.source / "tests").mkdir()
        link = self.source / "tests" / "sneaky.md"
        os.symlink(self.source / "master" / "redactions.md", link)
        planned = plan_copies(self.source)
        self.assertNotIn(Path("tests/sneaky.md"), planned)

    def test_symlink_outside_source_tree_is_not_planned(self):
        outside = Path(tempfile.mkdtemp())
        outside_file = outside / "external.md"
        outside_file.write_text("not part of this repo", encoding="utf-8")
        (self.source / "docs").mkdir()
        link = self.source / "docs" / "external-link.md"
        os.symlink(outside_file, link)
        planned = plan_copies(self.source)
        self.assertNotIn(Path("docs/external-link.md"), planned)


class TestSync(unittest.TestCase):
    def setUp(self):
        self.source = Path(tempfile.mkdtemp())
        (self.source / "scripts").mkdir()
        (self.source / "scripts" / "new.py").write_text("new", encoding="utf-8")
        (self.source / "master").mkdir()
        # A master/ that actually yields identifiers -- an id-less file (like
        # the old "real.md" fixture here) derives none, and the scan now
        # refuses to sync rather than treat that as clean. Uses an invented
        # persona; see TestContentScan.
        (self.source / "master" / "contact.md").write_text(
            "---\n"
            "id: contact.primary\n"
            "type: contact\n"
            "name: Contact details\n"
            "full_name: Jamie Sorrel\n"
            "email: jamie.sorrel@example.com\n"
            "---\n",
            encoding="utf-8")
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
        self.assertFalse((self.target / "master").exists())


class TestContentScan(unittest.TestCase):
    """Uses an invented persona in a temporary master/, never the real one."""

    def setUp(self):
        self.source = Path(tempfile.mkdtemp())
        (self.source / "master").mkdir()
        # `name` mirrors the real schema's use of that key as the entry
        # label, never the person's name -- the real name lives in
        # `full_name`, added after this branch started.
        (self.source / "master" / "contact.md").write_text(
            "---\n"
            "id: contact.primary\n"
            "type: contact\n"
            "name: Contact details\n"
            "full_name: Jamie Sorrel\n"
            "email: jamie.sorrel@example.com\n"
            "phone: 555-0142\n"
            "github: https://github.com/jamie-sorrel\n"
            "linkedin: https://www.linkedin.com/in/jamie-sorrel/\n"
            "---\n",
            encoding="utf-8")
        (self.source / "master" / "roles").mkdir()
        (self.source / "master" / "roles" / "northwind.md").write_text(
            "---\n"
            "id: role.northwind.staff-eng\n"
            "type: role\n"
            "company: Northwind Logistics\n"
            "---\n",
            encoding="utf-8")
        (self.source / "master" / "education.md").write_text(
            "---\n"
            "id: education.example\n"
            "type: education\n"
            "institution: State University\n"
            "---\n",
            encoding="utf-8")
        (self.source / "master" / "projects").mkdir()
        (self.source / "master" / "projects" / "halberd.md").write_text(
            "---\n"
            "id: project.halberd\n"
            "type: project\n"
            "name: Sirius Cybernetics migration\n"
            "---\n",
            encoding="utf-8")
        (self.source / "master" / "redactions.md").write_text(
            "- Vandelay Industries => a regulated enterprise customer\n"
            "- Project Halberd\n",
            encoding="utf-8")
        (self.source / "docs").mkdir()
        (self.source / "tests").mkdir()
        (self.source / "scripts").mkdir()
        self.target = Path(tempfile.mkdtemp())

    def test_clean_files_produce_no_findings(self):
        (self.source / "docs" / "note.md").write_text(
            "Nothing sensitive here.\n", encoding="utf-8")
        planned, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual(findings, [])
        self.assertTrue((self.target / "docs" / "note.md").exists())

    def test_contact_name_in_a_shared_file_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "Written by Jamie Sorrel.\n", encoding="utf-8")
        planned, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_name"])
        self.assertFalse((self.target / "docs" / "note.md").exists())

    def test_full_name_in_a_shared_file_is_refused(self):
        # The scan must read `full_name`, not just `name` -- `name` on this
        # entry is the section label ("Contact details"), and the real name
        # only lives in `full_name`. This is the exact gap the coordinator
        # flagged: a file naming the owner's real full name must be refused.
        (self.source / "tests" / "fixture_bio.md").write_text(
            "Case study written up by Jamie Sorrel for the team wiki.\n",
            encoding="utf-8")
        planned, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_name"])
        self.assertFalse((self.target / "tests" / "fixture_bio.md").exists())

    def test_generic_entry_label_does_not_cause_a_false_positive(self):
        # "Contact details" is the label held in `name`, not a name. If the
        # scan treated `name` as a term unconditionally, this ordinary sentence
        # would make every sync refuse.
        (self.source / "docs" / "note.md").write_text(
            "See the Contact details section of the template.\n",
            encoding="utf-8")
        planned, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual(findings, [])
        self.assertTrue((self.target / "docs" / "note.md").exists())

    def test_finding_never_carries_the_matched_string(self):
        (self.source / "docs" / "note.md").write_text(
            "Contact jamie.sorrel@example.com for details.\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        for finding in findings:
            self.assertNotIn("jamie.sorrel@example.com", finding.detail)
            self.assertNotIn("jamie.sorrel@example.com", finding.kind)

    def test_employer_in_a_shared_file_is_a_finding(self):
        (self.source / "tests" / "fixture.py").write_text(
            "COMPANY = 'Northwind Logistics'\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["employer"])

    def test_institution_in_a_shared_file_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "Graduated from State University.\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["institution"])

    def test_redacted_term_in_a_shared_file_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "Ran Project Halberd last year.\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["redacted_term"])

    def test_finding_blocks_every_copy_not_just_the_offending_file(self):
        (self.source / "docs" / "note.md").write_text(
            "Written by Jamie Sorrel.\n", encoding="utf-8")
        (self.source / "docs" / "clean.md").write_text(
            "Nothing sensitive.\n", encoding="utf-8")
        sync(self.source, self.target, dry_run=False)
        self.assertFalse((self.target / "docs" / "clean.md").exists())

    def test_dry_run_still_reports_findings(self):
        # A finding is a fail-closed condition, not something --dry-run should
        # quietly preview past.
        (self.source / "docs" / "note.md").write_text(
            "Written by Jamie Sorrel.\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=True)
        self.assertEqual([f.kind for f in findings], ["contact_name"])
        self.assertFalse((self.target / "docs" / "note.md").exists())

    def test_dry_run_with_no_findings_writes_nothing(self):
        (self.source / "docs" / "note.md").write_text(
            "Nothing sensitive here.\n", encoding="utf-8")
        planned, findings = sync(self.source, self.target, dry_run=True)
        self.assertEqual(findings, [])
        self.assertIn(Path("docs/note.md"), planned)
        self.assertFalse((self.target / "docs" / "note.md").exists())

    def test_phone_in_a_shared_file_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "Call 555-0142 for a reference.\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_phone"])

    def test_github_in_a_shared_file_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "Portfolio: https://github.com/jamie-sorrel\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        # The URL embeds the hyphenated name form too, so both kinds fire --
        # that overlap is exactly why check_private.py needs an explicit,
        # narrow allowance (see below).
        self.assertEqual(sorted(f.kind for f in findings),
                         ["contact_github", "contact_name"])

    def test_linkedin_in_a_shared_file_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "Profile: https://www.linkedin.com/in/jamie-sorrel/\n",
            encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual(sorted(f.kind for f in findings),
                         ["contact_linkedin", "contact_name"])

    def test_project_name_in_a_shared_file_is_a_finding(self):
        # Only contact/role/education used to contribute; a project naming a
        # client or codename was invisible to the scan.
        (self.source / "docs" / "note.md").write_text(
            "Case study: the Sirius Cybernetics migration.\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["project_name"])

    def test_hyphenated_name_is_a_finding(self):
        # A handle-shaped spelling of the name -- exactly the form the real
        # owner's own GitHub handle takes -- used to slip past a literal,
        # single-space match.
        (self.source / "docs" / "note.md").write_text(
            "Written by jamie-sorrel.\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_name"])

    def test_dotted_name_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "Contact: jamie.sorrel wrote this.\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_name"])

    def test_underscored_name_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "user: jamie_sorrel\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_name"])

    def test_concatenated_name_is_a_finding(self):
        (self.source / "docs" / "note.md").write_text(
            "handle: jamiesorrel\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_name"])

    def test_line_wrapped_name_is_a_finding(self):
        # Markdown wraps prose at 80 columns; a name can straddle the break.
        (self.source / "docs" / "note.md").write_text(
            "This case study was written up by Jamie\nSorrel for the wiki.\n",
            encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_name"])

    def test_unreadable_file_is_reported_not_silently_skipped(self):
        # A file the scan cannot decode used to be skipped with a silent
        # `continue`, publishing it unscanned.
        (self.source / "docs" / "binary.md").write_bytes(b"\xff\xfe\x00\xff")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["unreadable_file"])
        self.assertFalse((self.target / "docs" / "binary.md").exists())

    def test_upstream_repo_identity_files_are_not_flagged(self):
        # scripts/check_private.py's whole job is recognizing the shared
        # upstream repo, so it and its test necessarily spell the repo's
        # owner/name slug -- which happens to embed this persona's
        # hyphenated name. That is a deliberate, narrow allowance for these
        # two files and only the name/github kinds; it must not become a
        # blanket exemption (checked below).
        (self.source / "scripts" / "check_private.py").write_text(
            'UPSTREAM_REPOS = ("jamie-sorrel/resume-generator",)\n',
            encoding="utf-8")
        (self.source / "tests" / "test_check_private.py").write_text(
            'URL = "https://github.com/jamie-sorrel/resume-generator.git"\n',
            encoding="utf-8")
        planned, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual(findings, [])
        self.assertTrue(
            (self.target / "scripts" / "check_private.py").exists())
        self.assertTrue(
            (self.target / "tests" / "test_check_private.py").exists())

    def test_upstream_identity_allowance_does_not_cover_other_files(self):
        # The same hyphenated-name text in any other file is still a finding
        # -- the allowance is scoped to two specific paths, not to the string.
        (self.source / "docs" / "note.md").write_text(
            "jamie-sorrel/resume-generator\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["contact_name"])

    def test_upstream_identity_allowance_does_not_cover_other_kinds(self):
        # Even in the two allowed files, a different identifier kind (here,
        # the employer) still refuses the sync.
        (self.source / "scripts" / "check_private.py").write_text(
            "# worked at Northwind Logistics\n", encoding="utf-8")
        _, findings = sync(self.source, self.target, dry_run=False)
        self.assertEqual([f.kind for f in findings], ["employer"])


class TestIdentifierDerivationFailure(unittest.TestCase):
    """The scan must fail closed when it cannot derive the identifiers it
    exists to enforce -- an empty identifiers list must never be treated as
    "nothing to protect"."""

    def test_missing_master_is_refused_as_no_master(self):
        source = Path(tempfile.mkdtemp())
        (source / "docs").mkdir()
        (source / "docs" / "note.md").write_text("hello\n", encoding="utf-8")
        target = Path(tempfile.mkdtemp())
        planned, findings = sync(source, target, dry_run=True)
        self.assertEqual([f.kind for f in findings], ["no_master"])
        self.assertFalse((target / "docs" / "note.md").exists())

    def test_master_with_no_derivable_fields_is_refused_as_no_identifiers(self):
        # master/ exists (the path is right) but nothing in it yields a
        # term -- distinct from a missing master/ entirely, and the finding
        # kind must say so.
        source = Path(tempfile.mkdtemp())
        (source / "master").mkdir()
        (source / "master" / "known-gaps.md").write_text(
            "Nothing filled in yet.\n", encoding="utf-8")
        (source / "docs").mkdir()
        (source / "docs" / "note.md").write_text("hello\n", encoding="utf-8")
        target = Path(tempfile.mkdtemp())
        planned, findings = sync(source, target, dry_run=True)
        self.assertEqual([f.kind for f in findings], ["no_identifiers"])
        self.assertFalse((target / "docs" / "note.md").exists())

    def test_no_master_and_no_identifiers_are_distinguishable(self):
        # Both look like "zero identifiers" if the finding kind doesn't say
        # which -- verify they are in fact different kinds.
        no_master_source = Path(tempfile.mkdtemp())
        no_identifiers_source = Path(tempfile.mkdtemp())
        (no_identifiers_source / "master").mkdir()
        target = Path(tempfile.mkdtemp())
        _, no_master_findings = sync(no_master_source, target, dry_run=True)
        _, no_identifiers_findings = sync(
            no_identifiers_source, target, dry_run=True)
        self.assertNotEqual(
            [f.kind for f in no_master_findings],
            [f.kind for f in no_identifiers_findings])


if __name__ == "__main__":
    unittest.main()
