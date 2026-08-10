import sys
import unittest
from pathlib import Path

from resumelib.cvexport import DIGEST_RE, bullet_digest, render_cv
from resumelib.master import Bullet, Entry, load_entries
from resumelib.redactions import Redaction, load_redactions

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MASTER = FIXTURES / "master"
# tests/fixtures/master is pinned one live bullet below the thin-master
# threshold (see evals/README.md) for the invention/faithfulness/interview
# evals -- it must not grow a populated skill/education section. Tests that
# need one use this separate fixture instead; see its own README.md.
MASTER_SECTIONS = FIXTURES / "master-sections"


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

    def test_contact_header_carries_the_persona_name(self):
        self.assertIn("# CV -- Jamie Sorrel", self.text)

    def test_contact_header_carries_each_labeled_field(self):
        self.assertIn("**Location:** Portland, OR", self.text)
        self.assertIn("**Email:** jamie.sorrel@example.com", self.text)
        self.assertIn("**LinkedIn:** linkedin.com/in/jamiesorrel", self.text)
        self.assertIn("**GitHub:** github.com/jamiesorrel", self.text)

    def test_contact_header_excludes_phone(self):
        # Excluding phone from the export is a deliberate privacy choice, not
        # an oversight -- the fixture carries one so this has something to
        # guard.
        self.assertNotIn("555-0142", self.text)
        self.assertNotIn("Phone", self.text)


class TestPopulatedSections(unittest.TestCase):
    """Uses master-sections, not master: see the MASTER_SECTIONS comment above."""

    def setUp(self):
        self.entries = load_entries(MASTER_SECTIONS)
        self.redactions = load_redactions(MASTER_SECTIONS)
        self.text, self.findings = render_cv(self.entries, self.redactions)

    def test_renders_without_findings(self):
        self.assertEqual(self.findings, [])

    def test_populated_skills_section_renders_its_bullets(self):
        self.assertIn("## Skills", self.text)
        self.assertIn("Python, Go, and Rust in production services.", self.text)
        self.assertIn("AWS, Kubernetes, and Terraform for infrastructure.", self.text)
        self.assertIn(
            "Distributed systems design and on-call incident response.", self.text)

    def test_work_experience_section_sits_alongside_skills(self):
        self.assertIn("## Work Experience", self.text)
        self.assertIn("Anchor Cloud Systems", self.text)


class TestContactName(unittest.TestCase):
    """`name:` is the entry's descriptive label throughout this schema (the
    real master/contact.md has `name: Contact details`); only `full_name:` is
    trustworthy as the candidate's name."""

    def test_full_name_overrides_a_label_only_name(self):
        contact = Entry(id="contact.primary", type="contact",
                        path=Path("contact.md"),
                        meta={"name": "Contact details",
                              "full_name": "Jamie Sorrel"})
        text, findings = render_cv([contact], [])
        self.assertEqual(findings, [])
        self.assertIn("# CV -- Jamie Sorrel", text)
        self.assertNotIn("Contact details", text)

    def test_no_name_field_emits_a_bare_cv_title(self):
        contact = Entry(id="contact.primary", type="contact",
                        path=Path("contact.md"), meta={})
        text, findings = render_cv([contact], [])
        self.assertEqual(findings, [])
        self.assertTrue(text.startswith("# CV\n"))


