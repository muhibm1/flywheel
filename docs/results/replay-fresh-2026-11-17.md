# Replay, 17 November 2026: 30 fresh real changes, and what actually moves the pass rate

In plain words: Replay checks whether a coding agent can redo a change that really shipped. It
rewinds a repository to just before the change, gives the agent the commit message as its task, and
lets the real change's own tests decide pass or fail. This round asked two questions. Does a better
setup around the model (a written working method, then a second pass that reviews the work and
repairs gaps) raise the pass rate? And does the earlier result hold on a larger set of changes that
no agent had ever been run on?

**Result.** On 30 fresh changes from repositories never used before, scored once with the setup
frozen in advance, Sonnet passed 93% (28 of 30) and Opus with the new setup 87% (26 of 30). A run
that hits the time limit counts as a failure. The new setup itself made no measurable difference:
plain Sonnet also passed 28 of 30, and on 42 earlier cases Opus passed 90% with the new setup and
90% without it. What separates this set from the earlier, harder one is the task text: these
commit messages are about twice as long and say what to build. The earlier misses were mostly
cases where the tests checked a name or a wording the task never gave.

What it means for putting an agent into a team's codebase: on well-described changes to Python
services, Sonnet reproduces 9 in 10 real changes on its own, at about half of Opus's tokens and
time. Spend effort on how tasks are written before spending it on more agent steps.

## The setup that was tested

`flywheel replay run --harness protocol-review` runs two agent calls in the same working copy.

1. **Work.** The task plus a working method: read the repository's own instructions and the code
   and tests around the change; list every concrete requirement and use the task's exact words
   verbatim; write the tests the task says were added; run the touched tests and the whole suite;
   reread the task against `git diff` before finishing.
2. **Review and repair.** A fresh call, same model, gets the task again, reads `git diff`, checks
   each requirement, runs the tests and fixes any gap. It changes nothing if all is right.

Neither call sees the hidden tests or the real change. The prompts are `PROTOCOL_PROMPT` and
`REVIEW_PROMPT` in `src/flywheel/replay.py`.

## The fresh held-out set

| Step | Count |
| --- | ---: |
| Commits since January that change code and tests together, 500 lines or fewer, in repositories never used in Replay | 126 |
| Fair: the real tests fail before and pass after, twice each, and not for a missing name | 52 |
| Kept by a blind review (two Opus reviewers, the same rule as 13 November, never saw an agent result) | 30 |

The 30 come from Shu (17), ChangeLens (11), the ERP data platform (1) and Studbook (1). Every
verdict and its reason is in `studies/replay/fresh-2026-11-17/task-review.json`; the brief the
reviewers got is `REVIEW-BRIEF.md`. The set and the setup were committed before the first held-out
run (`PLAN.md`), and nothing changed after it started.

## Held-out results (30 cases, one run each, scored once)

| Setup | Passed | Pass rate (95% interval) | Mean tokens | Mean seconds |
| --- | ---: | --- | ---: | ---: |
| Sonnet, plain task | 28 of 30 | 93% (79% to 98%) | 535,196 | 117 |
| Sonnet, working method and review | 28 of 30 | 93% (79% to 98%) | 715,030 | 268 |
| Opus, working method and review | 26 of 30 | 87% (70% to 95%) | 1,075,567 | 311 |

Plain Sonnet was added after the two planned arms finished, as a control: its setup is the
original one and was never changed, so it could not be tuned to this set. Plain Opus was not run.

The misses: one ChangeLens change missed by all three setups, two more each missed by one setup
(Opus, and plain Sonnet), and three Shu runs that hit the 15-minute limit with the working method
(two Opus, one Sonnet). No run was
flagged for reaching outside its copy and none crashed.

## The same setup on the earlier cases

The 55 cases of the 13 November study are now development data. 48 of them still exist in the
local history; 42 were scored with Opus and the new setup (three hit the usage limit, three
were flagged).

| Setup, same 42 cases | Scored runs | Passed | Pass rate |
| --- | ---: | ---: | ---: |
| Opus, working method and review (1 run each) | 42 | 38 | 90% |
| Opus, plain task (13 November, 3 runs each) | 121 | 109 | 90% |
| Sonnet, plain task (13 November, 3 runs each) | 124 | 106 | 85% |

Same number either way. Three of the four misses are cases every setup has always failed, where
the tests check something the task does not say (a label's exact text, a lookup by an unstated
name).

## Why the fresh set scores higher

- **Task text.** The median commit message is 628 characters here against 272 in the earlier set.
  These repositories write commit messages that name the behaviour, the field and the edge case.
- **Kind of change.** All 30 are Python service changes. On 13 November the website cases were
  the weak spot (Opus 21 of 27 held out) and the service cases the strong one (Opus 26 of 28).
  This set has no website cases, so it says nothing new about website work.

## A scoring rule made stricter

Until now a run that hit the time limit was treated like a crash and re-run. It now counts as a
failure and is never re-run (`crashed()` in `replay.py`): the agent did get to work and ran out of
time. No earlier run had timed out, so no earlier number changes.

## Limits

- 30 cases with one run each; the intervals are wide.
- Five repositories, all Python services, all written by one owner.
- The task is the original commit message, which in these repositories is detailed.

## Reproduce

```
source studies/replay/fresh-env.sh   # test environments, built outside the repositories
flywheel replay run --spec studies/replay/fresh-repos.json \
  --cases studies/replay/fresh-2026-11-17/cases-heldout.json --models opus,sonnet --reps 1 \
  --clean-settings --harness protocol-review --setup protocol-review --out runs/
flywheel replay run ... --models sonnet --out runs/          # the plain control
flywheel replay report runs/
```

Every run's record is in `studies/replay/fresh-2026-11-17/runs-heldout/` and `dev/runs-opus-pr/`.
All runs used the Claude subscription; no API credit was spent.
