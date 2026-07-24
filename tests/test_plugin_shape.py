import unittest
from pathlib import Path

from scripts.check_manifest import check

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"

REQUIRED_SKILLS = ["build-master"]
REQUIRED_AGENTS = []


class TestPluginShape(unittest.TestCase):
    def test_required_skills_exist(self):
        for name in REQUIRED_SKILLS:
            self.assertTrue((PLUGIN / "skills" / name / "SKILL.md").exists(),
                            f"missing plugin/skills/{name}/SKILL.md")

    def test_required_agents_exist(self):
        for name in REQUIRED_AGENTS:
            self.assertTrue((PLUGIN / "agents" / f"{name}.md").exists(),
                            f"missing plugin/agents/{name}.md")

    def test_manifest_and_frontmatter_are_valid(self):
        findings = check(PLUGIN)
        self.assertEqual(findings, [], "\n".join(f"{f.kind}: {f.detail}" for f in findings))


if __name__ == "__main__":
    unittest.main()
