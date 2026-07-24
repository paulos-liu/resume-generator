import unittest

from resumelib.coverage import Coverage, EntryCoverage, YearCoverage
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


class TestTimelineRender(unittest.TestCase):
    def test_unmined_year_is_marked(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=4,
            years=[YearCoverage(2021, 1), YearCoverage(2022, 3),
                   YearCoverage(2023, 0), YearCoverage(2024, 1)])])
        out = render(cov)
        self.assertIn("2023", out)
        self.assertIn("nothing recorded", out)

    def test_quiet_year_is_shown_but_not_marked_unmined(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=1,
            years=[YearCoverage(2022, 0, quiet=True), YearCoverage(2023, 1)])])
        out = render(cov)
        self.assertIn("declared quiet", out)
        self.assertNotIn("nothing recorded", out)

    def test_undated_and_out_of_range_bullets_are_reported(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=3,
            years=[YearCoverage(2021, 1)],
            undated=["a.b2"], out_of_range=[("a.b7", "2019")])])
        out = render(cov)
        self.assertIn("1 undated", out)
        self.assertIn("a.b7", out)
        self.assertIn("outside", out)

    def test_entry_without_a_timeline_still_renders(self):
        cov = Coverage(entries=[EntryCoverage(
            id="proj.a", type="project", label="NDJSON Stream", bullet_count=1)])
        self.assertIn("NDJSON Stream", render(cov))


if __name__ == "__main__":
    unittest.main()
