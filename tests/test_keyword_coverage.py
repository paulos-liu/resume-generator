import tempfile
import unittest
from pathlib import Path

from scripts.keyword_coverage import parse_requirements, render, scan

REQUIREMENTS = """\
# Requirements

- [must] Kubernetes operations — nw.b2
- [must] Terraform — NO MATCH
- [nice] GraphQL APIs — nw.b3
- [must] Incident response -- nw.b4
"""

DRAFT = """\
# Jordan Rivera

## Experience

### Engineer, Acme — 2019–2022

- Ran Kubernetes operations for a 40-service platform
- Led incident responses across three regions
"""


def _scan(requirements_text, draft_text):
    with tempfile.TemporaryDirectory() as tmp:
        requirements = Path(tmp) / "requirements.md"
        draft = Path(tmp) / "draft.md"
        requirements.write_text(requirements_text)
        draft.write_text(draft_text)
        return scan(requirements, draft)


class TestParseRequirements(unittest.TestCase):
    def test_parses_priority_text_and_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirements.md"
            path.write_text(REQUIREMENTS)
            parsed = parse_requirements(path)
        self.assertEqual([r.priority for r in parsed],
                         ["must", "must", "nice", "must"])
        self.assertEqual(parsed[0].text, "Kubernetes operations")
        self.assertTrue(parsed[0].matched)
        self.assertFalse(parsed[1].matched)

    def test_double_hyphen_separator_also_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirements.md"
            path.write_text(REQUIREMENTS)
            parsed = parse_requirements(path)
        self.assertEqual(parsed[3].text, "Incident response")

    def test_non_requirement_lines_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirements.md"
            path.write_text("# Requirements\n\nprose line\n")
            self.assertEqual(parse_requirements(path), [])


class TestScan(unittest.TestCase):
    def test_matched_requirement_with_terms_in_draft_is_full(self):
        statuses = {r.text: r.status for r in _scan(REQUIREMENTS, DRAFT)}
        self.assertEqual(statuses["Kubernetes operations"], "FULL")

    def test_plural_in_draft_matches_singular_term(self):
        # "incident response" must be found in "incident responses".
        statuses = {r.text: r.status for r in _scan(REQUIREMENTS, DRAFT)}
        self.assertEqual(statuses["Incident response"], "FULL")

    def test_matched_requirement_absent_from_draft_is_missing(self):
        statuses = {r.text: r.status for r in _scan(REQUIREMENTS, DRAFT)}
        self.assertEqual(statuses["GraphQL APIs"], "MISSING")

    def test_no_match_requirement_is_a_gap_not_a_miss(self):
        # An honest gap must never be counted against the draft: pressuring
        # the draft to name an unmatched term is pressure to invent.
        terraform = next(r for r in _scan(REQUIREMENTS, DRAFT)
                         if r.text == "Terraform")
        self.assertEqual(terraform.status, "GAP")
        self.assertEqual(terraform.missing, [])

    def test_partial_when_some_terms_surface(self):
        requirements = "- [must] Kubernetes cost optimization — nw.b2\n"
        result = _scan(requirements, DRAFT)[0]
        self.assertEqual(result.status, "PARTIAL")
        self.assertIn("kubernetes", result.present)
        self.assertIn("optimization", result.missing)

    def test_term_match_is_word_bounded(self):
        # "Go" is filtered by length; check a 3-letter term does not match
        # inside a longer word.
        requirements = "- [must] AWS — nw.b2\n"
        result = _scan(requirements, "- Sawsawed through the backlog\n")[0]
        self.assertEqual(result.status, "MISSING")


class TestRender(unittest.TestCase):
    def test_report_names_missing_terms_and_counts_gaps(self):
        report = render(_scan(REQUIREMENTS, DRAFT))
        self.assertIn("draft never says: graphql", report)
        self.assertIn("1 honest gap(s)", report)


if __name__ == "__main__":
    unittest.main()
