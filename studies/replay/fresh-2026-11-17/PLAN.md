# Replay study, 17 November 2026: what is scored, fixed before any held-out run

## Why a new round

On 14 November the best setup (Opus, plain prompt) passed 85% of 20 held-out cases, exactly on the
line, with an interval of 74% to 92%. This round changes the harness around the model, not the
model, and scores it on a larger set of real changes that no agent has ever been run on.

## The harness under test (`--harness protocol-review`)

Two headless agent calls in the same working copy, before the real tests are put in place:

1. **Work.** The task plus a working method: read the repository's own instructions and the code
   and tests around the change; list every concrete requirement in the task and use the task's exact
   words verbatim; write the tests the task says were added; run the touched tests and the whole
   suite; reread the task against `git diff` before finishing.
2. **Review and repair.** A fresh agent call, same model, gets the task again, reads `git diff`,
   checks every requirement line by line, runs the tests, and fixes any gap. It changes nothing if
   all is right.

The prompts are `PROTOCOL_PROMPT` and `REVIEW_PROMPT` in `src/flywheel/replay.py`. The harness also
allows a few more read-only and test commands (`npm test`, `npx`, `head`, `tail`, `wc`).

Neither call sees the hidden tests, the real commit or its diff. Pass and fail are decided exactly as
before: the real change's own test files are put in place and must pass.

## Development data

The 55 cases of the 13 November study (35 tuning, 20 earlier held-out) are now development data.
48 of them still exist in the local history and were used to measure the harness. Development
runs are in `dev/`.

## The fresh held-out set

- Source: five repositories never used in Replay before (ChangeLens `fathom`, Shu, Studbook,
  Wasl, `erp-data-platform`), plus `verity`, `foothold`, `marginalia` and `studbook-agent`, which
  produced no fair case. Commits since 1 January 2026 that change code and tests together, 500
  lines or fewer (126 candidates).
- Fair: the real tests fail before the change and pass after it, twice each, and not for a
  missing name (52).
- Blind review: two Opus reviewers, each half the cases, with the brief in `REVIEW-BRIEF.md`, the
  same rule as the 13 November review. They saw the task, the test diff and the real code diff, and
  never any agent result. Kept: 30. Verdicts in `task-review.json`.
- `cases-heldout.json` (30 cases) is scored once, with the setup frozen at the commit that adds
  this file. Nothing about the harness changes after the first held-out run starts.

## What is reported

- Per setup: pass rate with a 95% Wilson interval, mean tokens and seconds, as before.
- Runs that reached outside the copy are flagged and left out; runs that crashed on the
  subscription's usage limit are re-run and never counted. Both rules are unchanged.
- Arms: Opus with `protocol-review` (the candidate best setup), and Sonnet with
  `protocol-review`, each 1 run per case. More repeats only if the subscription allows, decided
  before any result is seen.
- If a held-out score lands under 85%, this set becomes development data and a new fresh set is
  drawn before any claim is made.
