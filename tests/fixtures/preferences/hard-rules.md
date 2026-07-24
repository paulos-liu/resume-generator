# Hard rules

Non-negotiable constraints. The reviewer enforces every rule in the block below
mechanically; violations are findings, not suggestions.

```json
{
  "max_lines": 42,
  "banned_words": ["spearheaded", "synergy", "leveraged", "utilized", "passionate"],
  "ban_first_person": true,
  "filler_adverbs": ["very", "really", "significantly", "substantially"],
  "present_tense_verbs": ["manage", "lead", "build", "own", "drive", "maintain"]
}
```

Rationale for anything unobvious goes here, in prose, where the model will read it.
