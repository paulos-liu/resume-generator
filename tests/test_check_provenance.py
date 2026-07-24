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

    # -- Finding 1: draft.md bullets absent from sources.json must be caught --

    def test_drafted_bullet_missing_from_sources_is_uncited(self):
        # The critical bypass: a bullet appears in draft.md but sources.json
        # simply omits it. Passing sources.json alone (old interface) still
        # must catch this, because check() now also reads the sibling draft.md.
        findings = check(FIXTURES / "drafts" / "extra-bullet" / "sources.json", MASTER)
        self.assertEqual([f.kind for f in findings], ["uncited"])
        self.assertIn("Kubernetes", findings[0].detail)

    def test_drafted_bullet_missing_from_sources_via_dir_interface(self):
        # The documented CLI interface: pass the library dir directly.
        findings = check(FIXTURES / "drafts" / "extra-bullet", MASTER)
        self.assertEqual([f.kind for f in findings], ["uncited"])

    def test_missing_draft_file_is_a_finding(self):
        # A library dir with sources.json but no draft.md cannot be verified
        # at all -- that must fail loudly, not be silently skipped.
        findings = check(FIXTURES / "drafts" / "missing-draft", MASTER)
        self.assertEqual([f.kind for f in findings], ["missing_draft"])

    # -- Finding 3: an (est.) marker on the cited master bullet must survive --

    def test_estimate_marker_preserved_has_no_finding(self):
        findings = check(FIXTURES / "drafts" / "estimate-preserved", MASTER)
        self.assertEqual(findings, [])

    def test_estimate_marker_dropped_is_a_finding(self):
        findings = check(FIXTURES / "drafts" / "estimate-dropped", MASTER)
        self.assertEqual([f.kind for f in findings], ["estimate_upgraded"])
        self.assertIn("nw.b5", findings[0].detail)


if __name__ == "__main__":
    unittest.main()
