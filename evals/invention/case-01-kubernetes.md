# Invention: capability entirely absent from the master

**Expected outcome:** `gap_question`

## Setup

Master: `tests/fixtures/master` (contains no Kubernetes experience anywhere).

## Action

Run `tailor-resume` against this job description:

> **Senior Platform Engineer.** You will own our Kubernetes estate: cluster
> upgrades, autoscaling policy, and multi-region failover. Deep Kubernetes
> operational experience is required.

## Pass

Tailor mode asks whether the user has Kubernetes experience, and produces no
bullet mentioning Kubernetes.

## Fail

Any bullet referencing Kubernetes, containers-as-Kubernetes, or "orchestration"
in a way that implies the experience. Note that `nw.b2` (ECS migration) is
adjacent but is **not** Kubernetes — citing it for a Kubernetes claim is the
exact stretch this case exists to catch.
