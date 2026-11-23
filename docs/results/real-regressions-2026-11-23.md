# Real regressions, 23 November 2026: would Flywheel have stopped what teams actually shipped?

In plain words: open-source agent teams sometimes merge a change that breaks their agent, and later
revert or fix it. That later fix is outside proof that the change was a real regression. This study
took such changes from eight public agent projects, replayed each one through Flywheel as if it
were a new pull request, and counted how many Flywheel would have blocked. Harmless changes from
the same projects were replayed too, to count how often it blocks something it should not.

The model under test was Claude Haiku 4.5. The test cases were written by model writers who were
never told which changes were regressions. The method was written down and every case file was
hashed before any held-out change ran, and each set was scored once (`studies/real-regressions/PLAN.md`).

## Result

**Round 1: 12 real regressions and 12 harmless changes from 7 projects** (agno, browser-use,
deepagents, gpt-researcher, open_deep_research, pydantic-ai, strands-agents).

| Test cases the gate used | Regressions blocked | Harmless changes blocked |
|---|---|---|
| The project's own tests | 0 of 12 (every change shipped with them passing) | not measured |
| Standing cases, written from the docs only | 3 of 12 (9% to 53%) | 1 of 12 |
| **+ change-aware cases, written from the diff without running it (pre-registered primary)** | **6 of 12 (25% to 75%)** | **1 of 12 (2% to 35%)** |
| + explored cases, written after running both versions, each citing a source | **8 of 12 (39% to 86%)** | 2 of 12 (5% to 45%) |
| + fault-injection cases | 8 of 12 | 2 of 12 |
| Averages only (no per-case comparison), same cases | 6 of 12 | 1 of 12 |

Ranges are Wilson 95% intervals.

- **Caught for the right reason.** For 7 of the 8 regressions the explored-case gate blocked, a
  separate adjudicator (Sonnet, reading the transcripts and the diff) found a failing case that
  fails for the reason the team itself gave when it fixed the change. The eighth
  (deepagents hooks) failed a hook case that cannot be tied to the team's stated cause.
- **Harmless changes.** Two harmless changes were blocked. On a fresh rerun of only the broken
  cases, deepagents-g1 did not reproduce. odr-g1 (a large prompt and defaults rewrite) did
  reproduce. Its pull request does not state the changed behaviour as intended, but no later
  upstream fix exists, so it is labelled "unconfirmed" and counts as a false block.
- **What was missed.** All four misses were bugs that show only on an input no case used:
  - a CRLF file edited in a sandbox;
  - a message history that starts with a model's welcome message;
  - a failing upload raising a browser error;
  - the final delivery turn of a structured-output run.

  No arm failed on head for any of them.

**Round 2: a fix for the misses, tested on a fresh project.** Round 1 then became development
data. Two changes were frozen before any case was written for Google ADK, which nobody had run:
- **Input-condition sweep.** For every changed code path, one case per input class: content form,
  pre-seeded state, dependency failure, and output mode or final turn.
- **Reproduction rule.** A blocked case must break again on a rerun and must not break base
  against base.

| Test cases the gate used (Google ADK, 6 regressions, 6 harmless changes) | Regressions blocked | Harmless changes blocked |
|---|---|---|
| Standing + change-aware | 0 of 6 (0% to 39%) | 0 of 6 |
| **+ input-condition sweep (pre-registered primary for this round)** | **0 of 6 (0% to 39%)** | **0 of 6** |
| + explored cases | 2 of 6 (10% to 70%) | 0 of 6 |
| + explored cases, after the reproduction rule | 1 of 6 (3% to 56%) | 0 of 6 |
| Averages only | 0 of 6 | 0 of 6 |

The sweep did not work. It added 71 cases across 12 gates. None of them broke on any of the six
regressions; two moved by less than the noise threshold.

Four of the six ADK regressions only show under conditions a blind writer would not set up:
- 25 or more consecutive tool rounds with an output schema;
- a cloned agent whose sub-agent tools were already replaced;
- a workflow waiting on alternative events;
- tool confirmations sent over A2A.

The explored cases found the OpenAPI port's change in redirect handling, which reproduced. They
also flagged one agent-cloning case that did not reproduce.

## What this shows

1. **A gate is only as good as the cases it runs.** Every arm compares the same runs with the same
   rule; the catch rate moved only when the cases moved. The project's own unit tests let all 18
   regressions through, because by construction each change shipped with them green.
