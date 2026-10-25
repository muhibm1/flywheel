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

### A pull request cannot grade itself

Each side is graded by its own checkout. So a pull request could turn a failure into a pass
without touching the agent: loosen an evaluator, rewrite a case's expected answer, delete the
case, or raise `max_broken`. When agents write the pull requests, that is an easy shortcut to
take by accident. Flywheel lists every such edit in the report and blocks until a person
approves it, with the `flywheel-grading-approved` label or `flywheel gate --approve-grading`.

| Edit | How it is found |
|---|---|
| Evaluator code changed | `flywheel run` records a hash of each evaluator's module; the two sides differ. A helper the evaluator imports from another module is not covered. |
| Evaluator removed | It is in the base branch's `flywheel.toml` and not in the pull request's. |
| Gate setting changed | Any change to `[gate]`, in either direction. |
| Expected answer changed | A case in both datasets has different `reference_outputs`. |
| Case removed | A case in the base branch's dataset is gone. |

Adding cases or evaluators is not listed: it can only make the gate stricter.

### More runs only where they change the answer

Three runs a side settle a case that went from 3 of 3 to 0 of 3. They cannot settle one that
went from 3 of 3 to 1 of 3: the next three runs might call it noise. Running every case six
times settles both and doubles the bill. With `close_call_repetitions = 3` in `[gate]`, Flywheel
runs everything three times, finds the **close calls** (cases whose move is within one run of
the threshold), and runs only those again on both sides. `flywheel close-calls` lists them,
with the number to start the extra runs from (`flywheel run --first-repetition`), so a
recorded answer from the first runs is never replayed as a new one.

Replayed on the LangChain email study's four six-run experiments (12 pairings, no new model
calls), close calls reached the six-run decision and the same broken cases in all 12, with 34%
fewer runs. Three runs alone matched in 7 of 12. The script is
[studies/langchain-agents/close_calls_check.py](studies/langchain-agents/close_calls_check.py).
The check is fair in one direction only: close-call cases reuse the very runs the six-run
answer used, so what it shows is that the cases Flywheel skipped would not have changed the
decision.

### Main's result is stored, not rerun

Every pull request used to run the agent twice, once on main. Main's half is the same work each
time. The Action now stores the base branch's result, keyed by the base commit, the files in the
config's folder, the backend and the repetitions, and reuses it. Run the Action on `push` to
main too, and pull requests start with main's result already stored. A live gate costs half as
many model calls; `flywheel gate --base a.json b.json` still pools several runs of main when one
is not enough.

### What a run costs

An agent can keep passing while it gets more expensive: a longer prompt, an extra model call,
or a date placed early in the prompt that stops the cache from working. When the agent counts
its calls with `flywheel.spend` (below), each run keeps its calls' tokens, cache reads and, for
paid calls, list-price dollars. The report then adds a cost table, before and after, for an
average run of the cases both sides ran. Three settings in `[gate]` turn it into a check, each
off unless set:

| Setting | Blocks when |
|---|---|
| `max_cost_increase = 0.25` | A run's list-price dollars rose by more than 25%. Only runs whose every call was priced count. |
| `max_token_increase = 0.25` | A run's tokens, prompt and output, rose by more than 25%. This works for runs on a subscription too. |
| `max_cache_drop = 0.2` | The share of the prompt read from the cache fell by more than 20 points. |

Replayed calls keep the usage they were recorded with, so a replayed base compares fairly with
a live pull request. Like any other `[gate]` edit, changing these settings needs a person's
approval.

## Paid calls: a cap, a ledger and replay

`flywheel.spend` is a small module for the paid model calls themselves, and it needs only the
standard library. A call goes through it in this order:

1. **Replay.** Each call is keyed by a hash of its exact request, leaving out cache markers. A
   call recorded before is answered from the recording and costs nothing. A request sent
   several times, as an agent run three times sends its first request, keeps one recording per
   use, so the repeats keep their spread; in `flywheel run`, each repetition replays its own.
   With `FLYWHEEL_REPLAY=replay`, a call that was never recorded raises instead of going live,
   so a frozen CI run cannot start spending.
2. **The guard.** A live call needs a dollar cap. With no `FLYWHEEL_API_CAP` set, paid calls
   are off. Once the ledger's total reaches the cap, every later call is refused, in this run
   and the next.
3. **The ledger.** Every call is appended to `.flywheel/api-ledger.jsonl`: model, uncached
   input, cache writes, cache reads, output, list price and what was actually billed.

