import unittest
from pathlib import Path

from resumelib.master import load_bullets, load_entries

FIXTURES = Path(__file__).parent / "fixtures" / "master"


class TestLoadEntries(unittest.TestCase):
    def test_reads_frontmatter(self):
        entries = {e.id: e for e in load_entries(FIXTURES)}
        role = entries["role.northwind.staff-eng"]
        self.assertEqual(role.type, "role")
        self.assertEqual(role.meta["company"], "Northwind Logistics")
        self.assertEqual(role.meta["end"], "2024-08")

    def test_finds_entries_in_all_subdirs(self):
        ids = {e.id for e in load_entries(FIXTURES)}
        self.assertEqual(ids, {"role.northwind.staff-eng", "project.ndjson-stream"})


class TestLoadBullets(unittest.TestCase):
    def test_extracts_bullet_ids_and_text(self):
        bullets = load_bullets(FIXTURES)
        self.assertIn("nw.b1", bullets)
        self.assertIn("340ms to 90ms", bullets["nw.b1"].text)

    def test_joins_wrapped_continuation_lines(self):
        bullets = load_bullets(FIXTURES)
        self.assertIn("Shipped Q3 2022.", bullets["nw.b1"].text)
        self.assertNotIn("\n", bullets["nw.b1"].text)

    def test_marks_retired_bullets(self):
        bullets = load_bullets(FIXTURES)
        self.assertTrue(bullets["nw.b4"].retired)
        self.assertFalse(bullets["nw.b1"].retired)

    def test_retired_bullets_are_still_loaded(self):
        # Retired IDs must resolve so old library entries do not dangle.
        self.assertIn("nw.b4", load_bullets(FIXTURES))


if __name__ == "__main__":
    unittest.main()
