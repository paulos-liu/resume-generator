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
                          "develop", "support"],
  "ban_em_dash": true,
  "max_bullet_words": 40
}
```

## Why em dashes are banned

An em dash in bullet or summary prose reads as machine-written filler, and some
screeners treat it as exactly that. The check exempts headings — the shipped
template itself separates a role title from its dates with one — and says
nothing about the en dash inside a date range. Rewrite flagged sentences with a
comma, or split them.

## Why `max_bullet_words` is 40

A bullet longer than roughly 40 words wraps past two rendered lines (Calibri
11pt, standard margins) and stops being skimmable. When trimming to fit, cut in
this order: keep the action verb, keep the metric, cut the context last — see
`style.md`. Never satisfy the budget by dropping a qualifier that limits a
claim; that is a provenance violation, not a trim.

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
