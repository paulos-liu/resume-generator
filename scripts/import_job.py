#!/usr/bin/env python3
"""Import a scored career-ops posting into library/ as job.md.

Only the posting crosses. The evaluation report stays in career-ops: it is a
scouting note, and library/ holds claims the user may have to defend.

    python3 scripts/import_job.py 012
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.cvexport import cv_staleness, render_cv  # noqa: E402
from resumelib.draft import Finding  # noqa: E402
from resumelib.master import load_entries  # noqa: E402
from resumelib.redactions import load_redactions  # noqa: E402
from scripts.export_cv_md import career_ops_root  # noqa: E402

FIELD_RE = re.compile(r"^\*\*(Company|Title|Score|Source):\*\*\s*(.+)$")
LOCAL_RE = re.compile(r"^local:(.+)$")


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return text.strip("-")


def parse_report(path: Path) -> dict:
    report = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = FIELD_RE.match(line.strip())
        if not match:
            continue
        key, value = match.group(1).lower(), match.group(2).strip()
        report[key] = value
    source = report.pop("source", "")
    local = LOCAL_RE.match(source)
    report["jd_path"] = local.group(1) if local else source
    return report


def missing_fields(report: dict) -> list:
    """Upstream owns the report format and may change it. Name what is missing
    rather than crashing on a KeyError three frames later."""
    return [f for f in ("company", "title", "score", "jd_path") if not report.get(f)]


def import_job(report_num: str, career_ops: Path, library: Path,
               today: str) -> tuple:
    career_ops, library = Path(career_ops), Path(library)
    matches = sorted((career_ops / "reports").glob(f"{report_num}-*.md"))
    if not matches:
        return Path(), [Finding(
            "no_report", f"no report {report_num} under {career_ops}/reports")]
    report = parse_report(matches[0])
    missing = missing_fields(report)
    if missing:
        return Path(), [Finding(
            "unreadable_report",
            f"{matches[0]} is missing {', '.join(missing)}; career-ops may have "
            "changed its report format")]

    slug = f"{today}-{slugify(report['company'])}-{slugify(report['title'])}"
    target_dir = library / slug
    if target_dir.exists():
        return target_dir, [Finding(
            "already_imported", f"{target_dir} already exists; delete it to "
            "re-import, or tailor the existing application")]

    jd_path = career_ops / report["jd_path"]
    if not jd_path.exists():
        return Path(), [Finding(
            "no_jd", f"report {report_num} points at {jd_path}, which is missing")]

    header = (f"# {report['company']} — {report['title']}. Captured {today} "
              f"from career-ops report {report_num} (score {report['score']}), "
              f"{report['jd_path']}.")
    target_dir.mkdir(parents=True)
    job = target_dir / "job.md"
    job.write_text(f"{header}\n\n{jd_path.read_text(encoding='utf-8')}",
                   encoding="utf-8")
    return job, []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--career-ops", type=Path, default=None)
    parser.add_argument("--library", type=Path, default=Path("library"))
    parser.add_argument("--master", type=Path, default=Path("master"))
    args = parser.parse_args()

    career_ops = career_ops_root(args.career_ops)

    # A score computed against a stale cv.md is not evidence about the current
    # master, so importing on the strength of it would be importing a guess.
    # cv_staleness is the same function export_cv_md.py --check uses, so the
    # two can never disagree about what counts as current.
    cv = career_ops / "cv.md"
    entries = load_entries(args.master)
    redactions = load_redactions(args.master)

    # A stale-looking cv.md can have two very different causes, and "re-run
    # the export" is only the right advice for one of them. If master/
    # currently has a bullet naming a withheld term with no replacement
    # declared, render_cv refuses to produce a body at all -- re-running
    # export_cv_md.py just writes a refusal stub (or leaves the mismatch in
    # place), never a valid cv.md, so telling the user to re-export sends
    # them in a circle. Check that first, the same way export_cv_md.py itself
    # does, so the two scripts never disagree about the cause either.
    _, blocking = render_cv(entries, redactions)
    if blocking:
        for finding in blocking:
            print(f"[{finding.kind}] {finding.detail}")
        print(f"\n{cv} cannot be brought current by re-exporting: master/ has "
              "a term withheld with no replacement declared. Resolve it in "
              "master/redactions.md (add a replacement, or remove the term) "
              "before re-running scripts/export_cv_md.py and re-scoring.")
        return 1

    reason = cv_staleness(entries, redactions, cv)
    if reason == "missing":
        print(f"[missing_cv] {cv} does not exist; "
              "run scripts/export_cv_md.py and re-score before importing")
        return 1
    if reason == "no_digest":
        print(f"[stale_cv] {cv} carries no master-sha256 comment (hand-edited, "
              "or predates export_cv_md.py); "
              "run scripts/export_cv_md.py and re-score before importing")
        return 1
    if reason == "stale":
        print(f"[stale_cv] {cv} does not match master/; "
              "run scripts/export_cv_md.py and re-score before importing")
        return 1

    path, findings = import_job(args.report, career_ops, args.library,
                                today=datetime.date.today().isoformat())
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        return 1
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