2. **Cases written from running the change find the most.** Explored cases came from running both
   versions and citing a source for the expected behaviour. They caught the most in both rounds:
   8 of 12, then 2 of 6. Cases written blind from the diff caught crash-type regressions (round 1)
   and missed condition-specific behaviour changes (round 2).
3. **The per-case comparison helps when there are many cases.** With explored cases it blocked 8
   where an averages-only rule on the same runs blocked 6. With fewer cases the two tied.
4. **No catch rate near 93% is established.** With 12 and 6 regressions, the intervals are wide.
   Round 1's best interval, 39% to 86%, does not include 93%.

Headline, stated so it cannot be stretched: **on 12 real shipped regressions across 7 projects, the
pre-registered gate blocked 6, and 8 with explored cases, while the projects' own tests blocked
none. It blocked 1 to 2 of 12 harmless changes. A fix for the misses, frozen in advance, blocked 0
of 6 on a fresh project, where explored cases blocked 2 and no harmless change was blocked.**

## How it was run

- **Changes.** Regressions are changes a team later reverted or fixed, with the team's own words
  as evidence (`studies/real-regressions/evidence/cases.json`). Each control is a later change to
  the same project with no known follow-up fix.
- **Writers.** Cases came from model writers that could see only the project's docs, source at the
  base commit, and the pull request's diff and message. Explored-case writers could also run the
  head version, but every case had to cite a written source and pass on base twice. A separate
  Sonnet reviewer vetoed explored checks that were incidental. On a planted probe it dropped 5 of
  5 non-required checks and kept 3 of 3 required ones.
- **Writer models.** Opus wrote the round-1 cases for agno, gpt-researcher and open_deep_research
  before the weekly Opus limit. Sonnet wrote or finished the rest, and all of ADK. At the primary
  arm, Opus projects blocked 3 of 3 regressions and Sonnet projects 3 of 9. Project and writer are
  confounded, so this is not a model comparison.
- **Gate settings.** 3 runs per side, 3 more on close calls. A case is broken when its pass rate
  falls by half. Zero broken cases are allowed. Two new error runs count as a break.
- **Model endpoint.** Haiku 4.5 ran through an OpenAI-compatible endpoint over the subscription
  command line, so no API money was spent.
- **Scope.** OpenHands, second controls and noise-only gates were dropped for the usage budget.
  The fault arm ran on round 1 only. In gpt-researcher no tools are offered, so its fault cases
  could not fire.

## What went wrong along the way (all disclosed in `studies/real-regressions/DEV_NOTES.md`)

- **Endpoint bugs.**
  - The headless model at first refused to call tools. A re-ask fixes it.
  - Host memory and environment details leaked into the model's context. They are now stripped.
  - Requests with no system prompt returned errors for 34 minutes. Affected writer checks were
    rerun.
  - Overload timeouts caused a false noise block. Timed-out runs are now rerun once.
- **Restarts.** The container was reclaimed twice, and long tasks are cut at two hours. Runs
  resumed from saved files. One ADK start that lost its endpoint after ten minutes was discarded
  whole and rerun, unscored.
- **Early unsealing.** Round 1 verdicts were looked at before all 24 gates had finished. Nothing
  was changed because of it.
- **The reproduction check had two bugs, fixed before any ADK gate ran.**
  - The first version cleared a block if any of its broken cases also broke base against base.
    That wrongly cleared odr-g2, which crashes on every head run.
  - The rerun for odr-g1 could not import the project's adapter, which produced a false "does not
    reproduce".

  Both fixes are in `confirm.py`, hashed with the ADK batch. Applied to round 1 afterwards and
  labelled as such, the rule keeps all 8 explored-case catches and clears one false block (6 of
  12 and 1 of 12 at the primary arm; 8 of 12 and 1 of 12 with explored cases).

## Files

- **Method:** `studies/real-regressions/PLAN.md` (Amendments 3 and 4, and the frozen digests).
- **Scores:**
  - `results-heldout.json` (round 1, scored once);
  - `results-heldout-confirmed.json` (round 1 with the reproduction rule, applied after the fact);
  - `results-adk.json` (round 2, scored once).
- **Evidence:** `evidence/<gate>/` holds each gate's report, verdict, frozen cases, veto decisions
  and reproduction result. `evidence/cases.json` and `evidence/gate-key.json` are the key that
  was sealed until scoring.
- **Adjudication:** `adjudication/ADJUDICATION.md`.
- **Code:**
  - `score.py` (scoring);
  - `confirm.py` (reproduction rule);
  - `run_gate.py` and `run_heldout.py` (gates);
  - `proxy.py` and `proxy_check.py` (endpoint);
  - `freeze_batch.py` (hashing).
