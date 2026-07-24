import unittest
from pathlib import Path

from resumelib.coverage import Coverage, EntryCoverage, scan
from scripts.check_master_thin import check

FIXTURES = Path(__file__).parent / "fixtures"


def _coverage(bullet_counts):
    return Coverage(entries=[
        EntryCoverage(id=f"role.{i}", type="role", label=f"Role {i}", bullet_count=n)
        for i, n in enumerate(bullet_counts)])


class TestCheckMasterThin(unittest.TestCase):
    def test_fewer_than_three_entries_is_thin(self):
        # 2 entries, 8 live bullets total -> still thin on entry count alone.
        cov = _coverage([4, 4])
        self.assertEqual([f.kind for f in check(cov)], ["thin_master"])

    def test_fewer_than_eight_live_bullets_is_thin(self):
        # 3 entries, 6 live bullets total -> thin on bullet count alone.
        cov = _coverage([2, 2, 2])
        self.assertEqual([f.kind for f in check(cov)], ["thin_master"])

    def test_three_entries_and_eight_bullets_is_not_thin(self):
        cov = _coverage([3, 3, 2])
        self.assertEqual(check(cov), [])

    def test_exactly_at_threshold_is_not_thin(self):
        # The rule is "fewer than", so equal to the threshold passes.
        cov = _coverage([1, 1, 1, 1, 1, 1, 1, 1])  # 8 entries, 8 bullets
        self.assertEqual(check(cov), [])

    def test_finding_detail_reports_the_counts(self):
        cov = _coverage([1, 1])
        detail = check(cov)[0].detail
        self.assertIn("2 entries", detail)
        self.assertIn("2 live bullet", detail)

    def test_empty_master_is_thin(self):
        self.assertEqual([f.kind for f in check(Coverage())], ["thin_master"])


class TestAgainstFixtureMasters(unittest.TestCase):
    def test_eval_fixture_master_is_thin_by_design(self):
        # evals/README.md documents this fixture as intentionally below the
        # threshold (2 entries / 4 live bullets) so gap-detection evals can run
        # without tripping this refusal. If this test ever fails, the eval
        # fixture's shape changed and evals/README.md's claim is now false.
        cov = scan(FIXTURES / "master")
        self.assertEqual([f.kind for f in check(cov)], ["thin_master"])

    def test_master_thin_fixture_is_thin(self):
        cov = scan(FIXTURES / "master-thin")
        self.assertEqual([f.kind for f in check(cov)], ["thin_master"])


if __name__ == "__main__":
    unittest.main()
