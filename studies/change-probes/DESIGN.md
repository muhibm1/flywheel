# Change probes: a redesign so Flywheel stops at least 92% of real shipped regressions

Written 2026-11-23, before any code for it existed and before any new project was looked at.
Amendments are dated and appended; nothing above an amendment is edited after it.

## In plain words

Flywheel is a check that runs before a code change to an AI agent is merged. Until now it worked
by running a fixed list of test tasks on the old and new code and blocking the change when a task
that used to pass now fails. The study of 23 November 2026
(`docs/results/real-regressions-2026-11-23.md`) showed the limit of that idea. Of 18 changes that
real teams shipped and later had to fix, the best version blocked 10. Every miss had the same
cause: the bug only showed on an input or a state that no test task used. A file with Windows line
endings. A chat history that starts with a greeting. A tool loop that runs 25 times.

A list of tasks written in advance cannot be expected to contain the one odd input a future change
will break. So this redesign stops relying on the list. For every change, Flywheel now:

1. reads the change and writes down every way the new code behaves differently from the old code;
2. writes a small program (a "probe") for each difference and runs it on both versions, with a
   scripted stand-in for the language model so the result is the same every time;
3. checks that the probes really executed every changed line;
4. has a second, independent reviewer try to knock down each difference that looks harmful;
5. blocks the change only when a probe passes on the old code, fails on the new code every time,
   and the difference is not something the change said it meant to do.

The target, set by the owner: block **at least 92% of real regressions, for the reason the team
itself later gave**, on changes nobody on this project has seen, while blocking **at most 10% of
harmless changes**. The number counts only on fresh data, with the code frozen first, scored once.

## Why the old design could not reach the target

| What the old gate did | Why it missed |
|---|---|
| Ran tasks through a live model (Claude Haiku) | A live model cannot be made to produce 25 tool rounds, a malformed reply or a failed upload on demand. Rare conditions were unreachable. |
| Cases were written before the change was run, or after a short try | Nothing forced a case to reach the changed lines, so most cases never touched the bug. |
| A case needed a known right answer in advance | The writer had to guess the bug to write the check. A comparison of old against new needs no guess. |
| One writer, one pass | No second look, and nothing measured what was left unexplored. |
| 18 regressions | Too few for any rate near 92% to mean anything. |

## The new method

Terms: **base** is the code just before the change. **Head** is the code with the change. A
**probe** is a short script that drives the project's own public code in one specific situation
and records what happened. A **scripted model** is a fake language model that returns replies the
probe wrote in advance, so a run is repeatable and can be steered into any situation.

### Step 0. Mechanical preparation (code, no model)

- Parse the diff into changed files, functions and executable lines.
- Build base and head trees with the same dependencies, pinned to what existed on the change's date.
- Run the **base** version of the tests that touch the changed files against the **head** code. A
  change often edits tests to match its new behaviour; the old tests failing on new code is a free
  list of behaviour differences to examine.

### Step 1. The difference ledger (model: "hunter")

A hunter reads the diff, the surrounding code and the change's own description. For every hunk it
lists each behaviour difference: what changed, who is affected (which callers, inputs, states),
and whether the change says it is intended. It must walk a fixed checklist for every hunk. The
checklist is built from every regression missed so far and from general experience of how changes
break things:

1. Input forms: encodings, line endings, empty, very large, missing values.
2. State that already exists: history shape, resumed or saved sessions, cloned or copied objects.
3. Failure paths: a dependency or tool fails; which error is raised, swallowed or changed.
4. Output modes: structured output, streaming or not, sync or async, the final turn of a run.
5. Limits and loops: counters, caps, boundaries, long chains.
6. Other callers: every call site, subclass and override of a changed function; changed
   signatures, defaults and return shapes.
7. Removed code: what case did the deleted lines handle?
8. Concurrency: event loops, threads, context variables.
9. Imports, configuration and optional dependencies.
10. Wire formats and compatibility: schemas, serialised data, HTTP behaviour.
11. Templates and formatting: placeholders, escaping.
12. Feature combinations: the changed feature used together with each neighbouring feature.

