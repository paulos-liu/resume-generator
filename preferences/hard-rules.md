# Hard rules

Non-negotiable constraints on every tailored resume. The reviewer enforces every
rule in the block below mechanically — violations are findings, not suggestions.

Anything decidable by parsing belongs here rather than in `style.md`, because a
rule here is enforced and a rule there is only ever applied.

```json
{
  "max_lines": 42,
  "banned_words": ["spearheaded", "synergy", "leveraged", "utilized", "passionate",
                   "results-driven", "team player", "go-getter"],
  "ban_first_person": true,
  "filler_adverbs": ["very", "really", "significantly", "substantially", "highly"],
  "present_tense_verbs": ["manage", "lead", "build", "own", "drive", "maintain",
                          "develop", "support"]
}
```

## Why `max_lines` is 42

Calibrated against `templates/standard.md`: filled with filler text at the
template's font and margins, 42 non-blank lines is the most that fits on one page.
Recalibrate by re-running the procedure in that file's header comment whenever the
template changes.

## Conflicts

When two rules cannot both be satisfied, the reviewer surfaces the conflict rather
than picking. Record the resolution here so the same conflict cannot recur.
