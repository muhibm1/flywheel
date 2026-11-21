# Replay, 21 November 2026: Opus on real changes from open-source projects

In plain words: Replay checks whether a coding agent can redo a change that really shipped. It
rewinds a repository to just before the change, gives the agent the commit message as its task,
and lets the real change's own tests decide pass or fail. This round asked whether Opus clears 93%
on code its owner did not write: changes from 16 public Python projects such as click, attrs,
werkzeug, pluggy and marshmallow.

**Result.** On the third fresh set, 45 real changes no agent had ever been run on, scored once with
the setup frozen in advance, Opus passed **98% (44 of 45, 95% interval 88% to 100%)**. No run timed
out, crashed or was flagged. The two earlier fresh sets scored 92% and 90%; by the rule fixed before
any run, each became practice data and a new set was drawn. All three numbers are reported here.

What it means for putting an agent into a team's codebase: on unfamiliar, well-maintained Python
projects, Opus with a written working method redoes 9 to 10 real changes in 10 from the commit
message alone. The misses are almost all changes whose message does not say what the tests check.

## The three fresh sets

| Set | Setup | Passed | Pass rate |
| --- | --- | ---: | --- |
| 1 (40 changes) | method, one attempt | 36 of 39 | 92% (one run flagged and left out) |
| 2 (40 changes) | method with edge cases, one attempt | 36 of 40 | 90% |
| 3 (45 changes) | method with edge cases, up to three attempts | **44 of 45** | **98% (88% to 100%)** |

Sets 1 and 2 count: they are real, unseen results under the bar, and they are why the setup
changed. Set 3 is the number the setup is held to.

## How the cases were chosen

| Step | Count |
| --- | ---: |
| Commits since 1 January 2025 in 16 public Python projects that change code and tests together, 500 lines or fewer | 1,298 |
| The 25 newest per project | 352 |
| Fair: the real tests fail before and pass after, twice each, not for a missing name | 166 |
| Kept by a blind review (three Opus reviewers who never saw an agent result; a message that only says "Fix #1234" is too thin) | 125 |

Sets were drawn in order of the SHA-256 of the case id: the first 40, the next 40, then the last 45.
The projects were cloned read-only and nothing was pushed to them. Plan, verdicts and every run's
record are in `studies/replay/opus-2026-11-20/`.

## The setup

`flywheel replay run --harness method --attempts 3 --timeout 1800`

- **A working method** (`METHOD_PROMPT` in `src/flywheel/replay.py`): read the repository's
  instructions and the code and tests around the change; use the task's exact words; name anything
  unnamed in the code's existing style; refuse things the way neighbouring code does; write the
  tests the task implies, including duplicates, empty values, nesting, ordering and keyword-like
  names; run the touched tests; reread the task against `git diff`.
- **Independent attempts that vote with their own tests.** Each attempt works in its own copy. An
  attempt's tests count only if they pass on its own code; each attempt scores a point for every
  such test, from any attempt, that its code passes, and the highest score is chosen. The real
  change's tests are never read to choose. When the first two attempts each pass every test either
  one wrote, the third is never started: on set 3 that happened 39 times out of 45.
- **30 minutes per attempt**; a run that hits the limit counts as a failure.

Mean usage on set 3: 1.05 million tokens and 3 minutes per change, about twice a single attempt
(485,000 tokens on set 2) and about the same as the work-and-review setup of 17 November.

## What changed between sets, and why

- After set 1: one miss was the harness's fault. The change added a test fixture file next to its
  tests, and Replay put only `test_*.py` files in place. Replay now puts every file the change
  touched in the test folders in place; all unused cases were rechecked fair with it.
- After set 2: three of four misses failed on every attempt (the message is too thin); one was
  variance. The voting attempts were added for variance. On 16 practice cases they turned two of
  six earlier misses into passes and lost no finished pass.

## Honest reading

- On set 3 the first attempt alone also passed 44 of 45, and the vote changed the pick twice, both
  between passing attempts. So this set's 98% is not evidence that voting adds points; the evidence
  for voting is the practice data, and it is small.
- Sets 1 to 3 together: 116 of 124 scored runs passed (94%).
- The one set-3 miss (`llm-8c9728488e`, "Report unknown embedding models instead of a missing
  default") failed on both attempts; the tests check an exact error message the task does not give.
- 45 cases with one run each; the interval is wide. Python libraries only.

## Reproduce

```
flywheel replay run --spec studies/replay/external-repos.json \
  --cases studies/replay/opus-2026-11-20/cases-heldout-3.json --models opus --reps 1 \
  --clean-settings --harness method --setup method2-x3 --attempts 3 --timeout 1800 \
  --out studies/replay/opus-2026-11-20/runs-heldout-3
flywheel replay report studies/replay/opus-2026-11-20/runs-heldout-3
```

All runs used the Claude subscription; no API credit was spent.
