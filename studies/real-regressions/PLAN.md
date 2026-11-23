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
No case writer ever sees the fix, the revert, later history, or whether the change was undone.
Two kinds of cases are scored side by side, because they answer different questions:

- **Standing suite.** What a team that adopted Flywheel would already have. A separate agent gets
  the repository at the commit **before** the change, its README, docs, examples and its own
  evals if it has any, and writes 6 to 10 typical tasks for this agent, each with a check. Where
  the project ships its own eval tasks, those come first.
- **Change-aware cases.** What Flywheel can add per pull request. A separate agent gets the same
  repository plus the change's diff and title, exactly as a reviewer sees a new PR, and writes 4
  to 6 tasks that exercise the code the diff touches. It is told nothing about the outcome, and
  harmless controls get exactly the same treatment, so this arm pays for any extra catches in
  false blocks.

Cases and checks are frozen, hashed and committed before either side of any scored gate runs.
Neither arm is tuned after scoring.

## Model and transport

Every project's own agent code runs unchanged at both commits. Model calls go to `proxy.py`, an
OpenAI-compatible endpoint answered by `claude -p` on the Max subscription, model
**claude-haiku-4-5** for every run (chosen before any run, for throughput under the subscription's
usage windows). The transport is identical on both sides of every gate.

## Two strata

- **Behaviour** (class B): the change altered prompts, tool text, history, limits or loop rules.
  This is the headline.
- **Run-path breaks** (class C): the change broke code an ordinary run executes, with the team's
  stated reason. Reported separately, because a smoke test can also catch these.

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

Model calls run on the Max subscription through `claude -p` (Muhammad allowed this for the study
on 2026-11-22). API credit: $0 planned. If the route changes, the cost is restated and waits for his go.

## Frozen set (2026-11-22, before any case was written)

- 29 regressions kept after re-checking every survey row against the team's own words and
  installing each old version (12 behaviour, 17 run-path breaks); 90 rows excluded with reasons.
- One harmless control per regression, the first pick of `pick_controls.py` (seed 20261122):
  58 gates in all. The second pick of each is kept in reserve and is not run.
- Case writers see neutral gate ids (`adk-g3`) shuffled per project, never the ids, the fixes
  or which gates are regressions. The set and the id key are sealed until the cases are frozen.
- sha256 of cases.json: `2dc77eadf8214f41aba393e237dd0a50122ddcb9a95bb161bb2ae3ad482eb7c3`
- sha256 of gate-key.json: `ef99363bbf71644a3ac7012d71bca061778d97c0d82e35662753d10baeb811c7`

## Amendment 1 (2026-11-22 22:40Z, after the first project's result, before any other)

Muhammad's bar is 93% and he asked for the best honest number, with reworks allowed. So the
projects are split now, before any other gate result is seen:

- **Development projects:** mini-swe-agent, AutoGen, crewAI, smolagents (8 gates). Their results
  are used to improve the method (the model endpoint's fidelity and the case-writing brief).
  They are reported as development numbers, never as the headline.
- **Held-out projects:** the other nine (50 gates: 21 regressions, 21 controls... exact counts in
  the final report). They run once, with the method frozen after development.

Seen so far: mini-swe-agent only (regression not blocked, control passed). The miss is a
transport gap: the endpoint forces every tool call to be well-formed and ignores `max_tokens`, so
the malformed-call and truncation paths that change edited can never occur.
