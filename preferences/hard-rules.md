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

**UNCALIBRATED DEFAULT.** 42 has not actually been measured against a rendered
page — it is a placeholder, not ground truth. The calibration procedure lives in
the header comment of `templates/standard.md`; it renders the template filled
with filler bullets and counts what fits on page one. Run it for real at setup
time (`setup`'s step 3) wherever document rendering is actually available, then
replace this paragraph with the measured number and the date it was measured.
Recalibrate the same way whenever the template changes.

A "line" here means one non-blank line of the rendered output page — this
includes section headings (`## Experience`) and the name/contact line, not only
bullet lines, since a heading takes up a line of vertical space on the page just
as a bullet does.

## Conflicts

When two rules cannot both be satisfied, the reviewer surfaces the conflict rather
than picking. Record the resolution here so the same conflict cannot recur.
