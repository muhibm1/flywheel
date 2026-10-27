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

- **Against a single main run, Flywheel blocked the move to Haiku, and its control blocked
  too.** Both blocks were on the same case. A new colleague asks for a 30-minute chat, and
  LangChain's criteria say the agent must check the calendar before proposing times. The main
  Sonnet run did so in 4 of 6 runs. A second, unchanged Sonnet run did so in 0 of 6, and so did
  Haiku. Across both Sonnet runs it checked in 4 of 12: this email is a coin toss that usually
  lands badly, whichever model runs it. Comparing against one lucky main run called that noise a
  break. Running 6 times instead of 3 did not cure it.
- **So Flywheel gained a fix: pool several runs of main.** `flywheel gate --base a.json b.json`
  now combines several runs of the main version into one, case by case. The fix was committed
  before it was tested. It was then tested on a third, independent Sonnet run, made only for this
  check, against the first two pooled. **That control passed**: no case broken, 9 small moves.
  The calendar case read 4 of 12 against 1 of 6, a wobble.
- **With the fix, Flywheel still blocks the move to Haiku, on a different case.** A school asks a
  parent to volunteer and to reply by March 7. LangChain's criteria ask for a reply that
  acknowledges the deadline. The pooled Sonnet runs met them in 8 of 12, Haiku in 1 of 6. The
  calendar case is no longer blocking. One caveat, stated so it is not hidden: with all three
  Sonnet runs pooled, Sonnet met that case's criteria in 11 of 18. Against that, Haiku's drop is
  just under Flywheel's threshold. The verdict reported here uses the same setup the fix was
  tested with: the first two Sonnet runs pooled as main.
- **Haiku's other losses are spread thin.** Haiku called the expected tools in 30 of 66 reply
  runs against 34 to 36 for each Sonnet run, and met the criteria in 27 against 32 to 33. Haiku
  sorted emails slightly better (105 of 120, against 99 to 101).
- **The skipped calendar check was mostly the command-line route, not the agent.** On LangChain's own
  API client (the native-client check below), Haiku checked the calendar on that email in 3 of 3 runs.
- **The school-deadline break is real.** It shows again on LangChain's own client, Sonnet 3 of 3
  against Haiku 0 of 3 (below).
- The email agent is hard for every model on reply quality: about half of the replies meet
  LangChain's written criteria. The criteria are strict (exact tools, exact content).
- At 3 runs the numbers were: triage 51, 49 and 53 of 60; tools 18, 17 and 15 of 33; criteria
  17, 18 and 14 of 33 (main, control, Haiku). Reports: `email/runs/gate-*.md` (3 runs),
  `email/runs/gate-*-x6.md` (6 runs) and `email/runs/gate-pooled-*.md` (pooled main). The third
  Sonnet run scored triage 100 of 120, tools 34 of 66 and criteria 32 of 66.

### Mining: real failures become tests

29 new, realistic emails were labelled from the agent's own triage rules, before any run, and
sent through the agent once each, like a day of mail. Flywheel scored them with the same three
checks and found 4 failures in 3 places:

| Failures | Where it went wrong |
|---:|---|
| 2 | The reply agent skipped an expected tool (the calendar check). |
| 1 | The reply missed its criteria. |
| 1 | Triage answered a CI-failure notice that should only have been flagged. |

All 4 became test cases, growing the dataset from 16 to 20. Two of them decided the email gates:
the calendar case at first, and the school-deadline case once main was pooled. The traffic ran on the command-line
route, so the two skipped-tool failures may partly be the route (see the native-client check).

### What Flywheel caught that was not the agent

Mid-study the model service's usage limit ran out partway through a control run. Flywheel blocked
that run: 12 cases broken and 16 raising errors they did not raise before. The run was thrown
out and redone, and the blocked report is kept
(`email/runs/v1-transport/gate-control-limit-hit.md`). This is the gate doing its job on a
broken run.

## What was fixed along the way

- **A bug in Flywheel's own gate.** A check that only applies to some cases (the reply checks
  only apply to reply emails) was counted as a failure on every other case, so totals read
  14 of 60 instead of 14 of 33. Fixed in `src/flywheel/gate.py`, with a test.
- **Comparing against one run of main.** A case that passes about a third of the time can look
  broken against one lucky run. `--base` now takes several runs and pools them
  (`src/flywheel/experiment.py`, with tests); see the email results above.
- **Two grader bugs in this study's SQL check**, both found by reading failed answers: "138.6"
  did not match "138.60", and a read-only schema lookup (`PRAGMA table_info`) was flagged as a
  write. Both fixed and tested, then every SQL run was rescored.

## The native-client check: LangChain's own client

Every run above went through a command-line route, where the model returns its tool calls as
JSON instead of making native tool calls. To test what that changes, both models were run again
on LangChain's own `ChatAnthropic` client against the Anthropic API, 3 runs per case: Haiku on
both agents, then Sonnet on the email agent, 697 model calls in all.

### Does the command-line route give the same answers?

| | Command-line route (Haiku) | LangChain's own client (Haiku) |
|---|---|---|
| SQL, first 24 questions: correct | 70 / 72 | 72 / 72 |
| Email: sorted into the right category | 53 / 60 | 51 / 60 |
| Email: called every expected tool | 15 / 33 | 27 / 33 |
| Email: reply met LangChain's criteria | 14 / 33 | 27 / 33 |

- **On the SQL agent the two routes agree.** Flywheel's gate between them passes.
- **On the email agent they do not.** Sorting emails is about the same. Replies are far better
  on the native client: the expected tools were called in 27 of 33 runs against 15. The command-line
  route made the email agent's replies look worse than they are. So the email results in the
  section above measure the command-line route as much as the models.

