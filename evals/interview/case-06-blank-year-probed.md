# Interview: a blank tenure year is probed by name

**Expected outcome:** `named_year_probe`

## Setup

Master: `tests/fixtures/master`. The Northwind Staff Engineer role runs 2021-03 to
2024-08 and has bullets dated 2021 (`nw.b3`), 2022-Q3 (`nw.b1`), and 2023 (`nw.b2`) —
leaving **2024 unmined** — plus one undated bullet (`nw.b5`).

Per `interview.md`'s backfill-ordering rule, an undated bullet counts toward no
year, so the interview must clear `nw.b5` before treating any year as unmined —
otherwise it would re-ask the user for work already given. That makes dating
`nw.b5` the mandated first move on this role, ahead of naming 2024.

## Action

1. Tell the interview to keep going on the Northwind role.
2. Observe: the interview asks the year of the undated bullet `nw.b5` — the
   mandated first move.
3. Answer with a year that is **not** 2024 — e.g. "that was 2022." `nw.b5` is now
   placed, and the role has **no undated bullets left**. 2024 is the only tenure
   year still unmined.
4. Observe what the interview asks next.

## Pass

After step 3, the role has no undated bullets remaining, so naming the blank year
is the only correct next move: the interview asks about **2024 specifically, by
name** ("2024 is blank — what were you working on?").

## Fail

The role is treated as complete once `nw.b5` is dated, or the only follow-up is an
open-ended catch-all ("anything else about this role?") that never names 2024.
