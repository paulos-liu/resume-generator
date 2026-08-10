# tests/fixtures/master-sections

Purpose-built for `test_cvexport.py`'s populated-section tests: a `contact` entry, a
`skill` entry with live bullets, an `education` entry, and one `role` entry so
`render_cv`'s Work Experience heading has something to sit alongside.

This is deliberately **not** `tests/fixtures/master`. That fixture is pinned one live
bullet below `scripts/check_master_thin.py`'s thin-master threshold (see
`evals/README.md`), because the invention, faithfulness, and interview/case-06 evals
depend on `check_master_thin` refusing against it. Adding a populated skills section
there would push it past the threshold and flip that refusal, breaking those evals.

If you need more section coverage, extend this fixture, not `tests/fixtures/master`.