class TestSectionSuppressionAndOrder(unittest.TestCase):
    def test_entry_type_with_no_live_bullets_emits_no_heading(self):
        entries = [Entry(id="skill.empty", type="skill",
                         path=Path("skill.md"), meta={}, bullets=[])]
        text, findings = render_cv(entries, [])
        self.assertEqual(findings, [])
        self.assertNotIn("## Skills", text)

    def test_entry_with_only_retired_bullets_emits_no_heading(self):
        entries = [Entry(
            id="skill.retired", type="skill", path=Path("skill.md"), meta={},
            bullets=[Bullet(id="skill.b1", text="Old thing.", retired=True)])]
        text, findings = render_cv(entries, [])
        self.assertEqual(findings, [])
        self.assertNotIn("## Skills", text)

    def test_emits_projects_then_skills_then_education(self):
        entries = [
            Entry(id="proj.1", type="project", path=Path("proj.md"), meta={},
                 bullets=[Bullet(id="proj.b1", text="Built a thing.")]),
            Entry(id="skill.1", type="skill", path=Path("skill.md"), meta={},
                 bullets=[Bullet(id="skill.b1", text="Python.")]),
            Entry(id="edu.1", type="education", path=Path("edu.md"), meta={},
                 bullets=[Bullet(id="edu.b1", text="BS Computer Science.")]),
        ]
        text, findings = render_cv(entries, [])
        self.assertEqual(findings, [])
        self.assertLess(text.index("## Projects"), text.index("## Skills"))
        self.assertLess(text.index("## Skills"), text.index("## Education"))

    # The real master's education entry carries NO bullets -- a degree is
    # frontmatter, not an accomplishment -- so the bullets-only path dropped the
    # whole section and shipped a CV with no degree on it. The test above missed
    # it by giving its education entry a bullet, which no real entry has.
    def test_education_without_bullets_still_renders_from_frontmatter(self):
        entries = [Entry(
            id="edu.1", type="education", path=Path("edu.md"), bullets=[],
            meta={"degree": "B.S. Marine Biology", "institution": "Springfield University",
                  "minor": "Computer Science", "location": "Springfield, IL",
                  "end": "2018-06"})]
        text, findings = render_cv(entries, [])
        self.assertEqual(findings, [])
        self.assertIn("## Education", text)
        self.assertIn("B.S. Marine Biology, Springfield University", text)
        self.assertIn("(Minor: Computer Science)", text)
        self.assertIn("2018-06", text)

    def test_education_falls_back_to_name_when_degree_absent(self):
        entries = [Entry(
            id="edu.1", type="education", path=Path("edu.md"), bullets=[],
            meta={"name": "B.A. History, Springfield University"})]
        text, findings = render_cv(entries, [])
        self.assertEqual(findings, [])
        self.assertIn("B.A. History, Springfield University", text)

    def test_education_bullets_win_over_frontmatter_fallback(self):
        entries = [Entry(
            id="edu.1", type="education", path=Path("edu.md"),
            meta={"degree": "B.S. Basketweaving", "institution": "Springfield"},
            bullets=[Bullet(id="edu.b1", text="B.A. History, Springfield.")])]
        text, findings = render_cv(entries, [])
        self.assertEqual(findings, [])
        self.assertIn("B.A. History, Springfield.", text)
        self.assertNotIn("Basketweaving", text)

    # The fallback bypasses the bullet loop, so it must not bypass redaction.
    def test_withheld_term_in_education_frontmatter_blocks_the_export(self):
        entries = [Entry(
            id="edu.1", type="education", path=Path("edu.md"), bullets=[],
            meta={"degree": "B.S. Physics", "institution": "Secret Institute"})]
        text, findings = render_cv(entries, [Redaction("Secret Institute", None)])
        self.assertEqual(text, "")
        self.assertEqual([f.kind for f in findings], ["blocked_term"])

    def test_education_frontmatter_honors_a_replacement(self):
        entries = [Entry(
            id="edu.1", type="education", path=Path("edu.md"), bullets=[],
            meta={"degree": "B.S. Physics", "institution": "Secret Institute"})]
        text, findings = render_cv(
            entries, [Redaction("Secret Institute", "a private university")])
        self.assertEqual(findings, [])
        self.assertIn("a private university", text)
        self.assertNotIn("Secret Institute", text)


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

    def test_bare_redaction_matching_nothing_does_not_change_the_digest(self):
        # tests/fixtures/master/redactions.md declares "Project Halberd" with
        # no replacement, and no current bullet names it. The rendered body
        # is byte-identical with or without that declaration in scope, so the
        # digest must be too -- otherwise --check reports a current cv.md as
        # stale for a redaction that touched nothing, and import_job.py
        # refuses a perfectly good import.
        entries = load_entries(MASTER)
        before = bullet_digest(entries, [])
        redactions = load_redactions(MASTER)
        self.assertEqual(before, bullet_digest(entries, redactions))

    def test_bare_redaction_that_blocks_a_bullet_does_change_the_digest(self):
        # A redaction that actually matches an emitted bullet is a different
        # story: it collapses render_cv's body to "" (fail closed, no
        # replacement declared), which cannot collide with any real
        # document's digest. This is the property the digest needs to
        # preserve -- not the store's mere presence.
        entries = load_entries(MASTER)
        redactions = load_redactions(MASTER)
        before = bullet_digest(entries, redactions)
        _first_live_bullet(entries).text = "Ran Project Halberd."
        self.assertNotEqual(before, bullet_digest(entries, redactions))

    def test_digest_changes_when_role_frontmatter_changes(self):
        entries = load_entries(MASTER)
        redactions = load_redactions(MASTER)
        before = bullet_digest(entries, redactions)
        role = next(e for e in entries if e.type == "role")
        role.meta["title"] = "Distinguished Engineer"
        self.assertNotEqual(before, bullet_digest(entries, redactions))

    def test_digest_changes_when_a_bulletless_role_is_added(self):
        entries = load_entries(MASTER)
        redactions = load_redactions(MASTER)
        before = bullet_digest(entries, redactions)
        entries = entries + [Entry(
            id="role.new", type="role", path=Path("new-role.md"),
            meta={"company": "New Co", "title": "Engineer", "start": "2025-01"})]
        self.assertNotEqual(before, bullet_digest(entries, redactions))

    def test_digest_changes_when_contact_email_changes(self):
        entries = load_entries(MASTER)
        redactions = load_redactions(MASTER)
        before = bullet_digest(entries, redactions)
        contact = next(e for e in entries if e.type == "contact")
        contact.meta["email"] = "new-email@example.com"
        self.assertNotEqual(before, bullet_digest(entries, redactions))


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
        # A hand-edited cv.md carries no digest comment at all -- this
        # exercises the missing-digest branch, not the mismatch branch.
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        self._run("--master", str(MASTER), "--career-ops", str(tmp))
        (tmp / "cv.md").write_text("# CV -- edited by hand\n", encoding="utf-8")
        checked = self._run("--master", str(MASTER), "--career-ops", str(tmp),
                            "--check")
        self.assertEqual(checked.returncode, 1)
        self.assertIn("no_digest", checked.stdout)

    def test_check_fails_when_master_has_moved_on(self):
        # Export cleanly first (a real digest is embedded), then mutate a
        # copy of master/ and re-check -- this exercises the mismatch branch
        # specifically, which a missing-digest cv.md never reaches.
        import shutil
        import tempfile
        tmp_master = Path(tempfile.mkdtemp()) / "master"
        shutil.copytree(MASTER, tmp_master)
        tmp_co = Path(tempfile.mkdtemp())

        written = self._run("--master", str(tmp_master), "--career-ops",
                            str(tmp_co))
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)

        role_file = tmp_master / "roles" / "northwind-staff-eng.md"
        role_file.write_text(
            role_file.read_text(encoding="utf-8").replace(
                "Cut p99 checkout latency", "Cut p95 checkout latency"),
            encoding="utf-8")

        checked = self._run("--master", str(tmp_master), "--career-ops",
                            str(tmp_co), "--check")
        self.assertEqual(checked.returncode, 1)
        self.assertIn("[stale_cv]", checked.stdout)

    def test_write_replaces_a_leaky_cv_when_a_term_becomes_blocked(self):
        # A cv.md written before a term was declared withheld must not
        # survive on disk once that declaration blocks the export -- the
        # leaky artifact is the thing Finding 1 is about.
        import shutil
        import tempfile
        tmp_master = Path(tempfile.mkdtemp()) / "master"
        shutil.copytree(MASTER, tmp_master)
        tmp_co = Path(tempfile.mkdtemp())

        written = self._run("--master", str(tmp_master), "--career-ops",
                            str(tmp_co))
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
        before = (tmp_co / "cv.md").read_text(encoding="utf-8")
        self.assertIn("Migrated 38 services", before)

        role_file = tmp_master / "roles" / "northwind-staff-eng.md"
        role_file.write_text(
            role_file.read_text(encoding="utf-8").replace(
                "Migrated 38 services",
                "Ran Project Halberd, migrating 38 services"),
            encoding="utf-8")

        blocked = self._run("--master", str(tmp_master), "--career-ops",
                            str(tmp_co))
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("blocked_term", blocked.stdout)

        after = (tmp_co / "cv.md").read_text(encoding="utf-8")
        self.assertNotIn("Migrated 38 services", after)
        self.assertNotIn("Project Halberd", after)


if __name__ == "__main__":
    unittest.main()
