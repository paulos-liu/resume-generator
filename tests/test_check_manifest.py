import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_manifest import check


def build_plugin(tmp, skill_frontmatter):
    plugin = Path(tmp) / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "resume-assistant", "description": "d", "version": "0.1.0"}))
    skill = plugin / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\n{skill_frontmatter}\n---\n\nBody.\n")
    return plugin


class TestCheckManifest(unittest.TestCase):
    def test_valid_plugin_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, "name: build-master\ndescription: Does a thing.")
            self.assertEqual(check(plugin), [])

    def test_rejects_uppercase_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, "name: BuildMaster\ndescription: d")
            self.assertIn("bad_name", [f.kind for f in check(plugin)])

    def test_rejects_reserved_word_in_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, "name: claude-helper\ndescription: d")
            self.assertIn("reserved_word", [f.kind for f in check(plugin)])

    def test_rejects_empty_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, "name: ok-name\ndescription:")
            self.assertIn("empty_description", [f.kind for f in check(plugin)])

    def test_rejects_overlong_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = build_plugin(tmp, f"name: ok-name\ndescription: {'x' * 1025}")
            self.assertIn("long_description", [f.kind for f in check(plugin)])

    def test_rejects_missing_plugin_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()
            self.assertIn("missing_manifest", [f.kind for f in check(plugin)])


if __name__ == "__main__":
    unittest.main()
