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


class TestWordBoundary(unittest.TestCase):
    def test_short_alnum_term_does_not_match_inside_a_longer_word(self):
        # "Co" must not fire on "Company" -- a short withheld term embedded in
        # ordinary prose would otherwise block every bullet that contains it.
        redactions = [Redaction("Co", "a firm")]
        text, blocked = apply_redactions(
            "Company policy required review.", redactions)
        self.assertEqual(text, "Company policy required review.")
        self.assertEqual(blocked, [])

    def test_short_alnum_term_still_matches_as_a_whole_word(self):
        redactions = [Redaction("Co", "a firm")]
        text, blocked = apply_redactions("Consulted for Co on billing.", redactions)
        self.assertEqual(text, "Consulted for a firm on billing.")
        self.assertEqual(blocked, [])

    def test_term_with_trailing_punctuation_matches_as_a_substring(self):
        # "Deal!" ends in punctuation, so no trailing boundary is added --
        # \b only means something at a word/non-word transition.
        redactions = [Redaction("Deal!", None)]
        found = find_terms("Announced Deal!! internally.", redactions)
        self.assertEqual([r.term for r in found], ["Deal!"])

    def test_term_with_leading_punctuation_matches_as_a_substring(self):
        # "#ops" starts in punctuation, so no leading boundary is added --
        # it still matches immediately after "prod" with no boundary between.
        redactions = [Redaction("#ops", None)]
        found = find_terms("Tagged prod#ops in the notes.", redactions)
        self.assertEqual([r.term for r in found], ["#ops"])


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
