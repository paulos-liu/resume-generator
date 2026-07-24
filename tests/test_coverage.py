import unittest
from pathlib import Path

from resumelib.coverage import (
    Coverage,
    EntryCoverage,
    entry_coverage,
    has_metric,
    missing_sections,
    scan,
    timeline_gaps,
)
from resumelib.master import Bullet, Entry


def _role(bullets, **meta):
    return Entry(id=meta.get("id", "role.x"), type=meta.get("type", "role"),
                 path=None, meta=meta, bullets=bullets)


def _dated_role(id, start, end):
    return Entry(id=id, type="role", path=None,
                 meta={"start": start, "end": end}, bullets=[])


class TestHasMetric(unittest.TestCase):
    def test_digit_counts_as_metric(self):
        self.assertTrue(has_metric("Cut latency to 90ms"))

    def test_percent_and_dollar_count(self):
        self.assertTrue(has_metric("Raised revenue 20%"))
        self.assertTrue(has_metric("Saved $1.2M"))

    def test_prose_without_number_is_unquantified(self):
        self.assertFalse(has_metric("Introduced trunk-based development"))


class TestEntryCoverage(unittest.TestCase):
    def test_role_label_is_company_and_title(self):
        entry = _role([], company="Acme", title="Staff Engineer")
        self.assertEqual(entry_coverage(entry).label, "Acme Staff Engineer")

    def test_counts_only_live_bullets(self):
        entry = _role([Bullet("a.b1", "Shipped 3 things"),
                       Bullet("a.b2", "Old claim", retired=True)])
        cov = entry_coverage(entry)
        self.assertEqual(cov.bullet_count, 1)

    def test_unquantified_lists_live_bullets_without_a_number(self):
        entry = _role([Bullet("a.b1", "Cut latency 40%"),
                       Bullet("a.b2", "Led the team")])
        self.assertEqual(entry_coverage(entry).unquantified, ["a.b2"])

    def test_role_with_fewer_than_min_bullets_is_thin(self):
        entry = _role([Bullet("a.b1", "One thing, 5x faster")])
        self.assertTrue(entry_coverage(entry).thin)

    def test_role_meeting_min_bullets_is_not_thin(self):
        entry = _role([Bullet("a.b1", "1"), Bullet("a.b2", "2"), Bullet("a.b3", "3")])
        self.assertFalse(entry_coverage(entry).thin)

    def test_non_role_is_never_thin(self):
        entry = _role([Bullet("p.b1", "One bullet")], type="project", name="NDJSON")
        self.assertFalse(entry_coverage(entry).thin)


class TestTimelineGaps(unittest.TestCase):
    def test_gap_wider_than_threshold_is_flagged(self):
        entries = [_dated_role("role.a", "2016-06", "2019-01"),
                   _dated_role("role.b", "2021-03", "2024-08")]
        self.assertEqual(timeline_gaps(entries), [("2019-01", "2021-03")])

    def test_adjacent_roles_are_not_a_gap(self):
        entries = [_dated_role("role.a", "2016-06", "2019-01"),
                   _dated_role("role.b", "2019-04", "2024-08")]
        self.assertEqual(timeline_gaps(entries), [])

    def test_ongoing_role_ends_the_chain(self):
        # role.b has no end -> current job -> nothing after it can be a gap.
        # The only gap is the earlier role.a -> role.b transition.
        entries = [_dated_role("role.b", "2021-03", ""),
                   _dated_role("role.a", "2016-06", "2019-01")]
        self.assertEqual(timeline_gaps(entries), [("2019-01", "2021-03")])

    def test_roles_are_sorted_before_comparing(self):
        entries = [_dated_role("role.b", "2021-03", "2024-08"),
                   _dated_role("role.a", "2016-06", "2019-01")]
        self.assertEqual(timeline_gaps(entries), [("2019-01", "2021-03")])

    def test_non_roles_and_undated_roles_are_ignored(self):
        entries = [_dated_role("role.a", "2016-06", "2019-01"),
                   Entry(id="proj.x", type="project", path=None, meta={}, bullets=[]),
                   _dated_role("role.b", "2021-03", "2024-08")]
        self.assertEqual(timeline_gaps(entries), [("2019-01", "2021-03")])