The ledger is a structured file. Code rejects it if any hunk has no entry or any checklist item
is left without either a probe or a written reason it cannot apply.

### Step 2. Probes on both versions (hunter, with execution)

For each ledger entry the hunter writes a probe and runs it on base and on head. Rules enforced by
the runner, not by trust:

- A probe uses the project's public entry points and a scripted model. It may inject faults (a
  tool raises, the model returns a malformed or truncated reply).
- Each probe runs 3 times per side. Only a probe that passes 3 of 3 on base and fails 3 of 3 on
  head is a **confirmed difference**. Anything else is recorded and cannot block.
- **Changed-line coverage.** The runner measures which changed lines on head the probes executed.
  The hunter keeps going until every changed executable line is executed by at least one probe, or
  carries a written reason it cannot be reached. Both outcomes of every changed condition count.

### Step 3. Two independent hunters

Two hunters work each change without seeing each other's notes, with different starting emphases
(one starts from callers and existing state, one from inputs, failures and limits). Their
confirmed differences are pooled. Whether the second hunter earns its cost is measured on
development data before the freeze.

### Step 4. The verifier (a fresh model, told to disagree)

A separate reviewer with no view of the hunters' reasoning receives each confirmed difference: the
probe, both outputs, the diff, the change's description and the base documentation. Its job is to
knock the finding down. It reruns the probe itself, then answers four questions:

1. Is the probe realistic: public entry points, an input a real user could send?
2. Did this work at base? A bug in a feature the change adds is reported but never blocks; only a
   loss of something that worked counts as a regression.
3. Is the difference stated or clearly implied as intended by the change?
4. Is there harm: a crash, a wrong or lost result, a broken documented promise, a hang, or a
   silent change to a default?

### Step 5. The verdict (code)

Flywheel blocks when at least one finding is confirmed by the runner (3 of 3 against 3 of 3),
reproduced by the verifier, and answered realistic, worked-at-base, not intended and harmful.
Otherwise it passes. The model supplies hypotheses and judgements of intent; code holds the
evidence and makes the decision. The report lists each blocking finding with its probe so a
maintainer can rerun it.

### Where this lives in Flywheel

`src/flywheel/probe/`: diff mapping, the probe runner, the scripted model and fault injection,
changed-line coverage, the ledger format and its validator, the verdict rule and the report, with
a `flywheel probe` command. The hunter and verifier instructions ship in the package as briefs.
The existing live-model gate stays as it is for changes to prompt wording, where the question is
how a real model reacts and only a live run can answer.

## Scope, stated before any data is collected

In scope: a regression that can be shown with a repeatable test once you know where to look.
Out of scope for this number: a regression that exists only as a shift in how a live model
responds to reworded prompt text. Those need the live gate. Every candidate dropped for this
reason is counted and published, so the reader can see what share of real regressions the number
covers.

## Data: where the regressions come from

**Projects.** Public open-source projects that build or run language-model agents (frameworks,
agent applications, agent tooling). Python first; TypeScript projects are added only if the pool
is too small, decided before any held-out run. Never used before means none of the 13 projects in
the earlier study (ADK, agno, AutoGen, browser-use, crewAI, deepagents, gpt-researcher,
mini-swe-agent, open_deep_research, OpenHands, pydantic-ai, smolagents, strands-agents) and none
of my own repositories.

**A regression enters the pool only if all of these hold:**

1. **The team names the cause.** A later fix, revert or issue from the project's own maintainers
   identifies the introducing change and says what got worse. A bare "Revert X" is excluded.
2. **It is recent.** The introducing change was merged on or after 2026-07-01, after the training
   data of every model used here ends. No model can have memorised the fix.
