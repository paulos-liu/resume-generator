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
