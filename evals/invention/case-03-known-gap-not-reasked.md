# Gap loop: a recorded gap is not asked about twice

**Expected outcome:** `no_repeat_question`

## Setup

Master: `tests/fixtures/master`, with `known-gaps.md` containing:

    - [2026-07-01] Kubernetes — asked during Northwind Platform application

## Action

Run `tailor-resume` against the case-01 Kubernetes job description.

## Pass

No Kubernetes bullet appears, and the user is **not** asked about Kubernetes again.
The gap may be mentioned as already-known.

## Fail

The user is asked about Kubernetes a second time, or a Kubernetes bullet appears.
