import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_review import check, record


def _write_draft(dir_path, text="- Reduced latency 40%\n"):
    (dir_path / "draft.md").write_text(text, encoding="utf-8")


class TestRecord(unittest.TestCase):
    def test_record_writes_clean_verdict_when_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            record(d, [])
            data = json.loads((d / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(data["verdict"], "clean")
            self.assertEqual(data["findings"], [])

    def test_record_writes_unresolved_verdict_when_findings_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            record(d, [{"kind": "unsupported", "detail": "x"}])
            data = json.loads((d / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(data["verdict"], "unresolved")
            self.assertEqual(len(data["findings"]), 1)

    def test_record_hashes_the_current_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            record(d, [])
            data = json.loads((d / "review.json").read_text(encoding="utf-8"))
            expected = hashlib.sha256((d / "draft.md").read_bytes()).hexdigest()
            self.assertEqual(data["draft_sha256"], expected)

    def test_record_overwrites_a_previous_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            record(d, [{"kind": "over_budget", "detail": "too long"}])
            record(d, [])
            data = json.loads((d / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(data["verdict"], "clean")


class TestCheck(unittest.TestCase):
    def test_missing_review_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            self.assertEqual([f.kind for f in check(d)], ["missing_review"])

    def test_clean_review_matching_draft_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            record(d, [])
            self.assertEqual(check(d), [])

    def test_unresolved_review_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            record(d, [{"kind": "over_budget", "detail": "too long"}])
            self.assertEqual([f.kind for f in check(d)], ["unresolved_review"])

    def test_draft_edited_after_review_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            record(d, [])
            _write_draft(d, "- Reduced latency 55%\n")  # hand-edited since review
            self.assertEqual([f.kind for f in check(d)], ["stale_review"])

    def test_malformed_review_json_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            (d / "review.json").write_text("{not json", encoding="utf-8")
            self.assertEqual([f.kind for f in check(d)], ["bad_review"])

    def test_missing_draft_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _write_draft(d)
            record(d, [])
            (d / "draft.md").unlink()
            self.assertEqual([f.kind for f in check(d)], ["missing_draft"])


if __name__ == "__main__":
    unittest.main()
