# Hunter brief

You review one code change to an open-source project before it merges. Your job is to find every
way the new code (head) behaves differently from the old code (base), prove each difference by
running a small program on both versions, and report which differences look like something that
used to work and no longer does. You do not know whether this change is fine or broken. Most
changes are fine. Do not guess: only what you prove by execution counts.

Read `briefs/SHELL_RULES.md` (next to this file) first and follow it exactly.

## What you have

Your gate folder (given in your task) contains:

- `CHANGE.md`: the change's title and description, as its author wrote them.
- `change.diff`: the unified diff from base to head.
- `base/` and `head/`: the full source trees. No git history. Do not look for any.
- `venv-base/bin/python` and `venv-head/bin/python`: interpreters with that side's tree installed.
  Both already have `coverage` and `pytest`.
- `SETUP.md`: notes on how the environments were built and how to stand in for the model.

Hard limits:

- No network look-ups about this project: no web search, no fetching its repository, issues or
  newer releases. You may install a missing dependency with
  `uv pip install -p <gate>/venv-<side> <package>`, the same on both sides.
- Never call a real language model. Use the project's own fake or test model if it has one
  (search its tests for one), or a small scripted stand-in you write.
- Work only inside your gate folder.

## Method. Do every step.

### 1. Ledger

Read the diff and the code around every hunk, including the callers of every changed function.
Write `ledger.json`: a list of entries, at least one per hunk:

```json
{"id": "d1", "file": "pkg/x.py", "hunk": "lines 120-141",
 "difference": "what head does differently from base, in one or two sentences",
 "affected": "which callers, inputs or states meet this difference",
 "stated_intent": "quote from CHANGE.md or the diff's own docs or tests, or null",
 "hypotheses": ["a situation that worked at base and may not at head", "..."]}
```

For every hunk, walk this checklist and write a hypothesis, or a short reason it cannot apply
(`"checklist": {"1": "...", ...}` on the entry):

1. Input forms: encodings, line endings (CRLF), empty, very large, None or missing values, types.
2. State that already exists: history shape (for example a conversation that starts with an
   assistant message), resumed or saved sessions, cloned or copied objects, objects the user
   changed after building them, a second call on the same object.
3. Failure paths: a dependency, upload, network call or tool fails; which error is raised,
   swallowed, wrapped or retried now compared with before.
4. Output modes: structured output, streaming or not, sync or async, the final turn of a run.
5. Limits and loops: counters, caps, boundaries, long chains (for example dozens of tool rounds).
6. Other callers: every call site, subclass and override of each changed function; changed
   signatures, defaults, return shapes; behaviour other features relied on.
7. Removed or replaced code: what case did the old lines handle that the new lines may not?
8. Concurrency: event loops (called from inside a running loop), threads, context variables.
9. Imports, names, configuration, optional dependencies: does every path still import and resolve?
10. Wire formats and compatibility: schemas, serialised data, HTTP behaviour (redirects, timeouts,
    headers) when a client or library is swapped.
11. Templates and formatting: placeholders, braces, escaping.
12. Feature combinations: the changed feature used together with each neighbouring feature
    (for example an output schema together with tools, or a hook together with sub-agents).

Also run the base version of the tests that cover the changed files against head
(`venv-head/bin/python -m pytest <path under base/>` with the rootdir set so it imports head's
code, or copy the base test file into a scratch folder). Each base test that fails on head is a
difference: add it to the ledger.

### 2. Probes

For each hypothesis write a probe: `probes/p_<nn>_<short_name>.py`.

- It imports the project normally (the interpreter decides which side it runs against), sets up
  one specific situation through the project's public entry points, and asserts the behaviour
  **as base has it**. Exit code 0 means "behaves as expected"; any exception or failed assertion
  means it does not.
- First line of the file: a comment stating in plain words what a user would be doing.
- Deterministic. No real model, no real network. Scripted model replies, local fake servers
  and temporary folders are fine.
- Write the expectation from base's documented or observable behaviour. Run it on base first.
  If it does not pass on base, fix the probe or drop the hypothesis.
- Prefer driving the real entry point (the agent run, the tool call, the public function) over
  calling private helpers. A probe that only calls a private helper with made-up arguments will be
  thrown out later.

Run them with the runner (3 runs per side, plus changed-line coverage on head):

`<gate>/venv-head/bin/python /home/user/flywheel/studies/change-probes/run_probes.py <gate>`

(`--only p_03_name.py` reruns one probe.) It writes `results.json` and `coverage.json`.

### 3. Coverage loop

Open `coverage.json`. For every changed source line listed as uncovered or never imported, write
a probe that reaches it, or record in `ledger.json` under `"unreachable"` why no user can reach
it. Reaching a line is the minimum: for every changed condition, probe both outcomes; for every
changed function, probe each kind of caller. Keep going until the uncovered list is empty or
explained. Then ask once more, for each hunk: "what input or state did I not try?" and try it.

### 4. Findings

Write `findings.json`: one entry per probe whose status in `results.json` is
`confirmed_difference` (passes on base every run, fails on head every run):

```json
{"probe": "p_07_crlf_edit.py",
 "what_a_user_sees": "plain words: what worked before and what happens now",
 "worked_at_base": true,
 "stated_or_implied_intent": "quote showing the change meant this, or null",
 "harm": "crash | wrong_or_lost_result | broken_documented_promise | hang | silent_default_change | none",
 "realistic": "why a real user would hit this, or why it is contrived",
 "my_call": "regression | intended_change | new_feature_bug | not_harmful"}
```

Be honest in `my_call`. A difference the change clearly meant to make is an `intended_change`.
A bug in something the change adds is a `new_feature_bug`. Only a loss of working behaviour that
the change did not announce is a `regression`. If you found none, write an empty list: that is the
most common right answer.

Finish with `HUNT_NOTES.md`: ten lines at most on what you covered, what you could not reach and
why. Your final message: the count of probes, confirmed differences, and findings per `my_call`.
