# Resume Assistant

Maintains a master resume of verified facts and produces tailored, job-specific
resumes that can never contain a claim the master does not support.

This repo is a **template**. Clone it, make your copy **private**, and commit your
own facts — `git log master/` then becomes an audit trail of every claim you have
ever made and when you added it.

## Setup

1. Clone and set the remote to a private repo of your own.
2. Attach the folder to a Claude Cowork project, or open it in Claude Code.
3. Run the `setup` skill. It elicits your hard rules, harvests style exemplars,
   and calibrates the page budget.
4. Run `build-master` and give it anything you have — an old resume, a LinkedIn
   export, a brag doc, performance reviews.

## Use

Share a job description and ask for a tailored resume. The system will:

1. Extract the job's requirements and match each to your master resume.
2. Draft only from what matches, citing a source for every bullet.
3. Review the draft in an isolated context against your master and hard rules.
4. Ask you about anything the job wants that your master does not cover — and
   write your answers back into the master, so it gets richer with every job.
5. Render an approved draft, and offer an interview prep sheet tracing every
   claim back to the fact behind it.

## Where things live

| Path | What |
|---|---|
| `master/` | Your facts. Only `build-master` writes here |
| `preferences/hard-rules.md` | Enforced constraints |
| `preferences/style.md` | Exemplars and prefer/avoid, applied at generation |
| `library/` | Every application, with its provenance |
| `scripts/` | Deterministic checks |
| `evals/` | Model-dependent checks — see `evals/README.md` |

## Tests

    python3 -m unittest discover -s tests -v
    python3 scripts/check_manifest.py plugin

No dependencies; Python 3.9+ standard library only.

## Design

`docs/superpowers/specs/2026-07-24-resume-assistant-design.md`.