class TestMissingSections(unittest.TestCase):
    def test_reports_expected_sections_absent(self):
        entries = [Entry(id="role.a", type="role", path=None, meta={}, bullets=[])]
        self.assertEqual(missing_sections(entries), ["skill", "education"])

    def test_nothing_missing_when_all_present(self):
        entries = [Entry(id=f"{t}.x", type=t, path=None, meta={}, bullets=[])
                   for t in ("role", "skill", "education")]
        self.assertEqual(missing_sections(entries), [])


class TestScan(unittest.TestCase):
    def test_scan_returns_a_coverage_over_the_directory(self):
        master = Path(__file__).parent / "fixtures" / "master"
        cov = scan(master)
        self.assertIsInstance(cov, Coverage)
        self.assertTrue(any(ec.type == "role" for ec in cov.entries))
        self.assertIn("education", cov.missing_sections)


class TestScanAgainstThinMaster(unittest.TestCase):
    def setUp(self):
        self.cov = scan(Path(__file__).parent / "fixtures" / "master-thin")
        self.by_id = {ec.id: ec for ec in self.cov.entries}

    def test_one_bullet_role_is_thin(self):
        self.assertTrue(self.by_id["role.acme.senior-eng"].thin)

    def test_three_bullet_role_is_not_thin(self):
        self.assertFalse(self.by_id["role.northwind.staff-eng"].thin)

    def test_unquantified_bullets_flagged_per_role(self):
        self.assertEqual(self.by_id["role.acme.senior-eng"].unquantified, ["acme.b1"])
        self.assertEqual(self.by_id["role.northwind.staff-eng"].unquantified, ["nw.b3"])

    def test_the_employment_gap_is_flagged(self):
        self.assertEqual(self.cov.gaps, [("2019-01", "2021-03")])

    def test_missing_sections_are_skill_and_education(self):
        self.assertEqual(self.cov.missing_sections, ["skill", "education"])


import datetime

from resumelib.coverage import (
    YEAR_MIN_BULLETS, YearCoverage, quiet_years, tenure_years,
)


def _bullet(id, period=None, retired=False, text="Did a thing worth 3 points"):
    return Bullet(id=id, text=text, retired=retired, period=period)


class TestTenureYears(unittest.TestCase):
    def test_closed_range_spans_start_to_end_year(self):
        entry = _dated_role("role.a", "2021-03", "2024-08")
        self.assertEqual(tenure_years(entry), [2021, 2022, 2023, 2024])

    def test_ongoing_role_runs_to_the_reference_year(self):
        entry = _dated_role("role.a", "2022-01", "")
        self.assertEqual(tenure_years(entry, today=datetime.date(2024, 5, 1)),
                         [2022, 2023, 2024])

    def test_unparseable_start_yields_no_timeline(self):
        entry = _dated_role("role.a", "", "2024-08")
        self.assertEqual(tenure_years(entry), [])

    def test_end_before_start_yields_no_timeline(self):
        entry = _dated_role("role.a", "2024-01", "2021-01")
        self.assertEqual(tenure_years(entry), [])


class TestQuietYears(unittest.TestCase):
    def test_bare_years_are_parsed(self):
        entry = Entry(id="role.a", type="role", path=None,
                      meta={"quiet": "2023, 2025"}, bullets=[])
        self.assertEqual(quiet_years(entry), {2023, 2025})

    def test_quarter_form_and_garbage_are_ignored(self):
        # The map is year-resolution, so silencing a whole year because one quarter
        # was empty would hide three real quarters.
        entry = Entry(id="role.a", type="role", path=None,
                      meta={"quiet": "2024-Q1, banana, 2023"}, bullets=[])
        self.assertEqual(quiet_years(entry), {2023})

    def test_absent_quiet_key_is_empty(self):
        self.assertEqual(quiet_years(_dated_role("role.a", "2021-01", "2022-01")), set())


