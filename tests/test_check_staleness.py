import unittest
from pathlib import Path

from scripts.check_staleness import find_citations

LIBRARY = Path(__file__).parent / "fixtures" / "library"


class TestFindCitations(unittest.TestCase):
    def test_finds_the_application_citing_a_bullet(self):
        hits = [p.name for p in find_citations("nw.b4", LIBRARY)]
        self.assertEqual(hits, ["2026-03-11-northwind-platform"])

    def test_returns_empty_when_uncited(self):
        self.assertEqual(find_citations("nw.b99", LIBRARY), [])

    def test_finds_multiple_applications(self):
        hits = sorted(p.name for p in find_citations("nw.b1", LIBRARY))
        self.assertEqual(
            hits, ["2026-03-11-northwind-platform", "2026-05-02-acme-infra"])

    def test_results_are_sorted_by_directory_name(self):
        # nw.b1 is cited by both applications. Assert the order find_citations
        # itself returns, without sorting here -- that's the behavior under test.
        hits = [p.name for p in find_citations("nw.b1", LIBRARY)]
        self.assertEqual(
            hits, ["2026-03-11-northwind-platform", "2026-05-02-acme-infra"])


if __name__ == "__main__":
    unittest.main()
