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


class TestUndatedContext(unittest.TestCase):
    """An undated bullet counts toward no year, so a role whose bullets are all
    undated prints "nothing recorded" against every year while its real work sits
    in the undated list. The marker is what gets acted on, so it must carry that
    context rather than leaving the reader to find it further down."""

    def _all_undated(self):
        return Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=3,
            years=[YearCoverage(2021, 0), YearCoverage(2022, 0)],
            undated=["a.b1", "a.b2", "a.b3"])])

    def test_unmined_marker_names_the_unplaced_bullets(self):
        out = render(self._all_undated())
        self.assertIn("nothing recorded (3 undated bullet(s) unplaced)", out)

    def test_undated_line_precedes_the_year_rows_it_explains(self):
        lines = render(self._all_undated()).splitlines()
        undated_at = next(i for i, ln in enumerate(lines) if "undated bullet(s):" in ln)
        first_year_at = next(i for i, ln in enumerate(lines) if "2021" in ln)
        self.assertLess(undated_at, first_year_at)

    def test_marker_is_unadorned_when_nothing_is_undated(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=1,
            years=[YearCoverage(2021, 1), YearCoverage(2022, 0)])])
        out = render(cov)
        self.assertIn("<- nothing recorded", out)
        self.assertNotIn("unplaced", out)


class TestBadQuietRender(unittest.TestCase):
    def test_unparsed_quiet_value_is_surfaced(self):
        # Silently dropping it would let the interview re-probe a period the user
        # already declared quiet -- asking twice about, say, a medical leave.
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=1,
            years=[YearCoverage(2024, 0)], bad_quiet=["2024-Q1"])])
        out = render(cov)
        self.assertIn("2024-Q1", out)
        self.assertIn("bare years only", out)


class TestTenureInHeader(unittest.TestCase):
    def test_tenure_range_is_shown_when_known(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=1,
            start="2021-03", end="2024-08")])
        self.assertIn("2021-03 -> 2024-08", render(cov))

    def test_ongoing_role_shows_an_open_range(self):
        cov = Coverage(entries=[EntryCoverage(
            id="role.a", type="role", label="Acme Staff Engineer", bullet_count=1,
            start="2021-03")])
        self.assertIn("2021-03 -> now", render(cov))

    def test_entry_without_dates_shows_no_range(self):
        cov = Coverage(entries=[EntryCoverage(
            id="proj.a", type="project", label="NDJSON Stream", bullet_count=1)])
        self.assertNotIn("->", render(cov))


if __name__ == "__main__":
    unittest.main()
