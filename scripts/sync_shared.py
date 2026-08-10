#!/usr/bin/env python3
"""Copy this repo's shared layer into the public tool repo.

Invariant 7: real personal data never leaves master/, preferences/, and
library/. Those three are the user's; everything else is the tool.

The copy set is an allowlist, never a filter. A denylist fails open -- a new
directory holding something personal would be copied by default, and a public
git history cannot be un-published. An allowlist fails closed: anything not
named here simply does not travel.

    python3 scripts/sync_shared.py --dry-run
    python3 scripts/sync_shared.py --target ~/Projects/resume-generator
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402
from resumelib.master import load_entries  # noqa: E402
from resumelib.redactions import load_redactions  # noqa: E402

SHARED_PATHS = (
    "scripts", "resumelib", "plugin", "tests", "evals", "templates", "docs",
    "README.md", "AGENTS.md", "CLAUDE.md", ".gitignore",
)

# Named only so the allowlist can be asserted against them in tests. Nothing
# reads this to decide what to skip -- skipping is what the allowlist already
# does.
PRIVATE_PATHS = ("master", "preferences", "library", "jobs")

SKIP_NAMES = {".DS_Store", "__pycache__"}


def _walk(base: Path, entry: str) -> list:
    path = base / entry
    if path.is_symlink():
        return []
    if path.is_file():
        return [Path(entry)]
    if not path.is_dir():
        return []
    found = []
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            continue
        if not child.is_file():
            continue
        if SKIP_NAMES.intersection(child.parts):
            continue
        found.append(child.relative_to(base))
    return found


def plan_copies(source: Path) -> list:
    source = Path(source)
    planned = []
    for entry in SHARED_PATHS:
        planned.extend(_walk(source, entry))
    return planned


# Two or more Title-Cased words, letters/hyphens/apostrophes only -- shaped
# like "Jamie Sorrel", not like a section label. The contact entry's `name`
# key is documented (master/contact.md) to hold the *entry label* --
# "Contact details" -- with the real name in `full_name`. `full_name` is
# always trusted as-is. `name` is trusted only when it happens to look like a
# personal name instead, so that if a future contact entry puts a real name
# in `name` after all, the scan still catches it -- but an ordinary label
# never becomes a scan term, which would otherwise match routine prose ("the
# Contact details section...") and make every sync refuse. Do not "simplify"
# this back to reading `name` unconditionally.
_NAME_LIKE_RE = re.compile(r"^[A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,3}$")


def _looks_like_a_personal_name(value: str) -> bool:
    return bool(_NAME_LIKE_RE.match(value.strip())
                and all(word[:1].isupper() for word in value.split()))


# Hyphenated, dotted, underscored, and concatenated forms of a two-or-more
# -word name -- the shapes a handle or a username takes (the owner's own
# GitHub handle is the hyphenated form of their real name). "" (last) yields
# the concatenated form. The plain space-joined form needs no entry here:
# _identifier_pattern already treats internal whitespace in any term as
# \s+, which survives Markdown's 80-column wrap too, since \s matches a
# newline.
_NAME_JOINERS = ("-", ".", "_", "")


def _name_variants(full_name: str) -> list:
    """Punctuation/spacing variants of `full_name` beyond the literal string.
    Two or more words only: joining a single word is a no-op, and joining
    fewer than two words would risk matching on a given name alone -- a far
    more common token than the full name."""
    words = full_name.split()
    if len(words) < 2:
        return []
    return [joiner.join(words) for joiner in _NAME_JOINERS]


def _load_identifiers(master_dir: Path) -> tuple:
    """The owner's real identifiers, derived from `master/` at each run --
    never hardcoded, so a new role or a changed email is covered without a
    code change. `master/` is only read here, never written.

    Returns `(identifiers, finding)`. `identifiers` is the list of `(kind,
    term)` pairs described below. `finding` is `None` exactly when derivation
    succeeded; the caller must treat a non-`None` finding as a refusal, never
    as "nothing to protect" -- this scan exists to enforce these terms, and
    failing to derive them is a reason to stop, not a reason to proceed.

    Two distinct failures both look like "zero identifiers" if not told
    apart, and the user needs different fixes for each:
      - `master_dir` does not exist (or is not a directory) at all. A real
        checkout always has a `master/`, so this is almost always a wrong
        `--source`. Reported as `no_master`, naming the path that was
        checked.
      - `master_dir` exists but nothing in it yields a term -- no contact
        entry with a `full_name` or `email`, no role with a `company`, no
        education entry with an `institution`, no project with a `name`, and
        an empty (or absent) `redactions.md`. Every one of those fields is
        individually optional, so a real but very thin `master/` can
        legitimately land here. Reported as `no_identifiers`, distinct from
        `no_master`, so the user isn't sent chasing a path problem that
        isn't the actual cause.

    Identifiers derived, by entry type:
      - contact: `full_name` (and its punctuation/spacing variants -- see
        `_name_variants`), `name` when it looks like a personal name rather
        than a label (same variants), `email`, `phone`, `github`, `linkedin`.
      - role: `company`.
      - education: `institution`.
      - project: `name` -- a project can be named for a client or carry a
        codename, and unlike the contact entry's `name`, a project's `name`
        is never a generic section label, so it is trusted unconditionally.
      - every term `master/redactions.md` withholds.
    """
    master_dir = Path(master_dir)
    if not master_dir.is_dir():
        return [], Finding(
            "no_master",
            f"{master_dir} is not a directory; cannot derive the identifiers "
            "this scan exists to check publishable files against -- check "
            "--source")

    identifiers = []

    def _add_name(kind: str, value: str) -> None:
        identifiers.append((kind, value))
        for variant in _name_variants(value):
            identifiers.append((kind, variant))

    for entry in load_entries(master_dir):
        if entry.type == "contact":
            full_name = entry.meta.get("full_name")
            if full_name:
                _add_name("contact_name", full_name)
            name = entry.meta.get("name")
            if name and name != full_name and _looks_like_a_personal_name(name):
                _add_name("contact_name", name)
            email = entry.meta.get("email")
            if email:
                identifiers.append(("contact_email", email))
            phone = entry.meta.get("phone")
            if phone:
                identifiers.append(("contact_phone", phone))
            github = entry.meta.get("github")
            if github:
                identifiers.append(("contact_github", github))
            linkedin = entry.meta.get("linkedin")
            if linkedin:
                identifiers.append(("contact_linkedin", linkedin))
        elif entry.type == "role":
            company = entry.meta.get("company")
            if company:
                identifiers.append(("employer", company))
        elif entry.type == "education":
            institution = entry.meta.get("institution")
            if institution:
                identifiers.append(("institution", institution))
        elif entry.type == "project":
            name = entry.meta.get("name")
            if name:
                identifiers.append(("project_name", name))
    for redaction in load_redactions(master_dir):
        identifiers.append(("redacted_term", redaction.term))

    if not identifiers:
        return [], Finding(
            "no_identifiers",
            f"{master_dir} exists but no identifiers could be derived from it "
            "(no contact full_name/email, no role company, no education "
            "institution, no project name, no redactions) -- refusing to "
            "sync rather than assume there is nothing to protect")
    return identifiers, None


def _identifier_pattern(term: str) -> re.Pattern:
    # Mirrors resumelib.redactions._pattern's word-boundary anchoring: a
    # short identifier does not fire on every longer word that happens to
    # contain it. Goes further in one respect -- internal whitespace in a
    # multi-word term is matched as \s+ rather than a literal single space,
    # so a run of spaces or a Markdown line wrap (which breaks on whitespace,
    # and \s matches a newline) between the term's words still matches. That
    # widens matching, which is the safe direction here: it can only cause a
    # real occurrence to be caught, never a clean file to be flagged.
    parts = term.split()
    body = r"\s+".join(re.escape(part) for part in parts) if parts else re.escape(term)
    prefix = r"\b" if term[:1].isalnum() else ""
    suffix = r"\b" if term[-1:].isalnum() else ""
    return re.compile(prefix + body + suffix, re.IGNORECASE)


# scripts/check_private.py exists specifically to recognize the shared
# upstream repo, and tests/test_check_private.py exercises it -- both
# necessarily spell the repo's owner/name slug (UPSTREAM_REPOS) and the URLs
# built from it. That slug happens to be spelled with the same hyphenated
# form as the owner's real name and GitHub handle, so the widened name/github
# matching above flags both files. This is a deliberate, narrow, named
# allowance for exactly these two files and exactly the two identifier kinds
# that legitimately collide with the repo slug -- not a general exemption for
# either file. Every other kind (email, phone, linkedin, employer,
# institution, redacted_term, project_name) still applies to them exactly as
# it does everywhere else; if either file ever also carried, say, the real
# phone number, that would still refuse the sync.
_UPSTREAM_IDENTITY_FILES = (Path("scripts/check_private.py"),
                            Path("tests/test_check_private.py"))
_UPSTREAM_IDENTITY_KINDS = ("contact_name", "contact_github")


def _is_upstream_identity_mention(relative: Path, kind: str) -> bool:
    return relative in _UPSTREAM_IDENTITY_FILES and kind in _UPSTREAM_IDENTITY_KINDS


def scan_for_identifiers(source: Path, planned: list) -> list:
    """Scan the content of every file `plan_copies` would publish for the
    owner's real identifiers.

    Answers "what is in them", which the allowlist alone never does: a file
    can be on an allowlisted path and still carry the owner's name, email,
    an employer, an institution, or a withheld term, if someone typed it into
    a test fixture or a doc by hand instead of an invented persona.

    A finding never carries the matched string -- only the file and the kind
    of identifier that matched -- so refusing to sync cannot itself leak the
    thing it is protecting.

    If the identifiers this scan exists to check for cannot be derived at
    all, that is itself the finding (see `_load_identifiers`): no file
    content is scanned in that case, because there is nothing trustworthy to
    scan it against.
    """
    source = Path(source)
    identifiers, finding = _load_identifiers(source / "master")
    if finding:
        return [finding]

    seen = set()
    findings = []
    for relative in planned:
        path = source / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            # Skipping this silently would publish it unscanned. "Could not
            # be checked" is not evidence of "clean" -- report it and refuse,
            # same as any other finding.
            findings.append(Finding("unreadable_file", str(relative)))
            continue
        for kind, term in identifiers:
            if _is_upstream_identity_mention(relative, kind):
                continue
            key = (kind, relative)
            if key in seen:
                continue
            if _identifier_pattern(term).search(text):
                seen.add(key)
                findings.append(Finding(kind, str(relative)))
    return findings


def sync(source: Path, target: Path, dry_run: bool) -> tuple:
    """Plan and (unless `dry_run` or the content scan objects) copy every
    shared file to `target`.

    Returns `(planned, findings)`. The scan runs before any write, dry run or
    not: when `findings` is non-empty nothing is copied, because a file about
    to be published still names a real identifier and that is a fail-closed
    condition, not a preview detail.
    """
    source, target = Path(source), Path(target)
    planned = plan_copies(source)
    findings = scan_for_identifiers(source, planned)
    if dry_run or findings:
        return planned, findings
    for relative in planned:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    return planned, findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--target", type=Path,
                        default=Path("~/Projects/resume-generator").expanduser())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = args.target.expanduser()
    if not target.exists():
        print(f"[no_target] {target} does not exist")
        return 1

    planned, findings = sync(args.source, target, args.dry_run)
    if findings:
        for finding in findings:
            print(f"[{finding.kind}] {finding.detail}")
        print(f"\n{len(findings)} identifier finding(s); refusing to sync.")
        return 1

    verb = "would copy" if args.dry_run else "copied"
    print(f"{verb} {len(planned)} file(s) to {target}")
    print("master/ was read only to scan for identifiers, and was not "
          "copied; preferences/ and library/ were not read.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
