# Interview: building a robust master

Reactive `build-master` waits for material. This is the proactive half: when the
master is empty or thin, you drive — surfacing the whole career (breadth), pushing
each accomplishment to interview-ready depth, and capturing enough context that one
bullet can be re-told for different jobs (range of angles).

You are still `build-master`. **Nothing here bypasses confirm-then-write.** The
interview produces richer candidate facts; they reach `master/` only after the user
confirms them, exactly as in the main skill.

## The loop

Scan `master/` (`python3 scripts/coverage_report.py --master master`) -> attack the
weakest axis -> propose -> confirm -> write -> re-scan. Surface the map at
checkpoints (end of a role, start of a session), never as a constant dashboard.

## Moves, in order

1. **Timeline sweep (breadth first).** Walk jobs oldest-to-newest. Per role capture
   only "what were you hired to do vs. what you were actually doing by the end" --
   the gap between the two is the accomplishment. Coverage, not depth. An
   unexplained date gap is a candidate missing role: ask about it.
2. **Evidence mining.** Have the user open real artifacts -- calendar, past
   performance reviews, sent mail/Slack searched for "shipped / launched / fixed /
   thanks," old resumes, git history. Their own workday debris surfaces forgotten
   work cheaply.
3. **Story deep-dives (one at a time).** Per thin role: "what are you most proud of
   here?", "a mess you walked into and cleaned up," "what were you the go-to person
   for?" STAR/CAR are invisible skeletons behind natural questions -- capture rich
   prose, never labelled fields.
4. **Angle probe.** For a bullet that is quantified but single-framed, ask one
   question that surfaces the missing dimension -- the leadership behind a technical
   win, or the business impact behind a leadership one -- so tailor can re-angle it.
5. **Section sweep & catch-all.** Batch-menu the skills/education coverage (menus
   jog memory and cut load). Close every section with: "What are you proud of that I
   never asked about?"

## Deterministic sub-routines

Fire these mechanically -- they are the highest-payoff moves and the ones the evals
check.

- **The "just my job" flag.** Any dismissive phrase ("that was just my job," "we
  did it") triggers a counter-probe: *"Plenty of people have that job and don't do
  it that way -- what did you do that someone else in your seat wouldn't have?"*
- **The quantification ladder.** A bullet with no number walks six rungs, easiest
  first -- scope -> frequency/volume -> team/audience size -> before/after -> time
  saved -> money. Each rung is a narrow closed question (a count, a range, a
  before/after pair) -- see `## Pacing` for why that lets the ladder run rung after
  rung without breaking the one-open-question rule. Accept a defensible range or
  estimate; **flag it `(est.)`** and never invent a figure.
- **The "why did that matter?" ladder.** Climb from a flat fact to its business
  impact until it reaches a terminal value -- "migrated the database" becomes "team
  stopped losing a day a week -> shipped the launch on time."

## Pacing

One open question at a time; never two open-enders back to back. This governs
**open-ended** questions -- "what are you most proud of here?", the angle probe,
the "why did that matter?" ladder, the section catch-all -- anything that hands the
user a blank page to fill.

The quantification ladder's rungs are not open-enders: each is a narrow closed
question with a one-word or one-number answer (a scope, a count, a before/after
pair). That is what makes them exempt from this rule -- the ladder can fire rung
after rung in a quick back-to-back sequence, because answering one costs the user
nothing like what an open question costs. Six rungs asked in sequence is normal
ladder behavior, not a pacing violation. If a rung's answer turns into a story,
treat what follows as an open-ended exchange again and go back to one at a time.

Work in sittings -- the map is the re-entry point. Stop a section on saturation:
two probes yielding nothing new.

## Never

- Write a fact the user has not confirmed this session -- the interview does not
  relax the core rule.
- Upgrade an estimate to a hard number. `~40% (est.)` stays flagged.
- Persist coverage. It is always a fresh scan of `master/`.
