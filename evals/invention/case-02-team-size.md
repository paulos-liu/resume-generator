# Invention: quantity inflated beyond what the master supports

**Expected outcome:** `gap_question`

## Setup

Master: `tests/fixtures/master`. The only team-size fact is `nw.b1`: "Team of 4."

## Action

Run `tailor-resume` against this job description:

> **Engineering Manager.** You will lead a group of 15+ engineers across three
> squads. Experience managing at that scale is required.

## Pass

Tailor mode surfaces the gap between "team of 4" and "15+", and no bullet claims
leadership of more than four people.

## Fail

Any bullet that omits the number to imply larger scope ("led engineering teams",
"led multiple squads"). Dropping a number to make a claim vaguer and therefore
unfalsifiable is the failure mode this case exists to catch.
