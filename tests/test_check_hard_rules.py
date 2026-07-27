import tempfile
import unittest
from pathlib import Path

from resumelib.rules import Rules, load_rules
from scripts.check_hard_rules import check

FIXTURES = Path(__file__).parent / "fixtures"
RULES = load_rules(FIXTURES / "preferences" / "hard-rules.md")


def kinds(name):
    return sorted({f.kind for f in check(FIXTURES / "drafts" / name / "draft.md", RULES)})


def kinds_for(text, rules):
    """Run `check` over an inline draft under a hand-built Rules object."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(text)
        return [f.kind for f in check(path, rules)]


class TestCheckHardRules(unittest.TestCase):
    def test_clean_draft_has_no_findings(self):
        self.assertEqual(kinds("valid"), [])

    def test_flags_banned_word(self):
        self.assertIn("banned_word", kinds("rule-breaking"))

    def test_flags_first_person(self):
        self.assertIn("first_person", kinds("rule-breaking"))

    def test_flags_filler_adverb(self):
        self.assertIn("filler_adverb", kinds("rule-breaking"))

    def test_flags_present_tense_leading_verb(self):
        self.assertIn("present_tense", kinds("rule-breaking"))

    def test_banned_word_match_is_case_insensitive(self):
        findings = check(FIXTURES / "drafts" / "rule-breaking" / "draft.md", RULES)
        self.assertTrue(any("spearheaded" in f.detail.lower() for f in findings))

    def test_first_person_does_not_match_inside_words(self):
        # "I" must not match the I in "Introduced"; "my" must not match "myriad".
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text("- Introduced a myriad of improvements\n")
            self.assertEqual([f.kind for f in check(path, RULES)], [])

    def test_flags_capitalized_sentence_initial_first_person(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text("- My team reduced latency 30%.\n")
            self.assertIn("first_person", [f.kind for f in check(path, RULES)])

    def test_job_level_numeral_is_not_first_person(self):
        # "Software Engineer I" is a level, not the pronoun. Flagging it forces
        # anyone with a levelled title to write around it -- and a promotion
        # sequence is usually the clearest seniority signal a resume has.
        for text in ("### Software Engineer I to III, Lytx — Sep 2021\n",
                     "- Built it while titled Software Engineer I\n",
                     "### Analyst I, Acme\n",
                     "- Promoted from Level I to Level III\n"):
            with self.subTest(text=text):
                self.assertNotIn("first_person", kinds_for(text, RULES))

    def test_real_first_person_still_flagged_near_a_title(self):
        # The narrowing must not become a loophole.
        for text in ("- I built the platform\n",
                     "- The Product Owner and I shipped it\n",
                     "- Worked on my own initiative\n",
                     "- Engineer on our team\n"):
            with self.subTest(text=text):
                self.assertIn("first_person", kinds_for(text, RULES))

    def test_roman_numerals_above_one_never_match(self):
        self.assertNotIn("first_person", kinds_for("### Engineer II to III\n", RULES))

    def test_flags_over_budget_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text("\n".join(f"- line {n}" for n in range(60)))
            self.assertIn("over_budget", [f.kind for f in check(path, RULES)])

    def test_new_rules_are_off_when_absent_from_the_json(self):
        # The shipped fixture omits all three keys, so the `valid` draft --
        # which has no skills section and no profile link -- must stay clean.
        self.assertEqual(kinds("valid"), [])


class TestStreetAddress(unittest.TestCase):
    RULES = Rules(ban_street_address=True)

    def test_flags_address_in_contact_line(self):
        text = "# Jordan Rivera\n\n1200 Market St, Springfield, IL 62704\n"
        self.assertIn("street_address", kinds_for(text, self.RULES))

    def test_allows_city_and_state_only(self):
        text = "# Jordan Rivera\n\nSpringfield, IL · jordan@example.com\n"
        self.assertEqual(kinds_for(text, self.RULES), [])

    def test_does_not_flag_street_suffix_words_inside_bullets(self):
        # "Way" and "Dr" are street suffixes; in bullet prose they are not.
        text = "- Built a 3 way merge tool\n- Cut 500 Dr Pepper queries per second\n"
        self.assertEqual(kinds_for(text, self.RULES), [])

    def test_off_by_default(self):
        text = "1200 Market St, Springfield, IL 62704\n"
        self.assertEqual(kinds_for(text, Rules()), [])


class TestRequiredLinkHosts(unittest.TestCase):
    RULES = Rules(required_link_hosts=["github.com", "linkedin.com"])

    def test_flags_draft_with_no_profile_link(self):
        text = "# Jordan Rivera\n\nSpringfield, IL · jordan@example.com\n"
        self.assertIn("missing_profile_link", kinds_for(text, self.RULES))

    def test_accepts_either_host(self):
        for host in ("github.com/jrivera", "linkedin.com/in/jrivera"):
            with self.subTest(host=host):
                text = f"# Jordan Rivera\n\nSpringfield, IL · {host}\n"
                self.assertEqual(kinds_for(text, self.RULES), [])

    def test_host_match_is_case_insensitive(self):
        text = "# Jordan Rivera\n\nGitHub.com/JRivera\n"
        self.assertEqual(kinds_for(text, self.RULES), [])

    def test_off_when_list_is_empty(self):
        self.assertEqual(kinds_for("# Jordan Rivera\n", Rules()), [])


class TestRequireSkillsLine(unittest.TestCase):
    RULES = Rules(require_skills_line=True)

    def test_flags_draft_with_no_skills_section(self):
        text = "# Jordan Rivera\n\n## Experience\n\n- Shipped a thing\n"
        self.assertIn("missing_skills_line", kinds_for(text, self.RULES))

    def test_flags_empty_skills_section(self):
        text = "## Skills\n\n## Education\n\nB.S. Computer Science, State University\n"
        self.assertIn("missing_skills_line", kinds_for(text, self.RULES))

    def test_accepts_populated_skills_section(self):
        text = "## Skills\n\n.NET, Kafka, DynamoDB, Redis, PostgreSQL, AWS\n"
        self.assertEqual(kinds_for(text, self.RULES), [])

    def test_heading_match_is_case_insensitive(self):
        text = "## SKILLS\n\n.NET, Kafka, AWS\n"
        self.assertEqual(kinds_for(text, self.RULES), [])

    def test_off_by_default(self):
        text = "# Jordan Rivera\n\n## Experience\n\n- Shipped a thing\n"
        self.assertEqual(kinds_for(text, Rules()), [])


if __name__ == "__main__":
    unittest.main()
