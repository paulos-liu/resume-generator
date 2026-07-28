# Standing rules

Canonical. `CLAUDE.md` points here so the two cannot drift.

## Invariants

1. **`build-master` is the only writer to `master/`.** Every other component reads
   it. This includes gap answers, corrections, and recorded non-answers.
2. **No fact reaches `master/` without the user confirming it in conversation.**
   Not from an uploaded resume, not from inference.
3. **Bullet IDs are append-only.** Never reused, never renumbered. Retract by
   moving a bullet under `## Retired`; never delete.
4. **Every drafted bullet cites a live master bullet.** Uncited is a hard failure.
   Companion artifacts — cover letters, outreach emails — are bound the same way:
   every claim they make about the user restates a cited bullet from that
   application's reviewed draft.
5. **Deterministic checks are scripts, never prompts.** If it can be parsed, it is
   not a judgement call.
6. **Personal facts belong only in the user's own private copy.** `setup` runs
   `scripts/check_private.py` first; anything other than `SAFE` stops the run
   until the user resolves it. This binds every component, not only `setup` —
   `build-master` writes names, employers and dates, and `tailor-resume` writes
   them into `library/`, and neither runs the script itself. If you are about to
   write personal data and have no evidence this is the user's own private repo,
   ask before writing.
7. **Real personal data never leaves `master/`, `preferences/`, and `library/`.**
   Those three are the user's; everything else is shared. Test fixtures,
   examples, and documentation use an invented persona — never the user's real
   name, address, email, or employers.

## Feedback routing

Whenever the user comments on a draft, classify before acting:

| Comment is about | Goes to |
|---|---|
| How it reads — phrasing, ordering, voice | `preferences/` |
| What is true — a correction, an omission, a new accomplishment | `build-master` |
| Ambiguous | **Ask. Never guess.** |

"This sounds too junior" is the canonical ambiguous case: it could mean framing
(style) or missing seniority evidence (fact). Guessing writes to the wrong store,
and a wrong write to `master/` is a fact you will later have to defend.

Within `preferences/`, split by decidability:

- Decidable by parsing (banned words, length, first person) -> `hard-rules.md`,
  where the reviewer enforces it.
- Everything else -> `style.md`, where it is applied at generation only.

Write preferences specifically: *prefer "built" over "spearheaded"*, never *be more
direct*. A preference too vague to check is too vague to apply.

**Harvest rewrites.** When the user rewrites a bullet by hand instead of describing
what they wanted, that rewrite is the cleanest style signal available — offer to
keep it as an exemplar in `style.md`.

## Before finishing any task that touched a draft

    python3 -m unittest discover -s tests
    python3 scripts/check_manifest.py plugin
