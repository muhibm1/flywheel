# Brief: write Flywheel test cases for one open-source agent project

You are setting up Flywheel, a regression gate for AI agents, on one open-source agent project, the
way a team adopting it would. Flywheel runs a set of test cases (tasks for the agent, each with a
code check) on the main branch and on a pull request, several times each, and blocks the pull
request if a case that used to pass now fails, or starts raising errors.

Your project folder is `/tmp/rr/blind/<project>/`. It holds one folder per pull request ("gate"),
named like `<project>-g1`. Each gate folder has:
- `gate.json`: `base_src` (the project's source tree at the commit before the pull request),
  `base_env` (a Python venv with that tree installed), and the commit ids.
- `change.diff` and `change-message.txt`: the pull request's diff and message, exactly as a
  reviewer sees them when it opens.

## Hard rules (the study is worthless if these break)

1. Read ONLY: your project folder, the `base_src` and `base_env` paths it names, the Flywheel source
   at `/home/user/flywheel/src` and `/home/user/flywheel/README.md`, `/home/user/flywheel/examples`,
   and this brief. Do NOT read anything else under `/home/user/flywheel` (in particular not
   `studies/`), nothing under `/root`, `/mnt`, `/tmp/claude*`, other `/tmp/rr/blind/*` projects, or
   `/tmp/rr/src` / `/tmp/rr/envs` entries other than the ones your gate.json files name. The one
   exception under `/root` is each gate's `head_env` (and the source it is installed from), named in
   gate.json, used only as step 4b says.
2. No git commands, no network fetches of the project (no GitHub, no PyPI pages about it, no issue
   trackers). You must not learn what happened to any pull request after it was opened.
3. Never apply a diff yourself. The pull request's version is already installed at `head_env`
   (named in gate.json); you may RUN it only in step 4b below, and only to explore.
4. You may run the agent on base versions to make sure each case works (see below). Do not tune a
   case to make it fail or pass on purpose; a case should be a fair test of correct behaviour.
5. At the end, list every path outside your project folder you read, in your final reply.

## Working without prompts

Write every file with the Write or Edit tool, never with a shell heredoc or `echo`/`cat`
redirection (those raise permission prompts and stall the run). If any command hits a permission
prompt, abandon it and take another route. Keep shell commands simple.

## Model access

All model calls go to an OpenAI-compatible endpoint already running at
`http://127.0.0.1:8765/v1` (any api key string, e.g. "sk-local"; model name `claude-haiku-4-5`).
Point the project's own agent at it through the project's normal model configuration for an
OpenAI-compatible provider (e.g. `ChatOpenAI(base_url=...)`, LiteLLM `openai/<model>` with
`api_base`, `OpenAIChatCompletionClient(base_url=..., model_info=...)`). Use chat completions, not
the OpenAI Responses API. Do not use any other model or key. Keep `temperature` unset or the
project's default.

## What to build

In `/tmp/rr/blind/<project>/suite/`:

1. `adapter.py` with `target(inputs: dict) -> dict` that builds the project's agent the way its
   README/examples do, runs one task, and returns what the checks need (final answer, tool calls
   made, files written, any error text). Tasks must be self-contained and offline: local files,
   local tools you define in the adapter, a local HTTP server or sqlite db you create in a temp
   folder, never the public internet. Every run gets its own temp folder. Put a per-run timeout
   (e.g. 300 s) and a sensible step limit. If the agent raises, let the exception propagate
   (Flywheel records it as an error).
   The adapter must work on every gate's base version in this project. If the API differs between
   bases, branch on what is importable, not on the gate id.
2. Check functions `check_x(inputs, outputs, reference_outputs) -> bool` in `adapter.py`, computed by
   code wherever possible (exact values, files present, tool called, no error). A model-judged check
   is allowed only when no code check can work; it must also call the same endpoint.
3. **Standing suite** `standing.jsonl`: 6 to 8 cases a team would write from the README, docs and
   examples alone: typical tasks this agent is built for, covering its main features (tool use,
   multi-step tasks, structured output, memory or planning if the project has them). Write this
   BEFORE you open any `change.diff`. Each line:
   `{"id": "<short unique>", "inputs": {...}, "reference_outputs": {...}, "metadata": {"source": "standing"}}`.
4. **Change-aware cases**, after the standing suite is saved: for each gate, read its
   `change.diff` and `change-message.txt`, and write `<gate>/change.jsonl` with 3 to 5 cases that
   exercise behaviour the diff touches, as a careful reviewer would ("this PR changes how X works;
   here are tasks where X matters"). Same format, `"source": "change"`. Treat every gate the same
   way whatever you think of its diff: you are not told whether any change is good or bad, and you
   must not guess at it in the cases or files.
   Write at most 4 change-aware cases per gate. Do not run the head version for these.
4b. **Explored cases**, written last, after `change.jsonl` is saved: for each gate you may now run
   tasks on BOTH `base_env` and `head_env` to see where the pull request changes what the agent
   does. Then write `<gate>/diff.jsonl` with up to 4 cases (`"source": "diff"`) that test what the
   agent SHOULD do. Rules for every explored case:
   - Its check encodes correct behaviour you can justify from a written source: the base README,
     docs or docstrings, the pull request's own message (its stated intent is correct by
     definition), or a plain user expectation (the task gets done, no crash, the answer is right).
     Put that source in `metadata.citation` (a short verbatim quote and where it is from) and one
     sentence in `metadata.rationale`.
   - Never write "same output as base". A difference the pull request's message says it intends is
     correct behaviour, not a failure.
   - If you find no difference that breaks correct behaviour, still write 2 to 4 cases that
     exercise the changed code and that a correct agent passes. Treat every gate the same way.
   - Record in `metadata.seen_on_head` what you observed on head for that case ("pass", "fail",
     "error", "not run").
   - Every explored case must pass on base in 2 of 2 runs before you keep it.
5. For each gate, `<gate>/flywheel.toml`:
   ```toml
   [flywheel]
   target = "adapter:target"
   evaluators = ["adapter:check_a", "adapter:check_b"]
   dataset = "dataset.jsonl"
   repetitions = 3
   [gate]
   max_broken = 0
   close_call_repetitions = 3
   min_new_error_runs = 2
   ```
   and `<gate>/dataset.jsonl` = standing.jsonl, then change.jsonl, then diff.jsonl, and a copy of
   (or a tiny import shim to) `suite/adapter.py` next to it named `adapter.py`. Check field names in
   `/home/user/flywheel/src/flywheel/config.py`; adjust if a key is named differently.
6. Anything you install into a base env for the adapter, install into that gate's head env too
   (same versions). Flywheel is already in the head envs. Install Flywheel into each base env: `uv pip install -p <base_env> -e /home/user/flywheel` (add
   only what the adapter itself needs, and the same additions must work on every base).

## Check on base only

For each gate: from the gate folder, run
`<base_env>/bin/flywheel run --label smoke --out smoke.json --repetitions 1 --concurrency 2`.
Each case should pass on base. A case that fails on base because the case or check is wrong:
fix the case or check. A case that fails on base because the base agent genuinely can't do it:
replace it with a fairer one (a team's suite passes on main). Report, for every gate, how many
cases pass on base. Keep total smoke runs modest; the model has a usage window.

## Final reply

Short: per gate, number of standing, change-aware and explored cases, the base smoke pass count,
and for explored cases what you saw on head; anything
that could not be made to work and why; and every path outside your project folder you read.
