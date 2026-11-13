# Replay pilot, 2026-11-12: can an agent redo a real past change?

In plain words: Flywheel now has a second mode, `flywheel replay`. It takes a change that really
shipped in one of my repositories, rewinds the repository to the moment just before it, and asks
an agent to do the same task with no access to the later history. The tests that came with the
real change then decide pass or fail. This pilot ran 20 such changes on three models, one run each.

**Result:** Haiku passed 14 of 20 (70%), Sonnet 16 of 20 (80%), Opus 16 of 20 (80%). With 20 cases and
one run each, those three numbers are not clearly different from each other; the intervals overlap
almost entirely. Nothing here reaches 90%. What does stand out is cost: Sonnet matched Opus while
using about 45% fewer tokens and finishing in about 40% less time, and Haiku used the most tokens
because it took more steps.

## What was run

| Step | Count |
| --- | ---: |
| Real changes found (code and tests changed together, 500 lines or fewer) | 136 |
| Of those, fair: the real tests fail before the change and pass after it, twice each | 64 |
| Reviewed blind by a separate Opus agent for answer leaks and missing detail | 64 |
| Kept: the task text says enough for a correct solution to pass | 20 |
| Replayed: 3 models, 1 run each | 60 runs |

Repositories: AgentOps (16 cases) and WorkHorse (4 cases). ChangeLens contributed none: 36 of its
changes failed the fairness check, mostly because its tests did not pass reliably in my setup
across history, and the one fair case was judged under-specified.

A change is fair only if its tests fail before the change for a reason a person could fix from the
task. Of the 72 changes that were not fair, 36 were dropped because the tests need a name or option
the task never mentions, 35 because the tests did not pass after the real change (changed
dependencies or flaky tests), and 1 because the tests already passed before it. The Opus reviewer saw the task text, the real change and its tests,
and never any agent result. Its verdicts, one sentence each, are in
`studies/replay/pilot-2026-11-12/task-review.json`. Of the 64 fair cases it kept 20, marked 38
under-specified, 6 odd (not a code task) and found 0 that leaked the answer.

## Results

| Model | Scored runs | Passed | Pass rate (95% interval) | Mean tokens | Mean seconds | Flagged and left out |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| haiku | 20 | 14 | 70% (48% to 85%) | 1,246,033 | 126 | 0 |
| opus | 20 | 16 | 80% (58% to 92%) | 898,398 | 111 | 0 |
| sonnet | 20 | 16 | 80% (58% to 92%) | 484,266 | 78 | 0 |

| Case | haiku | opus | sonnet |
| --- | --- | --- | --- |
| agentops-09f949a336 | 1/1 | 1/1 | 1/1 |
| agentops-11067ac082 | 1/1 | 1/1 | 1/1 |
| agentops-15ff24efab | 1/1 | 1/1 | 1/1 |
| agentops-5290f6908b | 1/1 | 1/1 | 1/1 |
| agentops-58916f28b5 | 1/1 | 1/1 | 1/1 |
| agentops-6ec50db482 | 0/1 | 0/1 | 0/1 |
| agentops-710be1763e | 1/1 | 1/1 | 1/1 |
| agentops-75b77ef6d7 | 0/1 | 1/1 | 1/1 |
| agentops-7ad570fd6b | 0/1 | 0/1 | 1/1 |
| agentops-7ce4c80580 | 0/1 | 1/1 | 0/1 |
| agentops-aeb5e00f23 | 1/1 | 1/1 | 1/1 |
| agentops-cf21be9ce9 | 1/1 | 1/1 | 1/1 |
| agentops-d9ada42a58 | 1/1 | 1/1 | 1/1 |
| agentops-e717d7e353 | 1/1 | 1/1 | 1/1 |
| agentops-e8229a1bd3 | 1/1 | 1/1 | 1/1 |
| agentops-fb17e59771 | 0/1 | 0/1 | 0/1 |
| workhorse-2c9cd06380 | 0/1 | 0/1 | 0/1 |
| workhorse-32bdf1a25b | 1/1 | 1/1 | 1/1 |
| workhorse-566ef624e1 | 1/1 | 1/1 | 1/1 |
| workhorse-ef43c5ee85 | 1/1 | 1/1 | 1/1 |

Pass rate uses a Wilson 95% interval. Tokens include tokens read back from cache, so they measure
work done, not new text; the medians (tokens, steps, seconds) were Haiku 1.13M, 23, 106 s;
Sonnet 0.45M, 10, 58 s; Opus 0.80M, 16, 101 s. These are subscription runs, so no dollar figure is
given. No run was left out for peeking: the check looks for the source repository's path, git
history commands and network use in every tool call, and found none.

## What this says, and what it does not

- Three cases (agentops-6ec50db482, agentops-fb17e59771, workhorse-2c9cd06380) were failed by all
  three models. They may be under-specified in ways the blind review did not catch. They stay in
  the headline numbers. Without them the rates would be 14 of 17 for Sonnet and Opus and 11 of 17
  for Haiku, which is a post-hoc view and is not used as the result.
- One run per model per case. A run is noisy: the same model can pass and fail the same case on
  different tries. The next step is three runs per case, so each case gets its own pass rate.
- The tests judge only the real change's own tests. An agent could pass them and break something
  else; the whole repository's suite was not run.
- Task text is the real commit message. A reviewer judged it, but the text still sometimes states
  the fix in prose, which makes the cases easier than a task written from a bug report.
- The cases were chosen after seeing the repositories, not after seeing results, and 20 is
  small. This is a pilot, not a benchmark.

## How to run it

```bash
flywheel replay mine  --spec studies/replay/pilot-repos.json --since 2026-08-01 --out cases.json
flywheel replay check --spec studies/replay/pilot-repos.json --cases cases.json --out fair.json
flywheel replay run   --spec studies/replay/pilot-repos.json --cases fair.json \
  --models haiku,sonnet,opus --reps 3 --out results/
flywheel replay report results/
```

The agent is the `claude` command line, run headless on the signed-in subscription with a limited
tool list: read, search and edit files in the copy, and run tests and read-only commands. No API
key is read. The repository spec names each repository's test command and where its code and tests
live. Raw per-run records are in `studies/replay/pilot-2026-11-12/runs/`.
