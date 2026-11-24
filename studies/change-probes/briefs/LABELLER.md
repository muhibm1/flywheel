# Labeller brief

You turn proposed regressions into proven ones. Each proposal names an introducing change, the
commit before it (base) and a later fix. A proposal is kept only if a test shows the full story:
it passes on base, fails on the introducing change (head) and passes on the fix. Other agents will
later be tested on these changes without knowing the outcome, so everything you write is an answer
key: write only into the sealed folder named in your task, and report only counts.
Read `briefs/SHELL_RULES.md` (next to this file) first.

## Input

For your project, two files in the sealed folder (either may be missing):

- `mined/<project>.json`: rows a reader found where the team names the introducing change.
- `candidates/<project>.json`: fix commits paired by a script with the commit that last wrote the
  lines the fix replaced (`intros`, best first).

Work through the mined rows first, then the candidates, until you have 8 proven rows for the
project or run out. Skip a candidate whose introducing change is already proven.

## For each proposal

1. Check out three trees with `git -C <clone> worktree add --detach <work>/<project>/<n>-<side> <sha>`
   for base (`base_sha`), head (`intro_sha`) and fix (`fix_sha`). Remove them when done
   (`git -C <clone> worktree remove --force <path>`).
2. One environment per project is enough unless dependencies changed between the commits:
   `uv venv --python 3.12 <work>/<project>/venv`, install the project's dependencies and test
   extras (not the project itself as an editable install), plus `pytest pytest-asyncio`. Run
   tests with the helper, which puts the tree on the import path and sets placeholder
   credentials: `<venv>/bin/python /home/user/flywheel/studies/change-probes/run_pytest_at.py
   <tree> <source root or .> <test path>::<test name> -x -q`. Never set an environment variable
   on the command line. If the project cannot run without an editable install, make one venv per side.
3. Find the witness. Take the tests the fix commit added or changed (`git -C <clone> show <fix_sha>
   -- <test paths>`). Copy the fix's version of those test files over the same paths in the base
   and head trees (they are throwaway worktrees). Run each new or changed test on all three.
   A witness is a test that **passes on base, fails on head, passes on fix**, twice in a row, and
   fails on head with an assertion or error about behaviour (not ImportError, a missing fixture,
   or a name that only exists after the fix).
   - If the fix's tests cannot run on base because they use an API the fix added, you may write a
     minimal witness yourself from the fix's description, using only API that exists on all three
     trees. Mark it `"witness_origin": "written"`. Do this at most where the story is clear.
   - Needs a network, a paid service, a live model, Docker or a GPU: drop it
     (`"dropped": "needs <what>"`).
4. Check the head change is usable: at most 2,000 changed source lines, touches source, and base
   is the first parent of head.
5. Keep the row only when the witness holds. Fails on base too means the behaviour never worked
   (not a regression): drop with `"dropped": "fails on base"`. Passes on head means the pairing
   is wrong: try the next entry in `intros`, then drop with `"dropped": "passes on head"`.

## Output

Write `labelled/<project>.json` in the sealed folder: a list with one row per proposal you
examined, kept or dropped:

```json
{"repo": "owner/name", "intro_sha": "...", "base_sha": "...", "fix_sha": "...",
 "intro_date": "2026-08-14", "intro_title": "...", "changed_source_lines": 180,
 "source": "mined | candidate", "team_named_cause": true,
 "team_quote": "the fix's own words on what broke, or null",
 "what_broke": "one plain sentence",
 "witness": {"path": "sealed path of the witness file", "tests": ["tests/x.py::test_y"],
             "origin": "fix | written", "base": "pass,pass", "head": "fail,fail", "fix": "pass,pass",
             "head_failure": "last line of the failure"},
 "python": "3.12", "install": "exact install commands that worked", "source_root": "src",
 "kept": true, "dropped": null}
```

Save each witness test file under `witnesses/<project>/<intro_sha[:10]>/` in the sealed folder.
Record the install commands exactly: the gate builder reuses them.

Budget about 15 minutes per proposal; a proposal that needs more is dropped as `"too costly"`.
Final message: proposals examined, kept, and dropped by reason. Nothing about the rows.
