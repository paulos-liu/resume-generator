import json
import tempfile
import unittest
from pathlib import Path

from resumelib.draft import load_sources


class TestLoadSources(unittest.TestCase):
    def test_parses_text_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps([{"text": "a", "source": ["x.b1"]}]))
            bullets = load_sources(path)
            self.assertEqual(bullets[0].text, "a")
            self.assertEqual(bullets[0].source, ["x.b1"])

    def test_missing_source_key_becomes_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps([{"text": "a"}]))
            self.assertEqual(load_sources(path)[0].source, [])


if __name__ == "__main__":
    unittest.main()
