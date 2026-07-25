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
   Then walk *within* the role: two data points do not cover four years. Ask about
   each unmined year by name -- "2023 is blank; what were you working on?" Recall is
   time-cued, and a named year returns what "anything else?" never does. First
   clear the role's undated bullets, per the backfill rule under
   `## Deterministic sub-routines` -- an undated bullet reads as a blank year.
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
- **Date what you write.** Every bullet you propose carries the year it happened,
  as `(2023)` or `(2023-Q2)` right after the id. Ask "roughly what year was this?"
  -- a range is fine, an approximation is fine, a guess is not. Leave the token off
  rather than invent a date.
- **Backfill opportunistically -- and before you read the map as blank.** When a
  role you are already working shows undated bullets, ask their year: dating one
  bullet reliably cues the work around it, and this should never become a chore
  that blocks other progress. Do this *before* treating any of that role's years as
  unmined. Undated bullets sit outside every year on the coverage map, so a role
  with real accomplishments still undated can show every year as "0 bullet(s) --
  nothing recorded." Probing one of those years by name asks the user again for
  work they already gave you -- the exact failure the map exists to prevent. Clear
  a role's undated bullets first; only a year that is still blank after that is
  fair to probe as genuinely unmined.
- **Quiet periods are the user's call.** If a year is genuinely empty -- leave,
  illness, work under NDA -- propose recording it as `quiet: <year>` in the entry's
  frontmatter and wait for confirmation, exactly as with any other write. Probe
  first: a year spent grinding on one long project is an accomplishment, not a
  quiet year.

## Pacing

One open question at a time; never two open-enders back to back. Ladder rungs are
narrow closed questions and are exempt from that rule. Work in sittings -- the map is
the re-entry point.

**Saturation ends a topic, not a role.** Two probes yielding nothing new closes that
line of questioning. It does not close the role: people under-report their own work,
so "I think that's everything" is the moment the counter-probe exists for, not a
finish line.

**A role closes when its timeline is walked and the map shows no other marker
against it** -- every year of tenure carries at least one accomplishment or was
explicitly declared quiet, *and* the map carries no `thin`, undated-bullet, or
out-of-range marker for that role.

**Attack the largest blank first.** Target the longest unmined stretch on the map
rather than working in file order; forgotten work concentrates there.

## Never

- Write a fact the user has not confirmed this session -- the interview does not
  relax the core rule.
- Upgrade an estimate to a hard number. `~40% (est.)` stays flagged.
- Persist coverage. It is always a fresh scan of `master/`.
