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

- **Development projects:** mini-swe-agent, AutoGen, crewAI, smolagents (10 gates: 5 regressions, 5 controls). Their results
  are used to improve the method (the model endpoint's fidelity and the case-writing brief).
  They are reported as development numbers, never as the headline.
- **Held-out projects:** the other nine (48 gates: 24 regressions, 24 controls). They run once, with the method frozen after development.

Seen so far: mini-swe-agent only (regression not blocked, control passed). The miss is a
transport gap: the endpoint forces every tool call to be well-formed and ignores `max_tokens`, so
the malformed-call and truncation paths that change edited can never occur.

## Amendment 2 (2026-11-22, after development results for mini-swe-agent and AutoGen only)

Reviewed before adoption by an independent design review. Changes, all fixed before held-out:
- **Endpoint version 2.** Tool calls are no longer forced into the tool's schema (a model can call
  a tool wrongly, as it can live); `max_tokens` is honoured with `finish_reason: length`; `stop`
  sequences are applied; text and tool calls stream in separate chunks.
- **Transport failures are not scored.** A run that failed inside the endpoint is removed and run
  again on the same side (`transport.py`), and Flywheel's new `min_new_error_runs = 2` setting
  makes a new error count only when it repeats.
- **A ladder of arms, all reported on the same gates:** (1) the project's own tests at the change;
  (2) standing suite only; (3) plus change-aware cases written from the diff without running the
  pull request; (4) plus explored cases, where the writer may run both versions
  (`WRITER_BRIEF_v2.md`), every check citing the documented or stated behaviour it tests, and a
  separate reviewer vetoing checks that are not required behaviour (`VETO_BRIEF.md`). Arm 4 is
  reported as "Flywheel plus an automated reviewer that tries the pull request", with arm 3 beside
  it, and with how many arm 4 catches the writer had already seen fail on the pull request.
- **More controls:** the reserve second control for every held-out regression is now run too
  (48 controls), and development projects get base-against-base noise gates.
- Behaviour and run-path regressions are reported as separate rows. A regression that cannot be
  run stays in the denominator as a miss.

## Amendment 3 (2026-11-23, after development results only; before any held-out gate ran)

Why: the owner's weekly compute limit (the case-writing model ran out at 02:30 UTC) and four
development findings. Direction set by an independent design review; details in `DEV_NOTES.md`.

- **Scope, decided before any held-out gate ran.** Tier 1 = 24 held-out gates, 12 regressions and
  their first controls: agno, browser-use (3+3), deepagents (3+3), gpt-researcher,
  open_deep_research, pydantic-ai (2+2), strands. Tier 2 = adk (6+6), run only if Tier 1 finishes
  by 2026-11-25 12:00 UTC, and then as a whole project or not at all. Dropped for budget:
  OpenHands (6+6, docker runtime, never written), every second control, held-out noise gates. The
  write-up lists each dropped gate, and gives a second catch line over the original 24 held-out
  regressions with every dropped one counted as a miss.
- **Writers.** gpt-researcher, open_deep_research and agno were written by the larger model; the
  rest, and every fault case, by a smaller one. Results are split by writer model.
- **Endpoint version 2.3** (sha256 in Frozen set 2): re-asks up to twice when a tool turn comes back
  with no call and text saying a tool is unavailable (an artefact of the headless model, never
  seen from a real API); strips host-session context (memory, user details) from the model under
  test; adds the fault path below. Development runs before 2.3 had the context leak on both sides.
- **Arm 5, fault injection.** Base URL `/fault/<name>/v1` returns one scripted bad reply on a
  run's first tool turn (invalid JSON arguments, unknown tool, missing argument, truncation with
  `finish_reason: length`, empty reply, tool call written as text), identical on both sides. At most
  2 per gate, every Tier 1 gate, chosen from the diff, passing on base 2 of 2 (`FAULT_NOTE.md`).
  Reported as its own arm on top of arm 4, never folded into arms 2 to 4.
- **Timeouts.** At most 3 gates run at once. Every run that ends in a timeout is run once more on
  the same side; a second timeout stands and is scored (`run_gate.timeout_pass`). The counts are
  published. Under this rule the development noise gate that had blocked on two overload
  timeouts passes.
- **Gate settings unchanged:** 3 repetitions, `max_broken = 0`, close-call reruns 3,
  `min_new_error_runs = 2`.
- **Headline arm: arm 3** (standing plus change-aware, never saw the pull request run). Arms 2, 4
  and 5 and the averages-only baseline are reported beside it. Arm 1, the project's own tests: every
  regression in the set merged, so the project's own checks let all of them through.
- **Averages-only baseline:** block when the head's share of fully passing runs over all cases is
  lower than the base's, one-sided Fisher p < 0.05 (`score.py`).