class TestTimelineCoverage(unittest.TestCase):
    def _role_with(self, bullets, **meta):
        meta.setdefault("start", "2021-01")
        meta.setdefault("end", "2023-12")
        return Entry(id="role.a", type="role", path=None, meta=meta, bullets=bullets)

    def test_years_are_bucketed_by_period(self):
        entry = self._role_with([_bullet("a.b1", "2021"), _bullet("a.b2", "2021-Q4"),
                                 _bullet("a.b3", "2023")])
        years = {yc.year: yc.bullet_count for yc in entry_coverage(entry).years}
        self.assertEqual(years, {2021: 2, 2022: 0, 2023: 1})

    def test_a_year_with_nothing_recorded_is_unmined(self):
        entry = self._role_with([_bullet("a.b1", "2021"), _bullet("a.b2", "2023")])
        unmined = [yc.year for yc in entry_coverage(entry).years if yc.unmined]
        self.assertEqual(unmined, [2022])

    def test_a_declared_quiet_year_is_not_unmined(self):
        entry = self._role_with([_bullet("a.b1", "2021"), _bullet("a.b2", "2023")],
                                quiet="2022")
        cov = entry_coverage(entry)
        self.assertEqual([yc.year for yc in cov.years if yc.unmined], [])
        self.assertTrue([yc for yc in cov.years if yc.year == 2022][0].quiet)

    def test_undated_bullets_are_listed_not_guessed(self):
        entry = self._role_with([_bullet("a.b1", "2021"), _bullet("a.b2")])
        self.assertEqual(entry_coverage(entry).undated, ["a.b2"])

    def test_bullet_dated_outside_tenure_is_reported(self):
        entry = self._role_with([_bullet("a.b1", "2019")])
        self.assertEqual(entry_coverage(entry).out_of_range, [("a.b1", "2019")])

    def test_retired_bullets_do_not_count_toward_a_year(self):
        entry = self._role_with([_bullet("a.b1", "2022", retired=True)])
        years = {yc.year: yc.bullet_count for yc in entry_coverage(entry).years}
        self.assertEqual(years[2022], 0)

    def test_thin_still_fires_independently_of_the_timeline(self):
        # A one-year role must not clear the bar on a single bullet.
        entry = Entry(id="role.a", type="role", path=None,
                      meta={"start": "2021-01", "end": "2021-12"},
                      bullets=[_bullet("a.b1", "2021")])
        cov = entry_coverage(entry)
        self.assertTrue(cov.thin)
        self.assertEqual([yc.year for yc in cov.years if yc.unmined], [])

    def test_project_without_dates_has_no_timeline(self):
        entry = Entry(id="proj.a", type="project", path=None, meta={},
                      bullets=[_bullet("a.b1")])
        self.assertEqual(entry_coverage(entry).years, [])

    def test_dated_bullet_on_an_undated_entry_is_not_out_of_range(self):
        # A project has no tenure, so its dated bullet is unplaceable rather
        # than misfiled. Reporting it as out-of-range would be a false alarm.
        entry = Entry(id="proj.a", type="project", path=None, meta={},
                      bullets=[_bullet("a.b1", "2020")])
        cov = entry_coverage(entry)
        self.assertEqual(cov.out_of_range, [])
        self.assertEqual(cov.undated, [])


FIXTURE_MASTER = Path(__file__).parent / "fixtures" / "master"


class TestScanOverTheFixtureMaster(unittest.TestCase):
    def test_northwind_has_an_unmined_year_and_an_undated_bullet(self):
        cov = scan(FIXTURE_MASTER)
        northwind = [e for e in cov.entries if e.id == "role.northwind.staff-eng"][0]
        self.assertEqual([yc.year for yc in northwind.years if yc.unmined], [2024])
        self.assertEqual(northwind.undated, ["nw.b5"])

    def test_harbor_quiet_year_is_not_unmined(self):
        cov = scan(FIXTURE_MASTER)
        harbor = [e for e in cov.entries if e.id == "role.harbor.data-eng"][0]
        self.assertEqual([yc.year for yc in harbor.years if yc.unmined], [])
        self.assertTrue([yc for yc in harbor.years if yc.year == 2019][0].quiet)


if __name__ == "__main__":
    unittest.main()
