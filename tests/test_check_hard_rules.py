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
