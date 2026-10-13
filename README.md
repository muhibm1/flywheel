# Flywheel

**Flywheel turns an AI agent's real failures into tests, then checks every code change against
those tests before it ships.**

An agent built on a language model can pass every unit test and still get worse. The tests run
on a scripted stand-in for the model, while the real model reads the prompt and behaves
differently. Flywheel closes that gap in three steps:

1. **Mine.** It reads the agent's recorded runs in LangSmith (LangChain's tracing and
   evaluation service). It finds the runs that went wrong and groups them by where they went
   wrong. Each one becomes a proposed test case.
2. **Review.** A person confirms what the right answer was. The case joins a test file that
   lives in the repository, next to the code.
3. **Gate.** On every pull request, Flywheel runs the cases on the change and on the main
   branch. It compares them case by case and posts the result as a comment. If a case that
   used to pass now fails, the check fails.

The comment reads like this: *"Flywheel ran the agent on 7 test cases, 3 times each, before and
after this change. 2 cases that passed before now fail."* Each broken case links to its trace.

## The result that shows why it matters

AgentOps is an incident-response agent I built on LangGraph. Its suite of about 1,000 tests
runs on a scripted model. In this experiment I wired Flywheel into it.

- **Traffic.** On 2026-10-13 I sent 11 realistic incidents through AgentOps on Claude Haiku 4.5
  and traced them to LangSmith. Each was a known scenario, with its symptoms worded the way
  real alerts arrive: "orders error budget exhausted", or a support ticket relayed by a person.
- **Mining.** Flywheel scored the traces with AgentOps's own evaluators and found 2 failures.
  Both were the same scenario: two faults at once. The terse wording led the agent to give up
  and hand the incident to a person, when it should have fixed one fault and then the other.
  Both became test cases, so the dataset grew from 5 hand-written cases to 7.
- **The change.** I then made the kind of edit that passes code review. I shortened the
  root-cause prompt by deleting one paragraph that looked redundant. Every behavioural unit
  test still passed: 996 passed. The only 2 failures were tests that pin the prompt's exact
  wording, which a cleanup edits along with the prompt.
- **The gate.** Flywheel ran all 7 cases 3 times on Claude Sonnet 5.5, on main and on the
  change. **It blocked the change.** The two mined cases broke: one went from 2 of 3 runs
  correct to 0 of 3, the other from 3 of 3 to 1 of 3. Correct outcomes overall fell from 19 of
  21 runs to 14 of 21.
- **The lesson.** The hand-written version of the same scenario only *wobbled*, from 2 of 3
  to 1 of 3. That is within the noise allowance, so on its own it would not have blocked.
  **The cases that caught the regression came from traffic, not from imagination.**

A control run makes the result credible. I ran main against itself: same code, two separate
live experiments. Flywheel passed it with one case wobbling inside the allowance. So a red
check means a real change, not model noise. Reports and raw results:
[docs/results/agentops-2026-10-13.md](docs/results/agentops-2026-10-13.md).

## A second agent: the same result, a different kind of agent

