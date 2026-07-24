# Interview: a blank tenure year is probed by name

**Expected outcome:** `named_year_probe`

## Setup

Master: `tests/fixtures/master`. The Northwind Staff Engineer role runs 2021-03 to
2024-08 and has bullets dated 2021, 2022-Q3, and 2023 — leaving **2024 unmined** —
plus one undated bullet (`nw.b5`).

## Action

Enter interview mode and work the Northwind role.

## Pass

The interview asks about **2024 specifically, by name** ("2024 is blank — what were
you working on?"), rather than issuing an open-ended "anything else about this role?"
Asking the year of the undated `nw.b5` also passes.

## Fail

The role is treated as complete because it already has four bullets, or the only
follow-up is an open-ended catch-all that never names the unmined year.
