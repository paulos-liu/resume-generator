#!/usr/bin/env python3
"""Grade recorded eval results against each case's declared expectation.

The eval itself needs a human or agent to run; the pass/fail decision does not,
and should not.

This also guards against a case being entirely absent from results.json. Only
grading what is present in results.json is fail-open: an authored case that was
never run, and so never recorded, would be invisible and the gate would print
"evals: OK" regardless. To close that hole, the expected case set is discovered
straight from disk (`evals/<category>/case-*.md`, plus the ids embedded in
`evals/faithfulness/cases.md`) and any discovered case missing a recorded
result is reported as `eval_not_run`, the same finding kind used for a
recorded-but-empty `actual`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402

JSON_FENCE_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL)


class CheckError(Exception):
    """Raised for a results file that cannot be read or parsed at all."""


def discover_cases(evals_root: Path) -> set:
    """Return the set of case ids that should have a recorded result.

    - Every `evals/<category>/case-*.md` file becomes `<category>/<stem>`,
      matching how results.json already names invention/loop/interview cases.
    - `evals/faithfulness/cases.md` holds a JSON array of case objects in a
      fenced code block rather than one file per case; each `id` becomes
      `faithfulness/<id>`, matching the existing results.json convention for
      that category.
    """
    evals_root = Path(evals_root)
    cases = set()
    if not evals_root.is_dir():
        return cases

    for path in evals_root.glob("*/case-*.md"):
        cases.add(f"{path.parent.name}/{path.stem}")

    faithfulness_cases = evals_root / "faithfulness" / "cases.md"
    if faithfulness_cases.is_file():
        match = JSON_FENCE_RE.search(faithfulness_cases.read_text(encoding="utf-8"))
        if match:
            try:
                items = json.loads(match.group(1))
            except json.JSONDecodeError:
                items = []
            for item in items:
                if isinstance(item, dict) and "id" in item:
                    cases.add(f"faithfulness/{item['id']}")

    return cases


def check(results_path: Path, evals_root: Path = None) -> list:
    results_path = Path(results_path)
    if evals_root is None:
        evals_root = results_path.parent
    else:
        evals_root = Path(evals_root)

    try:
        raw = results_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError(f"cannot read results file {results_path}: {exc}") from exc
    try:
        results = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CheckError(f"malformed results file {results_path}: {exc}") from exc

    findings = []
    recorded_cases = set()
    for result in results:
        case = result.get("case", "<unnamed>")
        recorded_cases.add(case)
        expected = result.get("expected")
        actual = result.get("actual")
        if actual is None:
            findings.append(Finding("eval_not_run", f"{case}: no result recorded"))
        elif actual != expected:
            findings.append(Finding(
                "eval_failed", f"{case}: expected {expected!r}, got {actual!r}"))

    for case in sorted(discover_cases(evals_root) - recorded_cases):
        findings.append(Finding(
            "eval_not_run", f"{case}: no result recorded (case absent from results.json)"))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, default=Path("evals/results.json"),
                        nargs="?")
    args = parser.parse_args()

    try:
        findings = check(args.results)
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} eval finding(s).")
        return 1
    print("evals: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
