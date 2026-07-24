import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_eval_results import check


def write(tmp, payload):
    path = Path(tmp) / "results.json"
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


if __name__ == "__main__":
    unittest.main()
