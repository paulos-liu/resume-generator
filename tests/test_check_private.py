import unittest

from scripts.check_private import SAFE, UNKNOWN, UNSAFE, classify

UPSTREAM = ("owner/resume-generator",)


def status(remote, visibility, upstream=UPSTREAM):
    return classify(remote, visibility, upstream=upstream)[0]


class TestClassify(unittest.TestCase):
    def test_private_github_copy_is_safe(self):
        self.assertEqual(
            status("https://github.com/someone/my-resume.git", "PRIVATE"), SAFE)

    def test_public_repo_is_unsafe(self):
        self.assertEqual(
            status("https://github.com/someone/my-resume.git", "PUBLIC"), UNSAFE)

    def test_upstream_repo_is_unsafe_even_when_private(self):
        # Being private does not make the shared repo the right place for one
        # person's employment history.
        self.assertEqual(
            status("https://github.com/owner/resume-generator.git", "PRIVATE"),
            UNSAFE)

    def test_upstream_check_matches_ssh_remotes_too(self):
        self.assertEqual(
            status("git@github.com:owner/resume-generator.git", "PRIVATE"), UNSAFE)

    def test_no_remote_is_unknown_not_safe(self):
        # Fails closed: no remote may mean "deliberately local" or "cloned the
        # tool and never made a copy", and those need different answers.
        self.assertEqual(status(None, None), UNKNOWN)

    def test_non_github_remote_is_unknown(self):
        self.assertEqual(
            status("https://gitlab.com/someone/my-resume.git", None), UNKNOWN)

    def test_unreadable_visibility_is_unknown(self):
        self.assertEqual(
            status("https://github.com/someone/my-resume.git", None), UNKNOWN)

    def test_visibility_match_is_case_insensitive(self):
        self.assertEqual(
            status("https://github.com/someone/my-resume.git", "private"), SAFE)

    def test_private_is_not_safe_when_upstream_is_unconfigured(self):
        # The hole this test exists for: a private repo you own is
        # indistinguishable from the private original you own. Being private
        # says who can read it, not whose copy it is -- so with no upstream
        # configured the honest answer is UNKNOWN, never SAFE.
        self.assertEqual(
            status("https://github.com/someone/my-resume.git", "PRIVATE",
                   upstream=()), UNKNOWN)

    def test_public_is_still_unsafe_when_upstream_is_unconfigured(self):
        # Unconfigured upstream must not weaken the visibility check.
        self.assertEqual(
            status("https://github.com/owner/resume-generator.git", "PUBLIC",
                   upstream=()), UNSAFE)

    def test_message_is_returned_with_every_status(self):
        for remote, vis in (("https://github.com/a/b.git", "PUBLIC"),
                            ("https://github.com/a/b.git", "PRIVATE"),
                            (None, None)):
            with self.subTest(remote=remote):
                _, message = classify(remote, vis, upstream=UPSTREAM)
                self.assertTrue(message.strip())


if __name__ == "__main__":
    unittest.main()
