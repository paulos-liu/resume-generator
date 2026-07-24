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
