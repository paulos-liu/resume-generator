# Resume Assistant

Maintains a master resume of verified facts and produces tailored, job-specific
resumes that can never contain a claim the master does not support.

Two modes share one source of truth. **Build mode** is the only thing that writes
facts, and only after you confirm each one. **Tailor mode** reads a job description
and selects and rephrases from what is already there — it may never invent,
embellish, or stretch. Anything a job wants that your master does not cover becomes
a question, not a claim.

That rule exists to solve one failure: a resume that overstates your experience and
leaves you unable to back it up in the interview.

---

## Getting your own copy

**Do not fork this repo.** A GitHub fork of a public repo inherits that repo's
visibility and cannot be made private. Your `master/` will hold your real
employment history, so a fork would publish it.

Use one of these instead:

- **"Use this template"** on GitHub — creates an independent repo you can mark
  private. Easiest option.
- **Clone and re-point the remote:**

      git clone https://github.com/<upstream>/resume-generator.git
      cd resume-generator
      git remote remove origin
      git remote add origin git@github.com:<you>/<your-private-repo>.git
      git push -u origin main

The repo ships with `master/` empty. Everything personal you add stays in your
private copy; `git log master/` then becomes an audit trail of every claim you have
ever made and when you added it.

---

## Setup in Claude Code

Skills under `plugin/skills/` are **not** auto-discovered — that only applies to
`.claude/skills/`. This repo is a plugin, so install it:

```bash
cd resume-generator
claude
```

Then, inside Claude Code:

```
/plugin marketplace add .
/plugin install resume-assistant@resume-assistant
```

The repo root doubles as the marketplace: `.claude-plugin/marketplace.json` points
at `./plugin`. Run Claude **from the repo root** — the skills invoke
`python3 scripts/check_*.py` with paths relative to it, and they read `master/`,
`preferences/`, and `templates/` from there too.

Verify the install by running the setup skill:

```
/resume-assistant:setup
```

---

## Setup in Claude Cowork

Attach the repo to a **Cowork project**, not an ad-hoc session. A project gives a
persistent folder; work done in a one-off session does not survive cleanup, which
matters because this system's entire value is the state it accumulates.

1. Open Cowork and connect the GitHub account holding your private copy.
2. Create a **project** and attach the repo to it.
3. Install the plugin in the session the same way as above
   (`/plugin marketplace add .`, then `/plugin install`).

To have it install automatically at session start instead, commit a
`.claude/settings.json` in your private copy naming your own repo:

```json
{
  "extraKnownMarketplaces": {
    "resume-assistant": {
      "source": { "source": "github", "repo": "<you>/<your-private-repo>" }
    }
  },
  "enabledPlugins": ["resume-assistant@resume-assistant"]
}
```

Your personal `~/.claude/skills/` are not available in cloud sessions, which is
exactly why the capability ships as a repo plugin rather than as personal skills.

---

## First run

1. **`setup`** — elicits your hard rules, harvests style exemplars from writing you
   already like, and calibrates the page budget. It asks for examples rather than
   asking you to describe your "tone", because descriptions of tone do not survive
   contact with a draft.
2. **`build-master`** — give it anything: an old resume, a LinkedIn export, a brag
   doc, performance reviews. On an empty or thin master it switches to interview
   mode and drives, walking your timeline year by year rather than waiting for you
   to remember things unprompted.

Nothing is written to `master/` until you confirm the specific wording.

## Use

Share a job description and ask for a tailored resume. The system will:

1. Extract the job's requirements and match each to your master resume.
2. Draft only from what matches, citing a source for every bullet.
3. Review the draft in an isolated context against your master and hard rules.
4. Ask you about anything the job wants that your master does not cover — and write
   your answers back through build mode, so the master gets richer with every job.
5. Render an approved draft, and offer an interview prep sheet tracing every claim
   back to the fact behind it.

## Where things live

| Path | What |
|---|---|
| `master/` | Your facts. Only `build-master` writes here |
| `preferences/hard-rules.md` | Enforced constraints |
| `preferences/style.md` | Exemplars and prefer/avoid, applied at generation |
| `library/` | Every application, with its provenance |
| `plugin/` | The skills and the reviewer agent |
| `scripts/` | Deterministic checks |
| `evals/` | Model-dependent checks — see `evals/README.md` |

## Tests

    python3 -m unittest discover -s tests -v
    python3 scripts/check_manifest.py plugin

No dependencies; Python 3.9+ standard library only.

## Design

- `docs/superpowers/specs/2026-07-24-resume-assistant-design.md` — the system
- `docs/superpowers/specs/2026-07-24-master-resume-interview-design.md` — interview mode
- `docs/superpowers/specs/2026-07-24-extraction-depth-design.md` — timeline coverage
- `AGENTS.md` — the standing rules every component obeys
