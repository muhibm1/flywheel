# Flywheel on two of LangChain's open-source agents

**Question:** a customer runs one of LangChain's published agents and asks the question every
team asks: *can we move it to the cheaper model?* Flywheel's job is to answer that before the
change ships, case by case, and to say when it cannot tell.

This study ran Flywheel on two agents LangChain publishes, unchanged except for the model:

| Agent | Source | What it does |
|---|---|---|
| Email assistant | `langchain-ai/agents-from-scratch` | Sorts an email into ignore, notify or respond, then drafts replies and books meetings with tools. |
| Text-to-SQL Deep Agent | `langchain-ai/deepagents`, `examples/text-to-sql-agent` | Answers questions about a music store's database by exploring tables and writing SQL. |

The change under test moves every model call from Claude Sonnet 4.5 to Claude Haiku 4.5, about a
third of the price per token. Each gate has a **control**: main against a second run of main,
where nothing changed. The plan, cases and decision rules were written down before any result
([PLAN.md](PLAN.md)), and every run is kept in `*/runs/`.

## Results

### Text-to-SQL agent: 36 questions, 3 runs each

| | Sonnet 4.5 (main) | Sonnet 4.5 (control) | Haiku 4.5 (change) |
|---|---|---|---|
| Correct answer | 107 / 108 (99%) | 106 / 108 (98%) | 105 / 108 (97%) |
| Only read the database | 108 / 108 | 108 / 108 | 108 / 108 |

- **Flywheel's verdict on the move to Haiku: pass.** No case broke; two cases slipped from 3 of 3
  to 2 of 3, which Flywheel reports as noise and does not block on.
- **The control also passes**, so a green check here means something.
- The answers are checked by code, not by a model: each one must contain the values a
  hand-written SQL query returns from the same database.
- 24 questions were written first (6 easy, 8 medium, 10 hard). Sonnet got all 72 runs right,
  so the set was too easy to tell the models apart. 12 harder questions were added (NULL
  handling, stated tie-breaks, date arithmetic, a window function, "every one of" queries) and
  checked against the database before any agent saw them. The agent still got almost all of
  them right: this agent on Claude is genuinely strong on this database.

### Email assistant: 20 cases, 6 runs each

The 20 cases are LangChain's own 16 labelled emails plus 4 that Flywheel mined from traffic
(below). They are scored by LangChain's own three checks from the repository's tests. The plan
said 3 runs per case; at 3 runs the control blocked (below), so every side was run 3 more times
and both gates were run again at 6. Both rounds are reported.

| | Sonnet 4.5 (main) | Sonnet 4.5 (control) | Haiku 4.5 (change) |
|---|---|---|---|
| Sorted into the right category | 99 / 120 (83%) | 101 / 120 (84%) | 105 / 120 (88%) |
| Called every expected tool (reply emails) | 36 / 66 (55%) | 34 / 66 (52%) | 30 / 66 (45%) |
| Reply met LangChain's criteria (model judge) | 32 / 66 (48%) | 33 / 66 (50%) | 27 / 66 (41%) |

- **Flywheel's verdict on the move to Haiku: blocked**, on one case, at 3 runs and again at 6. A
  new colleague asks for a 30-minute chat; LangChain's criteria say the agent must check the
  calendar before proposing times. Main did so in 4 of 6 runs, Haiku in 0 of 6: it wrote back
  with times it never checked.
- **But the control blocked on the same case, at 3 runs and at 6.** A second run of unchanged
  Sonnet checked the calendar in 0 of 6 runs. Across both Sonnet runs it checked in 4 of 12, so
  this email is a coin toss that lands badly about two times in three, whichever model runs it.
  The main run happened to land well, and Flywheel compares each case against that one run. So
  this block is not evidence against Haiku, and more runs alone did not cure it.
- **What does point at Haiku is spread thin.** Haiku called the expected tools in 30 of 66 reply
  runs against 34 to 36 for Sonnet, and met the criteria in 27 against 32 to 33. No single case
  moved enough to count as broken. Haiku sorted emails slightly better (105 of 120).
- **The real finding about the agent is the skipped calendar check.** On meeting requests it
  often proposes times without looking at the calendar, which a user would only notice when
  they are double-booked. Flywheel surfaced it from traffic, not from LangChain's own cases.
