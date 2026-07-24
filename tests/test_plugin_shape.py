import unittest
from pathlib import Path

from scripts.check_manifest import check

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"

REQUIRED_SKILLS = ["build-master", "setup", "tailor-resume", "render-resume"]
REQUIRED_AGENTS = ["resume-reviewer"]


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


class TestInterviewWiring(unittest.TestCase):
    def test_interview_protocol_file_exists(self):
        self.assertTrue((PLUGIN / "skills" / "build-master" / "interview.md").exists())

    def test_skill_points_at_the_interview_protocol(self):
        skill = (PLUGIN / "skills" / "build-master" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("interview.md", skill)


if __name__ == "__main__":
    unittest.main()