The [Studbook agent](https://github.com/muhibm1/studbook-agent) answers questions about my
projects' design records, with citations, and refuses when the records do not say. It shares no
code with AgentOps. Flywheel ran it unchanged, with three new checks: did it cite the right
section, did it refuse exactly when it should, and did a model judge the answer correct.

On 36 questions, 3 runs each, on Claude Haiku 4.5, the agent's weak spot was questions that need
two records together. I added a prompt paragraph on comparing records. The averages barely
moved: correct answers fell from 95 to 91 of 108 runs, which reads as noise. The per-case view
did not: the paragraph fixed 3 questions and broke 5, and one of the broken ones was an
unanswerable question the agent started answering with an invented fact. Flywheel blocked it.
[Report](https://github.com/muhibm1/studbook-agent/blob/main/docs/results/comparison-prompt-2026-10-13.md).

## How it decides

The question a reviewer asks is "which cases did this break?", not "did the average move?". An
average hides one case going from always passing to always failing behind two that improved.
So Flywheel decides per case:

| Term | Meaning |
|---|---|
| Pass rate | The share of a case's repetitions that passed a check, such as 2 of 3. |
| Broken | The pass rate fell by at least half. With 3 repetitions, at least two runs flipped from pass to fail. |
| Fixed | The pass rate rose by as much. |
| Wobble | A smaller move. Reported, never blocking: one run in three flipping is what a live model's noise looks like. |
| New | A case added by the pull request. A failing new case is reported, not blocked, because adding a test for a known bug is how the bug gets fixed. |

The gate fails when a case breaks, or when a case starts raising an error it did not raise
before. The report also gives a sign test: the chance that a split this uneven between broken
and fixed cases would appear if the change did nothing.

On the base branch, the pull request's own test cases are run against the base code. So a fix
that arrives with its regression test shows up as *fixed*, not *new*.

## LangSmith, used end to end

| LangSmith feature | What Flywheel does with it |
|---|---|
| Tracing projects | `flywheel mine` reads root runs, feedback and LangGraph node metadata (`langgraph_node`, `langgraph_step`). It names the node where each failing run went wrong. |
| Feedback | `flywheel score` writes evaluator scores onto existing traces. It works like an online evaluator, using the same functions the tests use. |
| Annotation queues | `flywheel mine --queue` puts failing runs in front of a reviewer. |
| Datasets and version tags | `flywheel sync` mirrors the repository's test file into a dataset. It tags each version with the file's content hash, so an experiment records exactly which cases it ran. |
| Experiments (`evaluate`) | `flywheel run --backend langsmith` runs the agent through `Client.evaluate` with repetitions. Every run becomes a trace with its scores attached. |
| Comparison view | The pull-request comment links both experiments side by side. |

Evaluators use LangSmith's own signature, `(inputs, outputs, reference_outputs)`. So the same
function grades a run in CI, a LangSmith experiment, and a production trace.

## Use it

```bash
pip install "langsmith-flywheel[langsmith] @ git+https://github.com/muhibm1/flywheel@7b1730e8463224a624c5ddb20c387d6ad31544cd"
```

Write `flywheel.toml` next to your agent:

```toml
[flywheel]
target = "my_adapter:target"            # inputs dict in, outputs dict out
evaluators = ["my_adapter:correct_team"] # (inputs, outputs, reference_outputs) -> bool | score
dataset = "dataset.jsonl"                # the cases, versioned with the code
repetitions = 3
langsmith_dataset = "my-agent-regressions"

[gate]
max_broken = 0      # how many broken cases to tolerate
min_change = 0.5    # how far a pass rate must move to count

[mine]
project = "my-agent-prod"
rules = [{ key = "correct_team", below = 1 }]
```

Then:

```bash
flywheel score --project my-agent-prod --since 1d       # grade yesterday's traces
flywheel mine --since 1d --queue my-agent-review        # propose the failures as cases
flywheel promote .flywheel/candidates.jsonl             # add the reviewed ones
flywheel run --label base --out base.json               # on main
flywheel run --label head --out head.json               # on your branch
flywheel gate --base base.json --head head.json         # exit 1 when blocked
```

Add the gate to a repository's pull requests:

```yaml
permissions:
  contents: read
  pull-requests: write
jobs:
  gate:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - uses: muhibm1/flywheel@7b1730e8463224a624c5ddb20c387d6ad31544cd # v0.1.0
        with:
          config: flywheel/flywheel.toml
          install: python -m pip install -e .
```

Use a scripted or recorded model in CI where the agent has one: it is free and deterministic.
Run prompt and model changes against a live model with `--backend langsmith`, because a scripted
model cannot see them.

## Try it in a minute

The quickstart is a tiny message router that needs nothing installed. Its "regression" drops
the refund rule, the kind of tidy-up that reads fine in review.

```bash
cd examples/quickstart
flywheel run --label base --out /tmp/base.json
QUICKSTART_REGRESSION=1 flywheel run --label head --out /tmp/head.json
flywheel gate --base /tmp/base.json --head /tmp/head.json   # blocked: the refund case broke
```

## What is in the repository

| Path | What it is |
|---|---|
| `src/flywheel/gate.py` | The per-case comparison, the noise allowance and the decision |
| `src/flywheel/mine.py` | Failure detection, signatures (reason at node) and candidate cases |
| `src/flywheel/langsmith_backend.py` | Traces, feedback, datasets, experiments and annotation queues |
| `src/flywheel/report.py` | The pull-request comment |
| `action.yml` | The GitHub Action |
| `docs/playbook.md` | The first two weeks with a customer's agent, step by step |
| `examples/quickstart/` | The dependency-free demo |

The core needs only the Python standard library; LangSmith is an optional extra. Tests:
`pip install -e ".[dev,langsmith]" && pytest`.

## Limits, stated plainly

- Mining finds failures that a score or an error can see. A wrong answer that every evaluator
  passes stays invisible, so the evaluators deserve as much review as the agent.
- Three repetitions tell a real break from noise only for large moves. A case that goes from
  3 of 3 to 2 of 3 is reported as a wobble, not blocked. Raise `repetitions` for cases where a
  single failure matters.
- Each result above is one change on one agent: 7 or 36 cases, 3 repetitions, one model. It shows
  the mechanism working. It is not a benchmark.

MIT licensed.
