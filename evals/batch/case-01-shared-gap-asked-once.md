# Batch: a gap shared by two jobs is asked about once

**Expected outcome:** `one_question_two_jobs`

## Setup

Master: a copy of `tests/fixtures/master`, with one additional live bullet
appended to any existing role so the copy clears `check_master_thin.py`'s
floor (3 entries and 8 live bullets). The checked-in fixture itself sits one
live bullet under that floor on purpose and must not be edited — see the note
in `evals/README.md`. The appended bullet must not demonstrate Kubernetes,
Kafka, or Terraform experience — it may cover anything else. This case's Pass
depends on all three remaining gaps; a bullet that happens to match one of
them would make the corresponding requirement a false match instead of a gap,
independent of anything `batch-tailor` does right or wrong.

Two library directories, each with only a `job.md`:

- `2026-08-05-acme-platform/` — a posting requiring Kubernetes and Kafka
- `2026-08-05-globex-infra/` — a posting requiring Kubernetes and Terraform

## Action

Run `batch-tailor` over both slugs.

## Pass

Kubernetes is raised **once**, naming both applications. Kafka and Terraform are
raised separately. Neither subagent writes to `master/`; the answer is written
by a single `build-master` pass between rounds.

## Fail

Kubernetes is asked about twice, or a subagent writes to `master/`, or drafting
begins before the gap questions are answered, or the batch refuses on
`check_master_thin.py` because the copy wasn't given enough bullets to clear
the gate.
