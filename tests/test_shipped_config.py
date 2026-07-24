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
