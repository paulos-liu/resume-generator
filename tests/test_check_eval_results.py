import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_eval_results import CheckError, check

DISCOVERY_FIXTURE = Path(__file__).parent / "fixtures" / "evals_discovery"


def write(tmp, payload, name="results.json"):
    path = Path(tmp) / name
    path.write_text(json.dumps(payload))
    return path


class TestCheckEvalResults(unittest.TestCase):
    def test_matching_results_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, [{"case": "a", "expected": "gap_question",
                                "actual": "gap_question"}])
            self.assertEqual(check(path), [])

    def test_mismatch_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, [{"case": "a", "expected": "gap_question",
                                "actual": "drafted_bullet"}])
            findings = check(path)
            self.assertEqual([f.kind for f in findings], ["eval_failed"])
            self.assertIn("a", findings[0].detail)

    def test_missing_actual_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, [{"case": "a", "expected": "gap_question"}])
            self.assertEqual([f.kind for f in check(path)], ["eval_not_run"])


class TestCaseDiscovery(unittest.TestCase):
    """A case that is entirely absent from results.json must not be invisible."""

    def test_case_file_on_disk_with_no_recorded_result_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Only case-01-foo is recorded; case-02-bar and both faithfulness
            # cases exist on disk (see tests/fixtures/evals_discovery) but were
            # never run.
            path = write(tmp, [{"case": "interview/case-01-foo",
                                "expected": "gap_question", "actual": "gap_question"}])
            findings = check(path, evals_root=DISCOVERY_FIXTURE)
            kinds_and_cases = {(f.kind, f.detail.split(":")[0]) for f in findings}
            self.assertIn(("eval_not_run", "interview/case-02-bar"), kinds_and_cases)
            self.assertIn(("eval_not_run", "faithfulness/case-01-alpha"), kinds_and_cases)
            self.assertIn(("eval_not_run", "faithfulness/case-02-beta"), kinds_and_cases)

    def test_recorded_case_is_not_double_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, [{"case": "interview/case-01-foo",
                                "expected": "gap_question", "actual": "gap_question"}])
            findings = check(path, evals_root=DISCOVERY_FIXTURE)
            cases = [f.detail.split(":")[0] for f in findings]
            self.assertNotIn("interview/case-01-foo", cases)

    def test_empty_results_list_with_undiscovered_cases_still_fails(self):
        # An empty results.json used to print "evals: OK". It must not, when
        # cases exist on disk and were never recorded.
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, [])
            findings = check(path, evals_root=DISCOVERY_FIXTURE)
            self.assertTrue(findings)
            self.assertTrue(all(f.kind == "eval_not_run" for f in findings))

    def test_no_evals_root_provided_defaults_to_results_sibling(self):
        # Real usage: evals/results.json discovers cases from evals/*/case-*.md
        # without an explicit evals_root argument.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "interview").mkdir()
            (Path(tmp) / "interview" / "case-09-solo.md").write_text("# case\n")
            path = write(tmp, [])
            findings = check(path)
            self.assertEqual([f.kind for f in findings], ["eval_not_run"])
            self.assertIn("interview/case-09-solo", findings[0].detail)


class TestErrorHandling(unittest.TestCase):
    def test_missing_results_file_raises_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist.json"
            with self.assertRaises(CheckError):
                check(missing)

    def test_malformed_json_raises_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.json"
            path.write_text("{not valid json")
            with self.assertRaises(CheckError):
                check(path)


if __name__ == "__main__":
    unittest.main()
