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

    def test_claude_md_is_a_pointer_not_a_second_copy(self):
        # Naming AGENTS.md is not enough: a CLAUDE.md that restated every rule
        # AND linked to AGENTS.md would satisfy that alone, which is exactly the
        # two-copies-no-precedence problem the split exists to prevent.
        claude = (ROOT / "CLAUDE.md").read_text()
        self.assertLess(
            len(claude.split()), 40,
            "CLAUDE.md has grown past a pointer; standing rules belong in AGENTS.md")
        sections = [
            line.strip()
            for line in (ROOT / "AGENTS.md").read_text().splitlines()
            if line.startswith("## ")
        ]
        self.assertTrue(sections, "AGENTS.md has no sections to compare against")
        for section in sections:
            self.assertNotIn(
                section, claude, f"CLAUDE.md restates AGENTS.md section {section!r}")

    def test_agents_md_names_the_sole_writer_rule(self):
        text = (ROOT / "AGENTS.md").read_text()
        self.assertIn("build-master", text)
        self.assertIn("master/", text)

    def test_agents_md_states_sole_writer_and_append_only_as_rules(self):
        # Substring checks pass even if the words are scattered across unrelated
        # prose. These assert the rules are actually stated as rules.
        lines = (ROOT / "AGENTS.md").read_text().splitlines()
        self.assertTrue(
            any("build-master" in ln and "only writer" in ln for ln in lines),
            "AGENTS.md does not state that build-master is the only writer")
        self.assertTrue(
            any("append-only" in ln.lower() for ln in lines),
            "AGENTS.md does not state that bullet IDs are append-only")
        self.assertTrue(
            any("never delete" in ln.lower() for ln in lines),
            "AGENTS.md does not state that bullets are retired, never deleted")


if __name__ == "__main__":
    unittest.main()
