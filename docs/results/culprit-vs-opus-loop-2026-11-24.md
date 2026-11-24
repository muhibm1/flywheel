# Does Flywheel beat a plain model that can run code? A quick check

**Short answer: no.** On 10 fresh bugs, a plain Opus agent that could run code and use `git bisect`
named the right culprit change and proved it in 10 of 10 cases. Flywheel did it in 9 of 10.
Neither gave a wrong answer with a proof.

## Why this check

The earlier held-out result (`culprit-h1-2026-11-24.md`) compared Flywheel with a plain model
that was not allowed to run anything. That made the proof look like Flywheel's advantage. But
telling a model to run its own check is a one-line instruction, so the fair comparison is a model
with the same tools and no Flywheel logic. A second question was whether the model had simply
memorized these public bugs.

## Memorization

Opus's stated knowledge cutoff is June 2026. All 60 earlier bugs were introduced between July and
November 2026, so they did not exist when its training data was collected. The 10 bugs here were
all introduced on or after September 1, 2026, from projects Flywheel's culprit work had never
used (a sealed spare set, H2). Memorization cannot explain the result below.

## Setup

- **Cases.** 10 of the 30 H2 regressions introduced on or after 2026-09-01, one per project,
  picked by a fixed hash of the case id before anything ran. Same inputs as before: a short vague
  report, the working and broken versions, and an environment with the project's dependencies.
- **Flywheel.** Unchanged: a Sonnet reproducer writes a probe, the deterministic tracer bisects.
- **Plain Opus loop.** Prompt in `studies/culprit/loop/PROMPT.md`. A fresh shallow clone that
  ends at the broken version (no later commits, no tags, no remote), the report, and one neutral
  helper that runs a script against the checkout with the case's interpreter
  (`loop/run_in_tree.py`). It could read code and history, run tests and use `git bisect`. It had
  to name a commit and leave a `proof.py`.
- **Scoring** (`loop/score_quick.py`). A culprit is right when the true introducing commit is in
  the named change and not in its parent. The loop's proof is re-run 3 times at the named commit
  and 3 times at its parent; it holds only if it fails every time at the commit and passes every
  time at the parent.

## Result

| | Right culprit | With a proof that holds | Wrong answer with a proof |
|---|---|---|---|
| Plain Opus loop | 10 of 10 | 10 of 10 | 0 |
| Flywheel | 9 of 10 | 9 of 10 | 0 |

Flywheel's miss (h2-057) ended `invalid_probe`: its probe did not show the bug at the broken
version, so it gave no answer. With 10 cases the intervals are wide (Flywheel 60 to 98 percent,
the loop 72 to 100), but there is no sign of an edge for Flywheel.

## What this means

The value Flywheel claimed, a culprit that comes with a proof anyone can rerun, is real, but a
strong model gets it on its own once it is allowed to run code. Flywheel's fixed procedure does
not add accuracy over that. What is left in its favour is that it uses a cheaper model and a
search that does not depend on the model, which this check did not measure carefully.

## Disclosures

- **One setup error, fixed before scoring.** The writer that turned each case's notes into a bug
  report wrote two cases' reports into each other's folders (h2-034 and h2-044), so both systems
  first ran those two cases against a report about a different project. The swap was undone, both
  systems' outputs for those two cases were deleted, and both systems were run again on them once.
- **A first launch was stopped within seconds** because the loop prompt was missing; nothing had
  been written, and it was relaunched.
- One case's environment has a fallback interpreter that the loop's helper does not use; that
  case (h2-086) was answered correctly by both.
- The rules that keep the loop agent off the network and away from later history are
  instructions; its clone contains no later commits, but the agents' transcripts were not audited.
