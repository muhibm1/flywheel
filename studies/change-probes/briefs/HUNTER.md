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

Two more sources of hypotheses, both mandatory:

- **Every sentence of CHANGE.md.** Each sentence that describes a behaviour ("a removed tool
  comes back, and a replaced or subclassed one is swapped") names cases. Probe each named case on
  its own (removed, replaced, subclassed are three probes), and ask of each: who was doing this at
  base, and what happens to them now?
- **Every new rule against every special moment.** When the change adds a rule (refuse, repair,
  retry, cap, wait, raise, strip), list the special moments of the surrounding loop: the first
  step, the last allowed step, a turn after which no further request can follow (a final or
  delivery-only turn), limits already reached, retries already used, a resumed or second run, a
  hand-off and return. Probe the new rule firing at each of those moments. A rule that is harmless
  mid-run often breaks at the end of one.

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
 "effect": "loss | gain_or_repair | reshape",
 "loss_kind": "raises_where_it_returned | action_no_longer_happens | result_missing_or_wrong | run_cut_short | user_customisation_discarded | hang | null",
 "reach": "mainstream | legitimate_edge | contrived",
 "reach_reason": "who meets this and how, through which public entry point",
 "declared": "quote from CHANGE.md or the diff that announces this behaviour, or null"}
```

How to classify. This is the part reviewers get wrong, so follow it literally.

- **effect** describes what happens to a user who was relying on base, nothing else.
  - `loss`: something that worked at base no longer achieves its outcome at head. A call that
    returned a result now raises. An approval, tool call or hand-off that happened no longer
    happens. A run that finished with an answer is now cut short or ends empty. Text that passed
    through unchanged now makes the run fail. Something the user set up is thrown away.
  - `gain_or_repair`: head does more or better and nobody loses. A crash became a clean error. New
    data is added. A wrong result became right.
  - `reshape`: same outcome in a different form. Reworded messages, reordered lists, extra
    metadata, log lines.
- **A loss stays a loss when the change announces it.** "This change ignores X", "X is no longer
  carried over", "now raises on Y", "capped at N" describe a loss if someone legitimately used X,
  Y or more than N. Authors announce trade-offs they believe are safe; teams revert them when
  users turn out to depend on the old behaviour. Record the announcement under `declared` and
  still write `effect: loss`. Do not call a loss "intended".
- **A loss stays a loss when the change calls the old behaviour a bug or a risk**, as long as a
  legitimate user could have depended on it.
- **reach**: `mainstream` means a user following the documented public interface in normal
  operation meets it. `legitimate_edge` means an unusual but valid use of the public interface.
  `contrived` means it needs invalid input the project already rejected elsewhere, a private
  interface, a tampered environment (reloading modules, installing packages mid-run), or a model
  or server behaving in a way no real one does.
- A bug in a feature that did not exist at base is not a loss. List it with `effect:
  gain_or_repair` and say so in `what_a_user_sees`.

If you found no confirmed difference, write an empty list.

Finish with `HUNT_NOTES.md`: ten lines at most on what you covered, what you could not reach and
why. Your final message: the count of probes, confirmed differences, and findings per `effect`.
