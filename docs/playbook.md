# The first two weeks with a customer's agent

This is the plan I would follow when a team hands me an agent that "works in the demo" and asks
whether it is ready for production. It is written for the team's engineers and for whoever
signs off on the launch, so each step says what it gives the business as well as what gets
built.

The short version: **you cannot improve what you cannot see, and you cannot ship what you cannot
compare.** Week one makes the agent visible. Week two makes every change comparable.

Terms used below:
- **Trace**: a recording of one agent run in LangSmith, every model call and tool call in order.
- **Dataset**: a saved list of inputs with the answers we expect.
- **Evaluator**: a small function that scores one run, such as "did it pick the right team".
- **Experiment**: one version of the agent scored against one version of the dataset.
- **Regression**: a change that makes something that used to work stop working.

## Week one: make it visible

**Day 1. Turn on tracing everywhere the agent runs.** Set `LANGSMITH_TRACING` and a project
per environment (`<app>-dev`, `<app>-prod`). Name the root run after the business action
(`refund-request`, not `RunnableSequence`) and put the customer-facing ids in metadata, so a
support ticket can be matched to its trace in one search.
*What the business gets:* when something goes wrong, the answer to "what did the agent do?"
takes a minute, not a day.

**Days 2 to 3. Write down what "correct" means, as code.** Sit with the people who own the
outcome (support leads, the on-call team, compliance) and turn their judgement into evaluators.
Start with the checks that are cheap and certain: right team, right action, no forbidden tool
called, answer cites a source. Use a model as a judge only for what code cannot check, and
test the judge against a dozen human labels before trusting it.
*What the business gets:* a shared, written definition of a good answer, which usually exposes
a disagreement worth settling before launch, not after.

**Days 4 to 5. Build the first dataset from real traffic, not imagination.** Score a week of
traces with the evaluators (`flywheel score`, or LangSmith's online evaluators), then mine the
failures (`flywheel mine`). Failures group by where the agent went wrong, so twenty failures
are often three bugs. Put the failing runs in an annotation queue; a domain expert writes the
correct answer for each. Promote the reviewed ones into the dataset (`flywheel promote`).
Add a handful of hand-written cases for the rules that must never break (safety, money,
privacy), because real traffic may not have hit them yet.
*What the business gets:* a test set that reflects what customers actually send, with a named
person who signed off on every expected answer.

## Week two: make every change comparable

**Days 6 to 7. Gate every pull request.** Add the Flywheel action. Each pull request runs the
dataset against the change and against the main branch, compares them case by case, and
comments the result. Fail the check on a broken case. Use the scripted or recorded model path
in CI where one exists (free and deterministic), and a live-model run for prompt and model
changes, which a scripted model cannot see.
*What the business gets:* "did this change make anything worse?" has an answer before the
change ships, with a link to the exact case and trace.

**Day 8. Agree the noise policy in advance.** A live model does not answer the same way twice.
Decide, before the first argument, how many repetitions a case runs and how big a move counts
as real (Flywheel's default: three runs, and two of them must flip). Write the decision in the
config, so nobody relitigates it on a Friday release.
*What the business gets:* a red check means something, so people stop ignoring it.

**Days 9 to 10. Close the loop and hand it over.** Schedule the mining job (daily is usually
enough), route its report to the team's channel, and run one real cycle together: a production
failure becomes a case, the case fails on main, a fix makes it pass, and the gate shows it as
fixed. Keep a frozen held-out set that nobody tunes against, and score it only when a version
is ready to ship, so the team can tell real improvement from fitting the test.
*What the business gets:* the team can run the loop without me, and the launch decision rests
on numbers they trust.

## What I watch for

- **An average that hides a broken case.** Two cases fixed and one broken reads as "better" in
  an average. The gate reports cases, not averages, for this reason.
- **A prompt change tested on a scripted model.** It passes every time, because the script does
  not read the prompt. Prompt and model changes need a live run.
- **A dataset that only grows from imagination.** If no case came from a trace, the dataset
  tests what the team expects, not what customers do.
- **Tuning against the held-out set.** Once a team has seen held-out scores while making
  changes, those scores stop meaning anything. Freeze it and protect it.
