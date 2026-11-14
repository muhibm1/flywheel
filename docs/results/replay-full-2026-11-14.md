# Replay, 14 November 2026: 55 real changes, three models, and a finish check

In plain words: each case is a change that really shipped in one of my repositories. The
repository is rewound to just before it, an agent gets the commit message as its task, and the
tests that came with the real change decide pass or fail. This round grew the set from 20 to 55
cases across nine repositories, ran every case three times on each model, and tested one rule: a
hook that will not let the agent finish after editing code until it has run a test, lint or build.

**Result on the 20 held-out cases, scored once:** Opus passed 85%, Sonnet 78%, Haiku 76%. On the
35 tuning cases the order was the same (Opus 88%, Sonnet 82%, Haiku 77%). Sonnet used about half
of Opus's tokens and took about half the time. The finish check made no measurable difference: it
was 9 points behind plain Sonnet on the tuning cases and 4 points ahead on the held-out ones. No
setup reaches 90% overall.

## The cases

| Step | Count |
| --- | ---: |
| New candidate changes (code and tests changed together, 500 lines or fewer, since January) | 128 |
| Fair: the real tests fail before the change and pass after it, twice each, and not for a missing name | 100 |
| Kept by a blind review (three Opus reviewers who never saw an agent's result) | 35 |
| Plus the 20 pilot cases | 20 |
| Total, split by a hash of the case id | 35 tuning, 20 held out |

The review dropped 48 cases whose tests check exact wording, labels or new names the task never
gives, and 17 that are not code changes (copy edits, documents, version bumps). Every verdict, with
its one-sentence reason, is in `studies/replay/full-2026-11-13/task-review.json`. The cases come
from AgentOps, the portfolio site, WorkHorse, Agent Harbor (Lodestar), Garvis, Tannhauser Gate,
Auspex and Flywheel.

What was fixed before anything was scored is in `studies/replay/full-2026-11-13/PLAN.md`, with the
measurement changes made after the tuning runs and why.

## Held-out results (20 cases, 3 runs each, scored once)

| Setup | Scored runs | Passed | Pass rate (95% interval) | Mean tokens | Mean seconds |
| --- | ---: | ---: | --- | ---: | ---: |
| Opus | 55 | 47 | 85% (74% to 92%) | 993,523 | 96 |
| Sonnet with the finish check | 57 | 47 | 82% (71% to 90%) | 599,728 | 65 |
| Sonnet | 60 | 47 | 78% (66% to 87%) | 489,168 | 48 |
| Haiku | 51 | 39 | 76% (63% to 86%) | 1,329,773 | 105 |

## Tuning results (35 cases, 3 runs each)

| Setup | Scored runs | Passed | Pass rate (95% interval) | Mean tokens | Mean seconds |
| --- | ---: | ---: | --- | ---: | ---: |
| Opus | 100 | 88 | 88% (80% to 93%) | 927,016 | 105 |
| Sonnet | 101 | 83 | 82% (74% to 88%) | 506,626 | 64 |
| Haiku | 99 | 76 | 77% (68% to 84%) | 1,240,192 | 102 |
| Sonnet with the finish check | 105 | 77 | 73% (64% to 81%) | 559,403 | 56 |

## By kind of change

| Setup | Website, tuning | Website, held out | Services, tuning | Services, held out |
| --- | ---: | ---: | ---: | ---: |
| Opus | 33 of 34 | 21 of 27 | 55 of 66 | 26 of 28 |
| Sonnet | 30 of 36 | 20 of 27 | 53 of 65 | 27 of 33 |
| Sonnet with the finish check | 30 of 36 | 20 of 27 | 47 of 69 | 27 of 30 |
| Haiku | 28 of 34 | 16 of 25 | 48 of 65 | 23 of 26 |

On the tuning cases Opus looked nearly perfect on the website (33 of 34). The held-out cases did
not bear that out (21 of 27, 78%), so it is not a reason to pick Opus for website work. Where the
held-out cases favour Opus is the Python and Node services (26 of 28, 93%).

## Runs left out

A run is left out when the agent reached outside its copy: it looked into the original repository
(several agents looked for a ready Python environment in `/home/user/lodestar`), or ran a history
or network command (`git stash`, for example). Between 0 and 9 runs per setup were left out this
way; the tables count only the rest. A first version of this rule also flagged text the agent
wrote into a file through a heredoc script (a link on a page, a runbook that mentions `curl`).
Those runs did nothing outside their copy, so they are scored, and the rule now ignores heredoc
bodies. Runs whose agent crashed on the subscription's usage limit were re-run and never counted.

## The finish check made no measurable difference

The hook blocked Sonnet's first attempt to finish in about a third of tuning runs; Sonnet then ran
the tests. On the tuning cases Sonnet with the hook passed 73% against 82% without it; on the
held-out cases 82% against 78%. The two results point in opposite directions and every interval
overlaps, so the honest reading is no effect either way. Blocked runs on the tuning cases passed at
the same rate as runs the hook left alone.

The decision this supports: the hook is not worth installing for this kind of work. One reason it
has little to catch: the task prompt already tells the agent to run the tests. It might still
matter in live sessions where nobody says so; that would need measuring on live sessions.

## What this changes in practice

- Sonnet is the default for routine changes: 6 to 7 points behind Opus, at about half the tokens and
  half the time.
- Opus is worth it for harder service changes, where it passed 26 of 28 held-out runs.
- Haiku is not cheaper here: it used the most tokens of the three because it takes more steps.

## Limits

- 20 held-out cases is a small number; the intervals are wide.
- The task text is the original commit message, which is often more detailed than a real request.
- Tests judge only what the real change's tests check. A run can pass while doing something else
  wrong, or fail on a detail a person would accept.

## Reproduce

```
flywheel replay check --spec studies/replay/full-repos.json --cases <candidates.json> --out fair.json
flywheel replay run --spec studies/replay/full-repos.json \
  --cases studies/replay/full-2026-11-13/cases-tune.json --models haiku,sonnet,opus --reps 3 \
  --clean-settings --out runs/
flywheel finish-check --settings > finish-check.json   # the hook, for the fourth setup
flywheel replay run ... --models sonnet --settings finish-check.json --setup finish-check
flywheel replay report runs/
```

Every run's record is in `studies/replay/full-2026-11-13/runs-tune/` and `runs-heldout/`. The 25
runs made with the first version of the hook, which could not see edits made from the shell, are
set aside in `runs-set-aside-first-hook/` and were not counted.
