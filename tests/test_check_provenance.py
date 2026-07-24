import unittest
from pathlib import Path

from scripts.check_provenance import check

FIXTURES = Path(__file__).parent / "fixtures"
MASTER = FIXTURES / "master"


def kinds(draft_name):
    return [f.kind for f in check(FIXTURES / "drafts" / draft_name / "sources.json", MASTER)]


class TestCheckProvenance(unittest.TestCase):
    def test_valid_draft_has_no_findings(self):
        self.assertEqual(kinds("valid"), [])

    def test_unknown_id_is_a_finding(self):
        self.assertEqual(kinds("unknown-id"), ["unknown_source"])

    def test_uncited_bullet_is_a_finding(self):
        self.assertEqual(kinds("uncited"), ["uncited"])

    def test_citing_a_retired_bullet_is_a_finding(self):
        self.assertEqual(kinds("retired"), ["retired_source"])

    def test_finding_detail_names_the_offending_id(self):
        findings = check(FIXTURES / "drafts" / "unknown-id" / "sources.json", MASTER)
        self.assertIn("nw.b99", findings[0].detail)


if __name__ == "__main__":
    unittest.main()