A refused call or a replay miss ends `flywheel run` with exit 1 and one line naming the cause,
and no experiment file is written. Every later call would stop the same way, and a file of
errored runs would read to the gate as a regression.

```python
from flywheel import spend

guard = spend.Guard.from_env(project="my-agent")  # FLYWHEEL_API_CAP, FLYWHEEL_API_LEDGER
recorder = spend.Recorder.from_env()  # FLYWHEEL_REPLAY=record, replay or off


def ask(body):  # a Messages API request body
    return spend.call(body, send_to_anthropic, guard=guard, recorder=recorder)
```

A LangChain chat model gets the same order through LangChain's own cache slot, with the
`langchain` extra installed:

```python
from flywheel.langchain_spend import guard_model

model = guard_model(ChatAnthropic(model="claude-haiku-5-5"), guard, recorder, label="triage")
```

LangChain asks a model's cache before it sends any call, so a refusal or a replay miss is raised
before anything leaves. It does not ask when a model streams, so `guard_model` also turns
streaming off: `stream()` then waits for the whole answer. The key leaves out message ids,
the token usage on earlier answers, cache markers and transport settings such as the endpoint,
timeout and retry count. Usage is left out because LangChain zeroes the cost on an answer it
replays, and an agent loop sends that answer back in its next request. A prompt that carries
something new on every run, such as a random marker around untrusted text, can pass
`normalize=` to blank it in the key, so the rerun still replays.

Code that makes its own calls can count them with `guard.record(model, usage)`. Calls answered
through a Claude subscription are counted with `spend.note(model, usage, "subscription")`: they
keep their tokens and are never priced. `flywheel spend` totals one or more ledgers by day,
model and project, with what replay saved:

```bash
flywheel spend .flywheel/api-ledger.jsonl
```

`flywheel run` also sends its first case alone before it runs the rest in parallel. A cache
entry can be read only once its first answer has started, so cases started together would each
pay to write the same shared prompt prefix.

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
pip install "langsmith-flywheel[langsmith] @ git+https://github.com/muhibm1/flywheel@3fe3668707673b40a9219265c71af8f9669b1665"
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
close_call_repetitions = 3  # extra runs, on both sides, for cases near the threshold (0: off)
min_change = 0.5    # how far a pass rate must move to count
max_cache_drop = 0.2        # block a 20-point fall in the share of the prompt read from cache

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

Add the gate to a repository's pull requests. The `push` trigger stores main's result for
pull requests to reuse; `labeled` re-runs the gate when a person adds
`flywheel-grading-approved`:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    types: [opened, synchronize, reopened, labeled]
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
      - uses: muhibm1/flywheel@3fe3668707673b40a9219265c71af8f9669b1665 # main, 2026-10-24
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
| `src/flywheel/gate.py` | The per-case comparison, the noise allowance, close calls and the decision |
| `src/flywheel/grading.py` | Edits a pull request makes to its own checks |
| `src/flywheel/mine.py` | Failure detection, signatures (reason at node) and candidate cases |
| `src/flywheel/langsmith_backend.py` | Traces, feedback, datasets, experiments and annotation queues |
| `src/flywheel/report.py` | The pull-request comment |
| `src/flywheel/spend.py` | Prices, the budget guard and its ledger, record and replay, the per-run meter |
| `src/flywheel/langchain_spend.py` | The same guard and replay for a LangChain chat model, through its cache slot |
| `action.yml` | The GitHub Action |
| `docs/playbook.md` | The first two weeks with a customer's agent, step by step |
| `examples/quickstart/` | The dependency-free demo |

The core needs only the Python standard library; LangSmith and LangChain are optional extras.
Tests: `pip install -e ".[dev,langsmith,langchain]" && pytest`.

## Limits, stated plainly

- Mining finds failures that a score or an error can see. A wrong answer that every evaluator
  passes stays invisible, so the evaluators deserve as much review as the agent.
- Three repetitions tell a real break from noise only for large moves. A case that goes from
  3 of 3 to 2 of 3 is reported as a wobble, not blocked. Raise `repetitions` for cases where a
  single failure matters.
- Each result above is one change on one agent: 7 or 36 cases, 3 repetitions, one model. It shows
  the mechanism working. It is not a benchmark.
- The cost table sees only the calls an agent reports to `flywheel.spend`, and only on the local
  backend for now. Prices are Anthropic's list prices, kept by hand in `PRICES`.

MIT licensed.
