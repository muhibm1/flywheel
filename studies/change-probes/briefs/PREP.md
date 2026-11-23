# Gate preparation brief

You build the working folder for one or more "gates". A gate is one code change to an open-source
project, prepared so that a reviewer who must not see the future can study it. You are not the
reviewer. Do not review the change. Read `briefs/SHELL_RULES.md` (next to this file) first.

For each gate you are given: a neutral gate id, the repository, the base commit, the head commit
(the change), and optionally a Python version and install hints.

Build `<root>/gates/<gate-id>/` with:

1. `base/` and `head/`: the source trees at those commits, exported with no git history. Clone
   once per repository into `<root>/clones/<name>` (`git clone --filter=blob:none <url> <dir>`),
   then export with `git -C <clone> archive --format=tar --output=/tmp/<id>-<side>.tar <sha>` and
   `tar -xf /tmp/<id>-<side>.tar -C <gate>/<side>` (create the folder first with `mkdir -p`).
2. `change.diff`: `git -C <clone> diff <base> <head> --output=<gate>/change.diff`.
3. `CHANGE.md`: the head commit's title and message body exactly as committed
   (`git -C <clone> log -1 --format=%B <head>`), and, if the title carries a pull request number,
   the pull request's own title and description fetched with
   `gh api repos/<owner>/<repo>/pulls/<n> --jq .body`. Remove nothing the author wrote at the
   time. **Leave out** all review comments, later edits that mention a revert or a follow-up fix,
   labels, and links to later issues. If you cannot tell whether a sentence was added later, leave
   it out. Never write anything about what happened after the change.
4. `venv-base/` and `venv-head/`: `uv venv --python <version> <gate>/venv-<side>`, then install
   that side's tree editable with its test extras, pinned to the change's date:
   `uv pip install -p <gate>/venv-<side> -e <gate>/<side>[<extras>] --exclude-newer <head commit date>`
   plus `coverage pytest pytest-asyncio`. If the project is a monorepo, install the packages the
   diff touches (and what they need from the same repo) editable from that side's tree. If the
   build needs a version from git, use `env SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv pip install ...`.
5. A smoke check per side: write a tiny script that imports the changed modules and prints the
   file path of one of them; run it with each venv's python and confirm the path is inside that
   side's tree.
6. `SETUP.md`: the Python version, the exact install commands, anything that did not install, and
   **how to stand in for the model without a network**: look in the project's tests for a fake or
   test model, a mock client or a recorded-response helper, and name it with a five-line example.
   Facts only. Nothing about the change's quality or history.

## Shared environment mode (used when the task says so)

Disk is limited, so gates of one project share one environment where they can.

- Trees: export from the existing clone named in the task (do not clone again).
- `CHANGE.md`: `gh api repos/...` is blocked on this machine. Use the head commit's message only.
  If head is a merge commit, add the titles and bodies of the commits it merged
  (`git -C <clone> log --format=%s%n%b <base>..<head>`). Nothing else.
- Environment: `<root>/envs/<project>/` built once per project with the install commands given for
  the gate (they were recorded by someone who got the project's tests running), plus
  `coverage pytest pytest-asyncio`. Do not install the project itself into it. If it already
  exists, reuse it.
- Write `<gate>/gate.json`:
  `{"python": {"base": "<env>/bin/python", "head": "<env>/bin/python"},
    "pythonpath": {"base": ["<gate>/base/<source root>"], "head": ["<gate>/head/<source root>"]}}`
  (source root `.` means the tree itself). `run_probes.py` reads it.
- Smoke check: a script that imports the modules the diff touches and prints one module's file
  path (and exits 1 if that path is not under the folder named by the `PROBE_TREE` environment
  variable). Save it as `<gate>/probes/p_00_smoke.py`, run
  `python3 /home/user/flywheel/studies/change-probes/run_probes.py <gate> --reps 1`, and read
  `results.json`: the status must be `same` (passes on both sides, each from its own tree). Then
  delete the probe, `results.json` and `coverage.json`.
- If a side cannot import with the shared environment (dependencies changed between commits, or
  the project needs to be installed to work), build `venv-base/` and `venv-head/` for that gate
  as in steps 4 and 5 instead, and write no `gate.json`.
- `SETUP.md` lists the install commands and how probes reach the code (what is on the import
  path), and the model stand-in. Copy no remark from the install hints that mentions a test, a
  witness or what the change breaks.

Rules:

- The gate folder must contain no `.git`, no fix, no later commit, and no text from after the
  change. Do not copy the answer key or any labelling file into it.
- Do not run the project's full test suite. Do not fix failing installs by upgrading past the
  change's date; record what failed instead.
- When finished, report per gate: `ok` or what failed, in one line each.
