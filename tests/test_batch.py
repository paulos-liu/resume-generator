import unittest

from resumelib.batch import (
    Gap, group_gaps, next_round, normalize_requirement,
)


class TestNormalize(unittest.TestCase):
    def test_case_and_whitespace_are_ignored(self):
        self.assertEqual(normalize_requirement("  Kubernetes   Operations "),
                         normalize_requirement("kubernetes operations"))

    def test_trailing_punctuation_is_ignored(self):
        self.assertEqual(normalize_requirement("Kubernetes."),
                         normalize_requirement("Kubernetes"))

    def test_distinct_requirements_stay_distinct(self):
        self.assertNotEqual(normalize_requirement("Kubernetes"),
                            normalize_requirement("Kafka"))

    def test_plus_and_hash_are_significant_characters(self):
        self.assertEqual(normalize_requirement("C++"), "c++")
        self.assertEqual(normalize_requirement("C#"), "c#")
        self.assertEqual(normalize_requirement("C"), "c")
        keys = {normalize_requirement("C++"), normalize_requirement("C#"),
                normalize_requirement("C")}
        self.assertEqual(len(keys), 3)

    def test_years_with_plus_qualifier_stays_distinct_from_plain_years(self):
        self.assertNotEqual(normalize_requirement("3+ years"),
                            normalize_requirement("3 years"))
        self.assertEqual(normalize_requirement("3+ years"), "3+ years")
        self.assertEqual(normalize_requirement("3 years"), "3 years")

    def test_punctuation_only_requirement_normalizes_to_falsy(self):
        self.assertFalse(normalize_requirement("..."))


class TestGroup(unittest.TestCase):
    def test_same_requirement_across_jobs_is_one_question(self):
        questions = group_gaps([
            Gap("2026-08-05-acme-swe", "Kubernetes"),
            Gap("2026-08-05-globex-swe", "kubernetes "),
        ])
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].job_slugs,
                         ["2026-08-05-acme-swe", "2026-08-05-globex-swe"])

    def test_keeps_the_first_spelling_for_the_question_text(self):
        questions = group_gaps([
            Gap("a", "Kubernetes operations"),
            Gap("b", "kubernetes operations"),
        ])
        self.assertEqual(questions[0].requirement, "Kubernetes operations")

    def test_distinct_requirements_stay_separate(self):
        questions = group_gaps([Gap("a", "Kubernetes"), Gap("a", "Kafka")])
        self.assertEqual(len(questions), 2)

    def test_a_job_listed_twice_appears_once(self):
        questions = group_gaps([Gap("a", "Kubernetes"), Gap("a", "kubernetes")])
        self.assertEqual(questions[0].job_slugs, ["a"])

    def test_no_gaps_is_no_questions(self):
        self.assertEqual(group_gaps([]), [])

    def test_cpp_and_csharp_are_not_merged(self):
        questions = group_gaps([Gap("a", "C++"), Gap("b", "C#")])
        self.assertEqual(len(questions), 2)


class TestTermination(unittest.TestCase):
    def test_stops_when_a_round_produces_nothing_new(self):
        self.assertFalse(next_round(round_index=1, new_questions=0))

    def test_continues_when_questions_remain_and_rounds_are_left(self):
        self.assertTrue(next_round(round_index=1, new_questions=3))

    def test_stops_at_the_round_cap(self):
        self.assertFalse(next_round(round_index=2, new_questions=3))


if __name__ == "__main__":
    unittest.main()
