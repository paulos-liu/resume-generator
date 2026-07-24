import unittest

from resumelib.coverage import Coverage, EntryCoverage
from scripts.coverage_report import render


class TestRender(unittest.TestCase):
    def test_thin_role_is_marked(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Senior Engineer",
            bullet_count=1, unquantified=["acme.b1"], thin=True)])
        out = render(cov)
        self.assertIn("Acme Senior Engineer", out)
        self.assertIn("thin", out)
        self.assertIn("1 unquantified", out)

    def test_gaps_and_missing_sections_appear(self):
        cov = Coverage(entries=[], gaps=[("2019-01", "2021-03")],
                       missing_sections=["skill", "education"])
        out = render(cov)
        self.assertIn("2019-01", out)
        self.assertIn("2021-03", out)
        self.assertIn("skill", out)
        self.assertIn("education", out)

    def test_empty_master_renders_without_error(self):
        self.assertIn("MASTER COVERAGE", render(Coverage()))


if __name__ == "__main__":
    unittest.main()
