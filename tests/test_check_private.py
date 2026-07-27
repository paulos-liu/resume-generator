import unittest

from scripts.check_private import (SAFE, UNKNOWN, UNSAFE, UPSTREAM_REPOS,
                                   classify)

UPSTREAM = ("owner/resume-generator",)


class TestShippedUpstream(unittest.TestCase):
    def test_upstream_is_configured(self):
        # An empty UPSTREAM_REPOS degrades every private repo to UNKNOWN, which
        # is honest but turns the check into a prompt to ask the user. Guard the
        # shipped value so that degradation is never silent.
        self.assertTrue(UPSTREAM_REPOS, "UPSTREAM_REPOS is empty")

    def test_upstream_entries_are_owner_slash_name(self):
        # Matched as a substring of the origin URL, so `owner/name` catches both
        # https://github.com/owner/name.git and git@github.com:owner/name.git.
        # A bare name or a full URL would match too loosely or too strictly.
        for entry in UPSTREAM_REPOS:
            with self.subTest(entry=entry):
                self.assertEqual(entry.count("/"), 1, entry)
                self.assertNotIn("://", entry)
                self.assertFalse(entry.endswith(".git"), entry)

    def test_the_real_upstream_url_is_recognised(self):
        for url in ("https://github.com/paulos-liu/resume-generator.git",
                    "git@github.com:paulos-liu/resume-generator.git"):
            with self.subTest(url=url):
                self.assertEqual(classify(url, "PRIVATE")[0], UNSAFE)


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
