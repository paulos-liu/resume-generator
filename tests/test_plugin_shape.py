import json
import unittest
from pathlib import Path

from scripts.check_manifest import check

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"

REQUIRED_SKILLS = ["build-master", "setup", "tailor-resume", "render-resume",
                   "write-cover-letter", "outreach-email"]
REQUIRED_AGENTS = ["resume-reviewer", "recruiter-impressions"]


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


class TestRecruiterImpressionsWiring(unittest.TestCase):
    """The recruiter agent's value is that it is blind and advisory. Both
    properties are one helpful edit away from being lost, so both are guarded."""

    AGENT = PLUGIN / "agents" / "recruiter-impressions.md"

    def test_tailor_resume_dispatches_it(self):
        skill = (PLUGIN / "skills" / "tailor-resume" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("recruiter-impressions", skill)

    def test_agent_never_references_the_master(self):
        # It must see the resume and nothing else. The likely future edit is
        # granting it master/ access to cut down dead-end suggestions -- which
        # turns an outside reader into another insider, the one perspective the
        # rest of the system already has. Fail the build instead.
        text = self.AGENT.read_text(encoding="utf-8")
        offenders = [line.strip() for line in text.splitlines()
                     if "master/" in line and "source-of-truth" not in line]
        self.assertEqual(offenders, [], f"agent references master/: {offenders}")

    def test_agent_states_it_cannot_block_a_render(self):
        # Advisory-only is the property that keeps it from becoming the style
        # judge resume-reviewer deliberately refuses to be.
        text = self.AGENT.read_text(encoding="utf-8").lower()
        self.assertIn("review.json", text)
        self.assertIn("advice, not findings", text)

    def test_agent_is_not_hardcoded_to_technology(self):
        # It ships to anyone, so it must infer the field from the page rather
        # than assume software.
        text = self.AGENT.read_text(encoding="utf-8").lower()
        self.assertIn("field", text)
        self.assertNotIn("backend and platform engineers", text)


class TestMarketplaceManifest(unittest.TestCase):
    """`/plugin marketplace add` reads the root manifest; the plugin itself is
    described by plugin/.claude-plugin/plugin.json. Two files stating the same
    name and version drift silently, and the failure mode is a user installing
    a version that does not exist."""

    ROOT = PLUGIN.parent

    def _manifests(self):
        marketplace = json.loads(
            (self.ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        plugin = json.loads(
            (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        return marketplace, plugin

    def test_marketplace_exists_so_the_plugin_is_installable(self):
        # Without this file there is no install path at all: skills under
        # plugin/skills/ are not auto-discovered the way .claude/skills/ are.
        self.assertTrue((self.ROOT / ".claude-plugin" / "marketplace.json").exists())

    def test_name_and_version_agree_with_the_plugin(self):
        marketplace, plugin = self._manifests()
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], plugin["name"])
        self.assertEqual(entry["version"], plugin["version"])

    def test_source_resolves_to_the_plugin_directory(self):
        marketplace, _ = self._manifests()
        source = self.ROOT / marketplace["plugins"][0]["source"]
        self.assertTrue((source / ".claude-plugin" / "plugin.json").exists())


if __name__ == "__main__":
    unittest.main()