- **Controls.** The headline false-block rate counts every blocked control. An adjudicated rate is
  reported beside it: a blocked control counts as a real behaviour change only if (a) the blocking
  cases reproduce on a fresh 3-against-3 rerun and pass base against base, (b) an adjudicator given
  the base docs, diff, pull request text and transcripts finds the failed check documented at base
  and the change not stated as intended, and (c) a later upstream issue, fix or rework of the same
  behaviour exists, found by a fixed search of the project's later history for the touched file and
  linked. Two of three is listed as "unconfirmed" and stays a false block. The same adjudicator
  checks every caught regression for whether a failing case matches the team's stated reason
  ("caught for the stated reason").
- **Veto check.** The veto reviewer dropped 5 of 5 planted non-required checks and kept 3 of 3
  required ones (development probe), so arm 4 is reported as vetoed.
- **Reporting.** Counts with Wilson 95% intervals; with 12 regressions no rate near 93% can be
  established, and the write-up says so. Behaviour (B) and run-path (C) regressions are separate
  rows. A regression whose gate cannot run is a miss.
- **Scoring is `score.py`, run once,** over the frozen case files hashed in Frozen set 2.

## Frozen set 2 (held-out, before any held-out gate ran)

Frozen in batches so the endpoint runs while the last writers finish. Writers of a later batch get
no held-out result, and every brief they follow was frozen with batch 1. Each batch's file of
sha256 sums is `freeze-<batch>.json`; its own digest is listed here. `proxy_check.py` passed on the
endpoint (version 2.3) before batch 1 ran.
- batch b1: `freeze-b1.json` sha256 8cbf06179281eaa4279e425333d64c67c0214a64a110e63f701235c0bde1f303
- batch b2: `freeze-b2.json` sha256 c572bcb8972e71882d505c3d9e8b2d393e1c0f8b8f2239468335f769b282b548
- batch b3: `freeze-b3.json` sha256 5b0db1cfb09c78db0c3688a7259b02d65042f4cb71360ee97cafe9b2051e7007
- batch b4: `freeze-b4.json` sha256 9ff3fb2ab355f5f45d0fc3fe3b0b3b577005a5192996d028d010a16ae8f91b62

## Amendment 4 (2026-11-23, after Tier 1 was scored once, before any ADK case was written)

Tier 1 was scored once (`results-heldout.json`): arm 3 blocked 6 of 12 regressions and 1 of 12
controls; arm 4 blocked 8 of 12 and 2 of 12. Those numbers stand as the Tier 1 result and are not
re-scored. All four misses were input-condition bugs that no case fed (a CRLF file, a history
seeded with a model message, a failing upload, the final delivery turn of a structured run), and
neither blocked control reproduced on the step (a) rerun. Tier 1 is development data from here on.
Two changes, frozen before any ADK case is written, are tested on Tier 2 (adk-g1 to adk-g12,
6 regressions and 6 first controls), which nobody has run or written cases for:

- **Input-condition sweep (arm 6 = standing + change + sweep).** Writers follow
  `/tmp/rr/blind/SWEEP_NOTE.md` after `change.jsonl` and before running head: for each changed
  path, one case per input class that reaches it (content form, pre-seeded state, dependency or
  tool failure, output mode and final turn), at most 8 per gate, each passing on base 2 of 2.
  Arm 6 is the ADK primary. Arms 3 and 4 run unchanged as replication. Arm 5 (faults) is not run
  on ADK, to fit the usage budget.
- **Reproduction in the gate (`confirm.py`).** A blocked gate reruns only its broken cases, 3 runs
  each, on base twice and head once. An arm's block stands (`<arm>c`) only if its own broken cases
  block head against base and pass base against base. Both the plain and confirmed counts are
  reported. The confirmed rule is also applied to Tier 1 afterwards and labelled post hoc.
- ADK cases are frozen with `freeze_batch.py adk` before the first ADK gate runs; scoring is
  `score.py`, run once on ADK. Tier 1 and ADK are reported side by side, never pooled. Deadline
  2026-11-25 12:00 UTC; if ADK is not finished by then the write-up says it was not run.
- With 6 regressions, even 6 of 6 has a Wilson lower bound near 61%; no rate near 93% can be
  established, and the write-up says so.

## Frozen set 3 (ADK, Amendment 4)

- method: `freeze-adk-method.json` sha256 29b1fd4a0f497e1e8b43f561532fe2c427888024ff32452fd6f56d52867eb09d (before any ADK case)
- cases before any head run: `freeze-adk-pre-explore.json` sha256 331bdd283c0f6bc99a865b16e7ed8540bb9ca9830ce453d1d5b35eb6b53ea38f
- batch adk-a (g1 to g6), before any ADK gate ran: `freeze-adk-a.json` sha256 9eef884792be78ca52aa1b2419673e931c8b42ea5d78a201402cab05f0986153
- batch adk-b (g7 to g12), before any of them ran: `freeze-adk-b.json` sha256 121d14d858ff0113ceffe7d7c821d1c277f2cf21196a083c4060a0ea01adf45d. g7 and g12 add one gate-local check each to flywheel.toml (check_live_direct, check_confirmations); both return True for every case that does not set their input, so standing, change and sweep cases are unaffected.