3. **It is proven by execution.** A labelling agent, separate from every hunter, produces a
   **witness**: a test (the team's own regression test where one exists) that passes on base,
   fails on head and passes on the team's fix, each run twice. No witness, no entry. The witness
   is sealed and never shown to a hunter or verifier.
4. **It was working before.** The witness passing on base is what makes it a regression and not a
   bug in a new feature.
5. **It is reviewable.** At most 2,000 changed source lines. Larger changes are counted and listed.

**Harmless controls.** One per regression: a change from the same project and the same months, of
similar size, touching source code, at least 30 days old, that no later commit, pull request or
issue names as the cause of a problem (a fixed, scripted search). Picked by a seeded script, never
by hand. "No known fix" is not proof of harmless, so every blocked control is counted as a false
block in the headline, with an adjudicated count beside it.

**Sets.** The pool is split by project, with a fixed seed, into:

- **Development (D2):** about 20 regressions and 20 controls. Open for tuning. The 18 regressions
  already scored and the 11 never run from the earlier study (D1) are also development data.
- **Held-out H1, H2, H3:** each 60 regressions and 60 controls, each from projects that appear in
  no other set, at least 8 projects per set and at most 8 regressions per project. H2 and H3 are
  reserves. They are opened only if H1 misses the target, each after a rework frozen in advance.
  A set with fewer than 50 validated regressions is not scored as a headline.

Sixty regressions is the smallest size at which 92% is a meaningful statement: 56 of 60 has a 95%
interval of about 84% to 97%.

## How leakage is prevented

- **Separate roles.** Mining and labelling agents see the fixes. Hunters and verifiers never do.
  The answer key, the witnesses and the fix commits sit outside every hunter's working folder.
- **No history to peek at.** A hunter gets the base and head trees as plain exported folders with
  no git history, plus the change's title and description as they stood at merge. The labeller
  removes any later text from the description.
- **No look-ups.** Hunters may install dependencies, pinned to the change's date, and nothing
  else from the network. No web search, no fetching the project.
- **Neutral ids, same treatment.** Gates carry shuffled ids. Regressions and controls get the same
  brief, the same budget and the same steps. Hunters are not told the mix.
- **Post-cutoff data.** Rule 2 above.
- **The orchestrator stays blind.** Mining reports counts only. The key for a held-out set is read
  by the scoring script and by nothing else until that set is scored.
- **Freeze.** The method code, the briefs, the model choices, the verdict rule and the scoring
  script are committed and hashed before the first held-out gate starts. Each set is scored once.
  After scoring, a set is development data forever.

## Scoring

- **Catch rate (primary, strict).** A regression counts as caught only if Flywheel blocked it and
  a blocking finding is the team's own bug. A blind adjudicator decides, given the team's words,
  the fix, the finding and the result of running the finding's probe on the fix commit (a probe
  that goes green on the team's fix is strong evidence). "Partly" counts as no.
- **Catch rate (loose).** Blocked for any reason. Reported beside the strict rate.
- **False-block rate (primary).** Controls blocked, of controls run. Beside it: how many blocked
  controls an adjudicator and a rerun find to be a real, unintended loss of working behaviour.
- **A gate that cannot run** after an honest attempt stays in the denominator as a miss (for a
  regression) or is reported (for a control).
- **Baselines on the same changes.** (a) The project's own tests: every change shipped with them
  passing. (b) A plain model: the same model as the verifier, given the diff, the description and
  the changed files at base and head, asked once whether to block and why, scored by the same
  strict rule. (c) The earlier gate's best result, for context.
- **Success, fixed now:** strict catch rate at least 92% (56 of 60) and false-block rate at most
  10% (6 of 60) on one held-out set scored once. Wilson 95% intervals are reported.

## Before the freeze: development gates

1. **Acid test.** The redesign must catch the 8 regressions the old gate missed (4 in round 1, 4
   in ADK), with hunters blind to what broke. If it cannot, the design is reworked before any
   mining cost is spent on held-out sets.
2. **D1 and D2 together:** strict catch at least 95% and false blocks at most 10%, leaving margin
   for the drop that always comes on unseen data.
3. Decide on development data only: one hunter or two, which model hunts, the verifier's
   strictness, the time budget per gate.

## If H1 misses

Read every miss, find the class of cause, rework the method, test the rework on D1, D2 and H1
(now development data), freeze, then score H2 once. The same again for H3. No set is scored twice.

## Known risks and what is done about each

| Risk | Response |
|---|---|
| The plain model does as well as the method | Reported either way. The method's edge is execution and forced coverage; the baseline shows whether that edge is real. |
| Hunters find real but unrelated bugs in controls | Only loss of behaviour that worked at base can block; the verifier must find it unintended and harmful; adjudicated count reported. |
| Too few recent, provable regressions | Mine at least 40 projects. If the pool is still short, add TypeScript projects. Never relax rules 1 to 4. |
| The usage budget | Hunters run on the cheapest model that passes the development gates. Mining and labelling run on smaller models. All on the subscription; API spend planned: $0. |
| The cloud machine is reclaimed mid-run | Every gate writes its state to the project's shared folder; runs resume from saved files. |
| A hunter looks something up | Forbidden in the brief; pinned installs; post-cutoff data makes recall useless; trees carry no history. |
| Strict scoring depends on a model adjudicator | The probe-on-fix result is mechanical evidence; the adjudicator sees no gate ids or arm names; a sample is re-adjudicated to measure agreement. |

## Amendment 1 (2026-11-23, after the acid test, before any fresh data was mined)

The acid test ran the method blind on the 9 regressions the old gate missed and on 4 harmless
changes. It changed three things. Nothing above is edited; where this section differs, it wins.

1. **An announced loss still blocks.** The first pass reproduced all 9 regressions but waved 3
   through because the change description announced the new behaviour. Findings no longer carry
   an "intended" label. Each confirmed difference gets an `effect` (`loss`, `gain_or_repair`,
   `reshape`), a `reach` (`mainstream`, `legitimate_edge`, `contrived`) and the announcement, if
   any, under `declared`. The announcement is recorded and never excuses a loss.
2. **One hunter, then a gap pass, then a verifier.** The second hunter is replaced by a gap pass
   (`briefs/GAP.md`) that reads the first pass's work and tests what it did not: combinations,
   every case the description names, every caller, and who relied on the old behaviour. The gap
   pass found the team's own bug in 2 of the 9 where the first pass had not.
3. **The verdict rule is code** (`verdict.py`). A finding blocks only when the runner confirms it
   (passes every base run, fails every head run), the verifier reproduced it for the stated
   reason through a public entry point, the feature existed at base, the effect is a loss, the
   base behaviour was not a defect, and either ordinary use meets it, or an unusual but valid
   use loses something that succeeded at base. A change in how an existing failure is reported
   blocks only when ordinary use meets it (`base_outcome`). This last clause was added after one
   harmless change blocked on a relabelled error.

These rules were tuned on 13 already-scored changes, which are development data. They are
checked on the rest of the old set and on a fresh development set before the freeze.

## Amendment 2 (2026-11-24, while building the fresh data, before any fresh change was gated)

Building the answer key taught five things. Nothing above is edited; where this section differs,
it wins.

1. **Ground truth is the witness, not the team's wording.** A regression is in the key when a test
   passes on the commit before the change, fails on the change and passes on the fix, twice in a
   row, and an independent auditor who did not write the witness agrees that it runs the
   project's code, fails for a behaviour reason, follows from the change, and checks something a
   caller could rely on (`briefs/AUDITOR.md`). Whether the team named the cause is recorded per
   row (`team_named_cause`) and reported, not required. Witnesses that depend on timing or a
   thread race, or that are not Python tests, are rejected.
2. **Two sources of proposals.** Rows where the team names the introducing change (150 projects
   read) and rows paired mechanically from the lines a fix replaced (`find_candidates.py`). Both
   pass through the same witness and audit. The source is recorded per row.
3. **A pull request merged with a merge commit is one change.** Head is the merge commit, base is
   its first parent. A fix inside the same pull request as the breakage is not a regression that
   reached the main line and is dropped.
4. **Controls are picked by code** (`pick_controls.py`): same project, within 75 days, similar
   size, at least 30 days old, never named by a later commit, never part of any proposal. A
   control that is blocked counts as a false block; no after-the-fact excuse is accepted.
5. **Sets are split by code** (`assign_sets.py`) with a fixed seed: whole projects go to one set,
   at most 8 regressions per project, H1 (60 regressions) filled first, then D2 (20), the rest
   is the spare held-out set H2.

Operational rules learnt: gates of one project share one environment where they can
(`briefs/PREP.md`, shared environment mode); no environment variable is ever set on a command
line (helpers set them inside Python).
