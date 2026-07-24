#!/usr/bin/env python3
"""Grade recorded eval results against each case's declared expectation.

The eval itself needs a human or agent to run; the pass/fail decision does not,
and should not.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resumelib.draft import Finding  # noqa: E402


def check(results_path: Path) -> list:
    results = json.loads(Path(results_path).read_text(encoding="utf-8"))
    findings = []
    for result in results:
        case = result.get("case", "<unnamed>")
        expected = result.get("expected")
        actual = result.get("actual")
        if actual is None:
            findings.append(Finding("eval_not_run", f"{case}: no result recorded"))
        elif actual != expected:
            findings.append(Finding(
                "eval_failed", f"{case}: expected {expected!r}, got {actual!r}"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, default=Path("evals/results.json"),
                        nargs="?")
    args = parser.parse_args()

    findings = check(args.results)
    for finding in findings:
        print(f"[{finding.kind}] {finding.detail}")
    if findings:
        print(f"\n{len(findings)} eval finding(s).")
        return 1
    print("evals: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