- The email agent is hard for every model on reply quality: about half of the replies meet
  LangChain's written criteria. The criteria are strict (exact tools, exact content).
- At 3 runs the numbers were: triage 51, 49 and 53 of 60; tools 18, 17 and 15 of 33; criteria
  17, 18 and 14 of 33 (main, control, Haiku). Reports: `email/runs/gate-*.md` (3 runs) and
  `email/runs/gate-*-x6.md` (6 runs).

### Mining: real failures become tests

29 new, realistic emails were labelled from the agent's own triage rules, before any run, and
sent through the agent once each, like a day of mail. Flywheel scored them with the same three
checks and found 4 failures in 3 places:

| Failures | Where it went wrong |
|---:|---|
| 2 | The reply agent skipped an expected tool (the calendar check). |
| 1 | The reply missed its criteria. |
| 1 | Triage answered a CI-failure notice that should only have been flagged. |

All 4 became test cases, growing the dataset from 16 to 20. The mined calendar case is the one
that later decided both email gates.

### What Flywheel caught that was not the agent

Mid-study the subscription's usage limit ran out partway through a control run. Flywheel blocked
that run: 12 cases broken and 16 raising errors they did not raise before. The run was thrown
out and redone, and the blocked report is kept
(`email/runs/v1-transport/gate-control-limit-hit.md`). This is the gate doing its job on a
broken run.

## What was fixed along the way

- **A bug in Flywheel's own gate.** A check that only applies to some cases (the reply checks
  only apply to reply emails) was counted as a failure on every other case, so totals read
  14 of 60 instead of 14 of 33. Fixed in `src/flywheel/gate.py`, with a test.
- **Two grader bugs in this study's SQL check**, both found by reading failed answers: "138.6"
  did not match "138.60", and a read-only schema lookup (`PRAGMA table_info`) was flagged as a
  write. Both fixed and tested, then every SQL run was rescored.

## How it ran, and what it cost

- **API cost: $0.** Every run used the Claude subscription through headless the harness,
  wrapped as a LangChain chat model (`subchat.py`). The agents' graphs, prompts and tools are
  unchanged; only the model transport differs.
- **That transport is a disclosed difference.** The model does not get native tool calls; it
  returns its tool calls as JSON. In early runs it sometimes told the user "the SQL tools are not
  available" instead of calling them. Clearer framing cut this from 3 runs in 8 to about 1 run
  in 100 (0 of 108 Sonnet main runs, 1 of 108 Haiku runs, 2 of 108 control runs). Those runs count
  as failures above; they were not dropped.
- **The email judge** is Claude Sonnet 4.6 on the subscription, the same for every run, using
  LangChain's own judge prompt.
- **LangSmith's free monthly trace limit was used up**, so the traffic traces were exported to a
  file and mined with `flywheel mine --from-file` rather than read from LangSmith.
- Usage limits cut some runs short. `assemble.py` rebuilds a run from its saved answers and the
  remaining cases were run separately; each case keeps its first 3 answers (or 6).

## Gaps

- **The email control false-blocks, at 3 runs and at 6.** The cause is one case that passes
  about a third of the time: compared against a single main run, two runs of the same model can
  land 4 of 6 and 0 of 6. More runs did not fix it. The fix belongs in Flywheel: compare each
  case against the main branch's pooled history, or use a per-case statistical test, instead of
  a single main run. Until then, a block on a case like this one needs a person to read it.
- **Native API parity is not yet checked.** A small paid run of the Haiku side on LangChain's own
  `ChatAnthropic` client would show whether the subscription route gives the same verdicts.
  It is ready (`apiguard.py` enforces a hard spending cap) but has not run.
- **The SQL set does not separate the models.** Both are near-perfect; a harder database or
  multi-step questions would be needed to see a gap.
- The email assistant ships on OpenAI's gpt-4.1; it was not run on that model here.
- One author wrote the traffic labels and the harder SQL questions. They were fixed before any
  run, but no second person checked them.

## Reproduce

Each agent folder has `run.sh LABEL MODEL`, a `flywheel.toml`, and the adapter that wires the
agent to Flywheel. Then:

```
flywheel gate --base runs/<main>.json --head runs/<change>.json --report runs/gate.md
python ../summarize.py runs/<label>.json runs/dataset-v2.jsonl
```
