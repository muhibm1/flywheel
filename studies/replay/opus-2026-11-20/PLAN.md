# Replay study, 20 November 2026: Opus on 40 changes from open-source projects, fixed before any run

## Why

On 17 November Opus with the review harness passed 87% of 30 fresh changes (Sonnet 93%). Two of
Opus's four misses were runs that hit the 15-minute limit; two were a field or exit code the task
described but did not name. The bar is now 93%.

## The setup under test (`--harness method --timeout 1800`)

One Opus call with a working method (`METHOD_PROMPT` in `src/flywheel/replay.py`):

- read the repository's instructions and the code and tests around the change;
- use the task's exact words verbatim; name anything the task describes but does not name from
  the task's own words in the code's existing style; refuse things the way neighbouring code
  already refuses them (same exception, exit code and message style);
- write the tests the task says were added, then implement;
- run the touched tests freely, the whole suite at most once near the end, trimmed;
- reread the task against `git diff`, then stop.

No review pass: it doubled the time and changed nothing measurable on 17 November. Each call may
take 30 minutes (was 15). A run that hits the limit still counts as a failure.

## Practice data

The 30 cases of 17 November and the 48 earlier cases are practice. On the 17 November cases this
setup passed 19 of 20 runs that finished before the practice run was stopped to free the
subscription for this study (records in `practice/runs/`); the miss is the case every setup has
failed. No timeouts.

## The held-out set: real changes from projects the owner did not write

- 16 public Python projects, cloned read-only (none is pushed to): structlog, attrs, click,
  sqlite-utils, more-itertools, pluggy, tenacity, humanize, filelock, platformdirs, marshmallow,
  loguru, jinja, werkzeug, llm, httpx. Specs in `studies/replay/external-repos.json`.
- Commits since 1 January 2025 changing code and tests together, 500 lines or fewer: 1,298. The
  25 newest per project: 352.
- Fair (the real tests fail before and pass after, twice each, not for a missing name): 166.
- Blind review (three Opus reviewers, the brief in `../fresh-2026-11-17/REVIEW-BRIEF.md`, plus:
  a message that only says "Fix #1234" is too thin): 125 kept. Verdicts in `task-review.json`.
- Scored: the 40 kept cases with the lowest SHA-256 of the case id, in `cases-heldout.json`.

One run per case, scored once. Pass rate with a 95% Wilson interval. Flagged runs (reached outside
the copy) are left out as before; runs that crashed on the usage limit are re-run.

## First held-out result, and what changed before the second (21 November)

The first 40 scored 36 of 39 (92%; one passing run flagged and left out), under the bar, so they
became practice data. Of the three misses, one was the harness's fault: the change added a test
fixture file next to its tests (`tests/exceptions/source/...`), and Replay put only `test_*.py`
files in place, so the real tests could not pass whatever the agent did. Two changes, both made
before the second set was opened:

- Replay now puts in place every file the change touched in the test folders, not only test
  files (`test_assets`). All 85 unused kept cases still pass the fairness check with it.
- The method asks the agent to test the cases the change implies: duplicates, empty values,
  nesting, ordering, keyword-like names.

On the 40 practice cases the revised setup passed 36 of 38 (two passing runs flagged).

## Second held-out set

The next 40 kept cases by SHA-256 order (`cases-heldout-2.json`), never run by any agent, scored
once with the setup at the commit that adds this section.