### The email verdict on LangChain's own client

| | Sonnet 4.5 (main) | Haiku 4.5 (change) |
|---|---|---|
| Sorted into the right category | 52 / 60 (87%) | 51 / 60 (85%) |
| Called every expected tool (reply emails) | 24 / 33 (73%) | 27 / 33 (82%) |
| Reply met LangChain's criteria (model judge) | 27 / 33 (82%) | 27 / 33 (82%) |

- **On the native client, Haiku matches Sonnet on totals.** Both met LangChain's reply criteria
  in 27 of 33 runs.
- **Flywheel still blocks the move to Haiku, on one case: the school deadline.** Sonnet
  acknowledged the March 7 deadline in 3 of 3 runs, Haiku in 0 of 3. This is the same case that
  blocked on the command-line route, so the break shows on both routes. A total-score dashboard would
  have called the two models equal and shipped the change; the per-case gate shows one email
  type that Haiku reliably gets wrong.
- Haiku also fixed one case (a joint-presentation request: Sonnet 0 of 3, Haiku 3 of 3), and one
  GitHub notification moved by less than the noise threshold. Report:
  `email/runs/gate-api-haiku.md`.
- This gate uses one native Sonnet run as main, with no native control; the command-line-route control
  showed single-run mains can mislead. The school-deadline break is the one result that holds
  across the command-line route (pooled main) and the native client.

## How it ran

- **Two transports.** The native-client check above used `ChatAnthropic`. Every other run
  called the model through a headless command-line client, wrapped as a LangChain chat model
  (`subchat.py`). The agents' graphs, prompts and tools are unchanged; only the model transport
  differs.
- **That transport is a disclosed difference.** The model does not get native tool calls; it
  returns its tool calls as JSON. In early runs it sometimes told the user "the SQL tools are not
  available" instead of calling them. Clearer framing cut this from 3 runs in 8 to about 1 run
  in 100 (0 of 108 Sonnet main runs, 1 of 108 Haiku runs, 2 of 108 control runs). Those runs count
  as failures above; they were not dropped.
- **The email judge** is Claude Sonnet 4.6, the same for every run, using
  LangChain's own judge prompt.
- **LangSmith's monthly trace limit was reached**, so the traffic traces were exported to a
  file and mined with `flywheel mine --from-file` rather than read from LangSmith.
- Usage limits cut some runs short. `assemble.py` rebuilds a run from its saved answers and the
  remaining cases were run separately; each case keeps its first 3 answers (or 6).

## How often the gate blocks a change that did nothing

The controls above are single gates. To measure the false-block rate, every stored run of the
unchanged agent was pooled per case and gated against itself 2,000 times, drawing disjoint runs
for the two sides each time ([false_block_check.py](false_block_check.py), no new model calls).
Both sides are the same agent, so every block is a false one.

| Agent | Main runs vs head runs | Blocked, fall-by-half rule | Blocked, Fisher test (`max_p = 0.05`) |
| --- | --- | --- | --- |
| SQL, 36 cases | 3 vs 3 | 0% | 0% |
| Email, 20 cases | 3 vs 3 | 50% | 7% |
| Email, 20 cases | 6 vs 6 | 34% | 10% |
| Email, 20 cases | 12 (pooled) vs 6 | 17% | 5% |

- **On the SQL agent the gate is quiet.** Its cases pass almost always, so a fall by half is
  never noise.
- **On the email agent the fall-by-half rule is not.** Eight of its case checks pass between
  20% and 80% of the time across 18 Sonnet runs, and "the pass rate fell by half" fires on one
  of them by chance in half of all gates at 3 runs a side. Pooling main helps, and still leaves
  one gate in six blocked for nothing. The single controls that passed were the lucky draws.
- **So Flywheel gained a second rule: `max_p`.** With `max_p = 0.05` in `[gate]`, a one-sided
  Fisher exact test on each case's pass counts decides instead of the fixed threshold. A case
  blocks only when a fall that large would show up less than one time in twenty with nothing
  changed, so a coin-toss case needs more runs to block. It cut no-change blocks to 5-10%.
  The fall-by-half rule stays the default, so existing gates are unchanged.
- **The cost is power on coin-toss cases.** Against Haiku, pooled main (12 runs) against
  Haiku's six blocked in 84% of gates under the fall-by-half rule and 74% under the Fisher test.
  The school-deadline case itself was caught in 45% of gates under the old rule and 12% under the
  new one: on the command-line route Sonnet met it in only 11 of 18 runs, so Haiku's 1 of 6 is
  not strong evidence on its own. The Fisher gates that blocked Haiku did so mostly on a
  meeting-scheduling email (Sonnet 9 of 18, Haiku 0 of 6, p = 0.04).
- **On the native client the school-deadline break holds under both rules.** Sonnet 3 of 3
  against Haiku 0 of 3 gives p = 0.05, exactly the threshold, and the gate still blocks there.
- With three runs a side, only a full 3 of 3 to 0 of 3 flip reaches 0.05. Use the test with a
  pooled main (`--base a.json b.json`), where it has the runs to tell noise from a break.
- The draws treat any run of a case as exchangeable with any other. The three Sonnet runs were
  made on different days, so the real noise between two days can only be larger.

## Gaps

- **The pooling fix was tested on one agent, with one independent control.** It passed that
  control, but one test is not many. A case near the threshold can still flip with which runs
  are pooled, as the school-deadline case shows; the Fisher rule above is the remedy.
- **The native email gate has 3 runs a side and no native control.** The school-deadline break
  is consistent across routes, but more native runs would firm up the rest.
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
