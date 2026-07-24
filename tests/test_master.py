import unittest
from pathlib import Path

from resumelib.master import Bullet, Entry, _parse_bullets, load_bullets, load_entries, split_frontmatter

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
        self.assertEqual(
            ids,
            {"role.northwind.staff-eng", "project.ndjson-stream", "role.harbor.data-eng"},
        )


class TestLoadBullets(unittest.TestCase):
    def test_extracts_bullet_ids_and_text(self):
        bullets = load_bullets(FIXTURES)
        self.assertIn("nw.b1", bullets)
        self.assertIn("340ms to 90ms", bullets["nw.b1"].text)

    def test_joins_wrapped_continuation_lines(self):
        bullets = load_bullets(FIXTURES)
        self.assertIn("re-architecting the cart service", bullets["nw.b1"].text)
        self.assertNotIn("\n", bullets["nw.b1"].text)

    def test_marks_retired_bullets(self):
        bullets = load_bullets(FIXTURES)
        self.assertTrue(bullets["nw.b4"].retired)
        self.assertFalse(bullets["nw.b1"].retired)

    def test_retired_bullets_are_still_loaded(self):
        # Retired IDs must resolve so old library entries do not dangle.
        self.assertIn("nw.b4", load_bullets(FIXTURES))


class TestPeriodToken(unittest.TestCase):
    def test_year_token_is_parsed_and_stripped(self):
        bullets = _parse_bullets("- [a.b1] (2023) Shipped the billing rewrite.")
        self.assertEqual(bullets[0].period, "2023")
        self.assertEqual(bullets[0].text, "Shipped the billing rewrite.")

    def test_quarter_token_is_parsed_and_stripped(self):
        bullets = _parse_bullets("- [a.b1] (2022-Q3) Cut latency 73%.")
        self.assertEqual(bullets[0].period, "2022-Q3")
        self.assertEqual(bullets[0].text, "Cut latency 73%.")

    def test_bullet_without_token_is_undated(self):
        bullets = _parse_bullets("- [a.b1] Introduced trunk-based development.")
        self.assertIsNone(bullets[0].period)
        self.assertEqual(bullets[0].text, "Introduced trunk-based development.")

    def test_malformed_token_stays_in_text(self):
        # A wrong date is worse than no date: anything not matching the grammar
        # is left alone rather than guessed at.
        for raw in ("(22-Q3)", "(2022-Q9)", "(last year)"):
            bullets = _parse_bullets(f"- [a.b1] {raw} Did a thing.")
            self.assertIsNone(bullets[0].period, raw)
            self.assertEqual(bullets[0].text, f"{raw} Did a thing.")

    def test_parenthetical_later_in_text_is_not_a_period(self):
        # (est.) and mid-text parentheses must survive untouched -- the estimate
        # check in check_provenance.py greps the source text for "(est.)".
        bullets = _parse_bullets("- [a.b1] Cut build time roughly 40% (est.).")
        self.assertIsNone(bullets[0].period)
        self.assertIn("(est.)", bullets[0].text)

    def test_year_in_text_is_not_stripped_when_not_leading(self):
        bullets = _parse_bullets("- [a.b1] Shipped it (2023) after a long haul.")
        self.assertIsNone(bullets[0].period)
        self.assertIn("(2023)", bullets[0].text)


if __name__ == "__main__":
    unittest.main()
