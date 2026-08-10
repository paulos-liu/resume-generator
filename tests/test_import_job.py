import shutil
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


def _seed_career_ops(dest: Path) -> None:
    (dest / "reports").mkdir()
    (dest / "jds").mkdir()
    for src in (CAREER_OPS / "reports").glob("*.md"):
        (dest / "reports" / src.name).write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8")
    for src in (CAREER_OPS / "jds").glob("*.md"):
        (dest / "jds" / src.name).write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8")


class TestStalenessGate(unittest.TestCase):
    def test_refuses_when_cv_has_no_digest(self):
        # A hand-written cv.md carries no digest comment at all -- this
        # exercises the missing-digest branch, not the mismatch branch.
        career_ops = Path(tempfile.mkdtemp())
        _seed_career_ops(career_ops)
        (career_ops / "cv.md").write_text("# CV -- hand written\n",
                                          encoding="utf-8")
        library = Path(tempfile.mkdtemp())
        result = subprocess.run(
            [sys.executable, "scripts/import_job.py", "012",
             "--career-ops", str(career_ops), "--library", str(library),
             "--master", str(MASTER)],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("[stale_cv]", result.stdout)

    def test_refuses_when_cv_was_built_from_a_different_master(self):
        # Export a real, current cv.md against a copy of master/, then
        # mutate that copy and import against it -- this exercises the
        # digest *mismatch* branch specifically, which a missing-digest
        # cv.md never reaches.
        career_ops = Path(tempfile.mkdtemp())
        _seed_career_ops(career_ops)

        tmp_master = Path(tempfile.mkdtemp()) / "master"
        shutil.copytree(MASTER, tmp_master)

        exported = subprocess.run(
            [sys.executable, "scripts/export_cv_md.py",
             "--master", str(tmp_master), "--career-ops", str(career_ops)],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(exported.returncode, 0,
                         exported.stdout + exported.stderr)

        role_file = tmp_master / "roles" / "northwind-staff-eng.md"
        role_file.write_text(
            role_file.read_text(encoding="utf-8").replace(
                "Cut p99 checkout latency", "Cut p95 checkout latency"),
            encoding="utf-8")

        library = Path(tempfile.mkdtemp())
        result = subprocess.run(
            [sys.executable, "scripts/import_job.py", "012",
             "--career-ops", str(career_ops), "--library", str(library),
             "--master", str(tmp_master)],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("[stale_cv]", result.stdout)


if __name__ == "__main__":
    unittest.main()
