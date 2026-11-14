# Replay, 14 November 2026: 55 real changes, three models, and a finish check

In plain words: each case is a change that really shipped in one of my repositories. The
repository is rewound to just before it, an agent gets the commit message as its task, and the
tests that came with the real change decide pass or fail. This round grew the set from 20 to 55
cases across nine repositories, ran every case three times on each model, and tested one rule: a
hook that will not let the agent finish after editing code until it has run a test, lint or build.

**Result on the 35 tuning cases:** Opus passed 88%, Sonnet 83%, Haiku 77%. Sonnet used about half
of Opus's tokens and finished about 40% faster. The finish check did not help: Sonnet
passed 76% with it and 83% without, a gap inside run-to-run variation. None of the three models reaches 90% overall; Opus reaches 97% on
the website's changes (33 of 34). The 20 held-out cases are scored once, separately, in the section
at the end.

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
its one-sentence reason, is in `studies/replay/full-2026-11-13/task-review.json`. Nine
repositories are represented: AgentOps, the portfolio site, WorkHorse, Agent Harbor (Lodestar),
Garvis, Tannhauser Gate, Auspex and Flywheel.

What was fixed before anything was scored is in `studies/replay/full-2026-11-13/PLAN.md`, with the
two measurement changes made after the tuning runs and why.

## Results on the tuning set (35 cases, 3 runs each)

| Setup | Scored runs | Passed | Pass rate (95% interval) | Mean tokens | Mean seconds |
| --- | ---: | ---: | --- | ---: | ---: |
| Opus | 100 | 88 | 88% (80% to 93%) | 927,016 | 105 |
| Sonnet | 100 | 83 | 83% (74% to 89%) | 499,334 | 64 |
| Sonnet with the finish check | 99 | 75 | 76% (66% to 83%) | 533,740 | 55 |
| Haiku | 99 | 76 | 77% (68% to 84%) | 1,240,192 | 102 |

5 or 6 runs per setup were left out because the agent touched the source repository or a network
or history command (some of these were harmless, such as `git remote -v` in a copy with no
history; the rule was narrowed afterwards, and the held-out runs use the narrower rule). Runs whose
agent crashed on the subscription's usage limit were re-run, never counted.

By kind of change:

| Setup | Website (React) | Python and Node services |
| --- | ---: | ---: |
| Opus | 33 of 34 (97%) | 55 of 66 (83%) |
| Sonnet | 30 of 36 (83%) | 53 of 64 (83%) |
| Sonnet with the finish check | 30 of 36 (83%) | 45 of 63 (71%) |
| Haiku | 28 of 34 (82%) | 48 of 65 (74%) |

## The finish check did not help

The hook blocked Sonnet's first attempt to finish in 34 of 99 runs; Sonnet then ran the tests and
26 of those 34 runs passed (76%). The 65 runs where the hook stayed silent passed at the same rate
(49 of 65, 75%). So being stopped did not make runs fail, and it did not rescue them either. The
drop against plain Sonnet (76% against 83%, intervals overlapping) comes mostly from runs the hook
never touched: 16 of the 24 failures had no block at all. That points to ordinary run-to-run
variation, not harm from the hook. Nine cases did worse with it and two did better.

The decision this supports: the finish check adds nothing measurable on these tasks, so it is not
worth installing. One reason it has little to catch here: the task prompt already tells the agent
to run the tests. It may still matter in live work where
nobody says so; that would need measuring on live sessions, not replays.

## What this changes in practice

- Sonnet is the default for routine changes: within 5 points of Opus at about half the tokens.
- Opus is worth it for website work, where it missed 1 of 34 runs.
- Haiku is not cheaper here: it used the most tokens of the three because it takes more steps.

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

Every run's record is in `studies/replay/full-2026-11-13/runs-tune/`. The 25 runs made with the
first version of the hook, which could not see edits made from the shell, are set aside in
`runs-set-aside-first-hook/` and were not counted.

## Held-out (20 cases, scored once)

Running.
