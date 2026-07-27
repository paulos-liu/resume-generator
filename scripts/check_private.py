#!/usr/bin/env python3
"""Decide whether this working copy is safe to write employment history into.

`master/` ends up holding a real name, real employers, and real dates, and git
history is published along with the tree -- deleting the files later does not
unpublish them. So the check has to happen before the first personal fact is
written, which is `setup`, not after.

Two separate questions, because they fail differently:

  1. Did the user make their own copy, or are they working in the upstream tool
     repo? Writing personal facts into the shared repo is the mistake that
     cannot be walked back.
  2. Is that copy private?

Deliberately fails closed. "Cannot tell" is reported as not-safe: the cost of a
false negative is a permanently public employment history, and the cost of a
false positive is one question to the user.
"""

from __future__ import annotations

import argparse
import json
import subprocess

SAFE, UNSAFE, UNKNOWN = "SAFE", "UNSAFE", "UNKNOWN"

GITHUB_HOSTS = ("github.com",)

# Substrings identifying the shared upstream repo this tool is distributed from,
# e.g. ("owner/resume-generator",). Fill this in when the tool is published.
#
# While this is empty the "am I in the upstream repo?" question is UNDECIDABLE,
# not merely unchecked: a private repo you own looks identical to the original
# private repo you own. The script reports UNKNOWN in that case rather than
# SAFE. Being private is evidence about who can read the repo; it is no evidence
# at all about whether it is your copy.
UPSTREAM_REPOS: tuple = ()


def _run(cmd: list) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def classify(remote_url: str | None, visibility: str | None,
             upstream: tuple = UPSTREAM_REPOS) -> tuple:
    """(status, message). Pure, so the decision table is testable without git."""
    if remote_url is None:
        return UNKNOWN, (
            "no git remote is configured, so this may not be your own copy. "
            "Confirm with the user that they intend a purely local repo. If they "
            "want a backup or an audit trail they can trust, they should create "
            "their own PRIVATE repo first and point origin at it")

    if any(marker in remote_url for marker in upstream):
        return UNSAFE, (
            f"remote {remote_url} is the shared upstream tool repo, not a "
            "personal copy. Employment history written here would land in the "
            "repo everyone else pulls from. The user needs their own copy first "
            "-- see README.md 'Getting your own copy'")

    if not any(host in remote_url for host in GITHUB_HOSTS):
        return UNKNOWN, (
            f"remote {remote_url!r} is not GitHub, so visibility cannot be "
            "checked automatically. Confirm by hand that it is private, and that "
            "it is the user's own copy, before writing employment history")

    if visibility is None:
        return UNKNOWN, (
            "GitHub remote found but visibility could not be read (is `gh` "
            "installed and authenticated?). Confirm by hand that the repo is "
            "private and is the user's own copy")

    if visibility.upper() != "PRIVATE":
        return UNSAFE, (
            f"remote {remote_url} is {visibility.upper()}. Personal facts written "
            "here would be published, and so would every commit containing them "
            "-- deleting the files later does not remove them from history")

    if not upstream:
        return UNKNOWN, (
            f"remote {remote_url} is PRIVATE, but the upstream repo identity is "
            "not configured, so this cannot be distinguished from the original "
            "tool repo -- a private repo you own looks exactly like the private "
            "original you own. Ask the user directly whether this is their own "
            "copy. To make this decidable, set UPSTREAM_REPOS in "
            "scripts/check_private.py once the tool has a published home")

    return SAFE, (f"remote {remote_url} is PRIVATE and does not match the "
                  "upstream tool repo")


def _remote_url() -> str | None:
    return _run(["git", "remote", "get-url", "origin"]) or None


def _visibility(remote_url: str) -> str | None:
    raw = _run(["gh", "repo", "view", remote_url, "--json", "visibility"])
    if not raw:
        return None
    try:
        return json.loads(raw).get("visibility")
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    remote = _remote_url()
    status, message = classify(remote, _visibility(remote) if remote else None)
    print(f"[{status}] {message}")
    if status == SAFE:
        return 0
    print("\nStop. Do not write to master/ or preferences/ until this is resolved.")
    print("See README.md 'Getting your own copy'.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
