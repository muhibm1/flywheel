# Would Flywheel have stopped regressions that real agent teams shipped?

Written 2026-11-22, before any replay ran. Nothing below changes after the first scored run.

## The question in plain words

Open-source agent teams sometimes merge a change, ship it, and then take it back because the
agent got worse. That revert is a verdict someone else reached, on their own agent, with their own
users. This study replays each such change through Flywheel's gate, as if it were a new pull
request, and asks two things:

1. **Catch rate.** Of the changes the teams later reverted for making the agent worse, how many
   would the gate have blocked?
2. **False-block rate.** Of ordinary changes from the same weeks that nobody reverted, how many
   would the gate have blocked by mistake?

## Where the cases come from

`survey-2026-11-22/` (also in the project files) lists 119 introducing-change and fix pairs from
23 projects, found by reading commit history only. A pair enters the scored set only if all hold:

- **Behavioural.** The change altered what the model sees or how the loop is steered (prompt or
  tool text, history assembly, compaction, step limits, stop rules, defaults), or broke code an
  ordinary run executes.
- **The team says it got worse,** in the fix or revert message, the linked PR, or the changelog.
  A bare "Revert X" with no reason is excluded: we cannot tell a regression from a change of mind.
- **The introducing commit is pinned** with high or medium confidence.
- **It runs on Claude** without another vendor's key, a paid cloud service or a sandbox this
  container cannot host.

Candidates meeting all four at survey time: about 12 to 14. The exact list is frozen in
`cases.json` before any run, with the reason each excluded pair was dropped.

**Harmless controls.** For each regression, one or two commits from the same project, touching the
same area within the same month, that were never reverted or fixed. Picked by a script with a
fixed seed from that filtered list, not by hand.

## What the gate runs on (written blind)

The weak point of any replay like this is test cases written by someone who knows what broke.
So, for each project:

- A separate agent is given the repository at the commit **before** the change, the project's
  README and docs, and nothing about the change, the fix or this study. It writes 6 to 10 test
  cases the way a team adopting Flywheel would: typical tasks for this agent, each with a check.
- Where the project already ships its own evals or example tasks at that commit, those are used
  first, and the blind agent only fills gaps.
- Cases and checks are frozen, hashed, and committed before either side runs.

## How each gate runs

Base = the commit before the change. Head = the change. Same cases, same model, same settings,
3 runs a side, pooled control runs where noise needs it. Flywheel's standing rules decide
(per-case "broken" = pass rate fell by half; errors that start count), with `close_call_repetitions`
on. No rule is tuned on these cases. The model is chosen once up front for the whole study.

## Scoring, once

- Catch rate = regressions blocked / regressions run. A regression that cannot be run after an
  honest attempt is reported as "not run", with the reason, not dropped.
- False-block rate = controls blocked / controls run.
- Baseline beside each: the project's own test suite at the change (did it pass?), and a
  gate that compares averages only.

## Honesty rules

- The scored set, the blind cases, the model and the gate settings are committed before the first
  scored run. Any practice runs use pairs outside the scored set and are reported as practice.
- Every run's raw output is kept in `runs/`.
- If the catch rate is low, the report says so and says why (case coverage, noise, or a regression
  that only shows on another vendor's model), rather than re-scoring.

## Cost

Model calls run on the Max subscription through `claude -p`, if Muhammad allows that command for
this study. API credit: $0 planned. If the route changes, the cost is restated and waits for his go.
