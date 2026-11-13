"""Replay: test a coding agent on real past changes from a repository's own history.

A case is one commit that changed code and added or changed tests. To replay it, the repository is
rewound to the commit's parent and copied without any history, so nothing after that point can be
read. An agent gets the commit message as its task and works in the copy. Then the commit's own
test files are put in place and run: the case passes when they pass.

A case is only used when it is fair: with the real change's tests, the code before the change fails
them for a reason a person could fix from the task (not a missing name), and the code after the
change passes them, both twice in a row.

Standard library only. The agent is the `claude` command line, run headless on the signed-in
subscription; no API key is read.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

# A failure of these kinds means the test needs a name the task never mentions, so no agent could
# be expected to pass it from the task text alone.
INTERFACE_ERRORS = re.compile(
    r"ImportError|ModuleNotFoundError|AttributeError|NameError|is not a function|"
    r"Cannot find module|is not defined|has no attribute|unexpected keyword argument|"
    r"takes \d+ positional argument|ERR_MODULE_NOT_FOUND"
)
FIX_WORDS = re.compile(r"\b(fix|fixes|fixed|bug|regression|revert|broke|crash|wrong)\b", re.I)


@dataclass(frozen=True)
class RepoSpec:
    """How to find and test one repository."""

    name: str
    path: str
    test_command: str  # `{tests}` becomes the case's test files; may be unused
    code_globs: tuple[str, ...]
    test_globs: tuple[str, ...]
    env: dict[str, str] = field(default_factory=dict)  # `{work}` becomes the working copy
    agent_path: str = ""  # a folder put first on PATH for the agent, so `python` has the deps

    @staticmethod
    def load(path: Path) -> list[RepoSpec]:
        """Read a list of repository specs from a JSON file."""
        out = []
        for d in json.loads(path.read_text()):
            out.append(
                RepoSpec(
                    d["name"],
                    d["path"],
                    d["test_command"],
                    tuple(d["code_globs"]),
                    tuple(d["test_globs"]),
                    d.get("env", {}),
                    d.get("agent_path", ""),
                )
            )
        return out


@dataclass(frozen=True)
class Case:
    """One real change to replay."""

    repo: str
    fix: str
    parent: str
    subject: str
    task: str
    tests: tuple[str, ...]
    code: tuple[str, ...]
    lines: int

    @property
    def id(self) -> str:
        """A short stable name: repository and the first ten characters of the commit."""
        return f"{self.repo}-{self.fix[:10]}"


def _git(root: str | Path, *args: str, check: bool = True) -> str:
    """Run git in `root` and return its standard output."""
    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if check and done.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()[:300]}")
    return done.stdout


def _matches(path: str, globs: Iterable[str]) -> bool:
    """True when `path` matches any glob (`**` crosses folders)."""
    from fnmatch import fnmatch

    return any(fnmatch(path, g) or fnmatch(path, g.replace("**/", "")) for g in globs)


def task_text(message: str) -> str:
    """The commit message as a task: subject and body, without trailers or sha lines."""
    keep = []
    for line in message.strip().splitlines():
        if re.match(r"^(Co-authored-by|Signed-off-by|Claude-Session):", line, re.I):
            continue
        keep.append(line)
    return "\n".join(keep).strip()


def mine(
    spec: RepoSpec,
    *,
    since: str,
    max_lines: int = 600,
    fixes_only: bool = True,
) -> list[Case]:
    """Commits since a date that change code and tests together, oldest last."""
    log = _git(
        spec.path,
        "log",
        "--no-merges",
        f"--since={since}",
        "--format=@@%H%x1f%P%x1f%s%x1f%B%x1e",
        "--numstat",
    )
    cases = []
    for block in log.split("@@")[1:]:
        head, _, stats = block.partition("\x1e")
        sha, parents, subject, body = head.split("\x1f", 3)
        parent_list = parents.split()
        if len(parent_list) != 1:
            continue
        files, lines = [], 0
        for row in stats.strip().splitlines():
            parts = row.split("\t")
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                files.append(parts[2])
                lines += int(parts[0]) + int(parts[1])
        tests = tuple(f for f in files if _matches(f, spec.test_globs))
        code = tuple(
            f for f in files if _matches(f, spec.code_globs) and not _matches(f, spec.test_globs)
        )
        if not tests or not code or lines > max_lines:
            continue
        if fixes_only and not FIX_WORDS.search(subject):
            continue
        cases.append(
            Case(spec.name, sha, parent_list[0], subject, task_text(body), tests, code, lines)
        )
    return cases


def materialize(spec: RepoSpec, case: Case, dest: Path, *, at: str, tests: bool) -> None:
    """Write the repository as it was at `at` ("parent" or "fix") into `dest`, with no history.

    With `tests`, the real change's test files are copied over from the fix commit.
    """
    dest.mkdir(parents=True, exist_ok=True)
    rev = case.parent if at == "parent" else case.fix
    archive = subprocess.run(
        ["git", "-C", spec.path, "archive", rev], capture_output=True, check=True
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    if tests:
        overlay_tests(spec, case, dest)


def overlay_tests(spec: RepoSpec, case: Case, dest: Path) -> None:
    """Copy the fix commit's version of each of the case's test files into `dest`."""
    for rel in case.tests:
        shown = subprocess.run(
            ["git", "-C", spec.path, "show", f"{case.fix}:{rel}"], capture_output=True
        )
        if shown.returncode:
            continue  # the change deleted this test file
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(shown.stdout)


def snapshot(work: Path) -> None:
    """Make `work` a one-commit git repository, so the agent can diff its own changes."""
    for args in (
        ["init", "-q"],
        ["config", "user.email", "replay@example.invalid"],
        ["config", "user.name", "replay"],
        ["add", "-A"],
        ["commit", "-q", "-m", "snapshot", "--no-gpg-sign"],
    ):
        subprocess.run(["git", "-C", str(work), *args], capture_output=True, check=False)


def run_tests(spec: RepoSpec, case: Case, work: Path, timeout: int = 300) -> tuple[bool, str]:
    """Run the repository's tests on the case's test files in `work`; True when they pass."""
    existing = [t for t in case.tests if (work / t).exists()]
    cmd = spec.test_command.format(tests=" ".join(shlex.quote(t) for t in existing))
    env = {**os.environ, **{k: v.format(work=work) for k, v in spec.env.items()}}
    try:
        done = subprocess.run(
            cmd,
            shell=True,  # the command is the repository spec's own, written by the owner
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    out = (done.stdout + done.stderr)[-4000:]
    return done.returncode == 0, out


def check_fair(spec: RepoSpec, case: Case, scratch: Path) -> dict:
    """Decide whether a case can be used: fails before for a fixable reason, passes after."""
    result: dict = {"id": case.id, "fair": False, "reason": ""}
    before = []
    for i in range(2):
        w = scratch / f"{case.id}-before-{i}"
        materialize(spec, case, w, at="parent", tests=True)
        before.append(run_tests(spec, case, w))
        shutil.rmtree(w, ignore_errors=True)
    if any(ok for ok, _ in before):
        result["reason"] = "the tests already pass before the change"
        return result
    if any(INTERFACE_ERRORS.search(out) for _, out in before):
        result["reason"] = "the tests need a name or option the task does not give"
        result["before_tail"] = before[0][1][-400:]
        return result
    after = []
    for i in range(2):
        w = scratch / f"{case.id}-after-{i}"
        materialize(spec, case, w, at="fix", tests=False)
        after.append(run_tests(spec, case, w))
        shutil.rmtree(w, ignore_errors=True)
    if not all(ok for ok, _ in after):
        result["reason"] = "the tests do not pass after the real change (or they are flaky)"
        result["after_tail"] = after[0][1][-400:]
        return result
    result.update(fair=True, reason="ok")
    return result


PROMPT = """You are working in a copy of a software repository. Make the change described below \
in the working tree. Run the repository's existing tests and any checks you can to verify your \
work. Do not ask questions; finish when the change is complete.

Task:
{task}
"""

# What the agent may do without asking: read, search and edit files in the copy, and run tests and
# read-only commands. Anything else is refused, since nobody is there to approve it.
ALLOWED_TOOLS = (
    "Read",
    "Edit",
    "Write",
    "Glob",
    "Grep",
    "Bash(python:*)",
    "Bash(python3:*)",
    "Bash(pytest:*)",
    "Bash(node:*)",
    "Bash(ls:*)",
    "Bash(cat:*)",
    "Bash(grep:*)",
    "Bash(find:*)",
    "Bash(git diff:*)",
    "Bash(git status:*)",
)

# Paths and commands that would let an agent look at the real history or the network.
LEAK = re.compile(r"git (fetch|pull|clone|remote)|curl |wget |github\.com")


def _flags(events: list[dict], work: Path, repo_path: str) -> list[str]:
    """Tool calls that went outside the working copy or touched history: contamination flags."""
    flags = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") != "tool_use":
                continue
            blob = json.dumps(block.get("input", {}))
            if repo_path and repo_path in blob:
                flags.append(f"touched the source repository: {blob[:120]}")
            elif LEAK.search(blob):
                flags.append(f"history or network: {blob[:120]}")
    return flags


def run_agent(
    spec: RepoSpec,
    case: Case,
    *,
    model: str,
    rep: int,
    out_dir: Path,
    timeout: int = 900,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    claude: str = "claude",
) -> dict:
    """One replay: the agent works on the rewound copy, then the real tests judge it."""
    out_file = out_dir / f"{case.id}__{model}__{rep}.json"
    if out_file.exists():
        return json.loads(out_file.read_text())
    work = Path(tempfile.mkdtemp(prefix=f"replay-{case.id}-"))
    started = time.time()
    record: dict = {"case": case.id, "model": model, "rep": rep}
    try:
        materialize(spec, case, work, at="parent", tests=False)
        snapshot(work)
        cmd = [
            claude,
            "-p",
            PROMPT.format(task=case.task),
            "--model",
            model,
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            *ALLOWED_TOOLS,
            "--no-session-persistence",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--disallowedTools",
            "WebFetch",
            "WebSearch",
            "Agent",
        ]
        try:
            env = {**os.environ, **{k: v.format(work=work) for k, v in spec.env.items()}}
            if spec.agent_path:
                env["PATH"] = os.path.expandvars(spec.agent_path) + os.pathsep + env.get("PATH", "")
            done = runner(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=timeout)
            stdout, error = done.stdout, done.returncode != 0
        except subprocess.TimeoutExpired as exc:
            stdout, error = (exc.stdout or "") if isinstance(exc.stdout, str) else "", True
            record["timed_out"] = True
        events = []
        for line in stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        final = next((e for e in reversed(events) if e.get("type") == "result"), {})
        usage = final.get("usage", {})
        record.update(
            seconds=round(time.time() - started),
            turns=final.get("num_turns"),
            tokens=sum(
                usage.get(k, 0)
                for k in (
                    "input_tokens",
                    "output_tokens",
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                )
            ),
            agent_error=bool(final.get("is_error")) or (error and not final),
            flags=_flags(events, work, str(Path(spec.path).resolve())),
        )
        changed = _git(work, "status", "--porcelain", check=False).strip().splitlines()
        record["files_changed"] = len(changed)
        overlay_tests(spec, case, work)
        ok, tail = run_tests(spec, case, work)
        record["passed"] = bool(ok) and not record["agent_error"]
        if not ok:
            record["fail_tail"] = tail[-600:]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(record, indent=1))
    return record


def run_all(
    specs: dict[str, RepoSpec],
    cases: list[Case],
    models: list[str],
    reps: int,
    out_dir: Path,
    workers: int = 3,
    progress: Callable[[dict], None] | None = None,
) -> list[dict]:
    """Run every (case, model, repeat) with a few at a time; finished ones are skipped."""
    jobs = [(c, m, r) for c in cases for m in models for r in range(reps)]
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(run_agent, specs[c.repo], c, model=m, rep=r, out_dir=out_dir)
            for c, m, r in jobs
        ]
        for future in as_completed(futures):
            record = future.result()
            results.append(record)
            if progress:
                progress(record)
    return results


def wilson(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """A 95% interval for a pass rate."""
    if not total:
        return (0.0, 0.0)
    p = passed / total
    d = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / d
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def summarize(results: list[dict]) -> dict[str, dict]:
    """Per model: runs, passes, pass rate with interval, mean tokens and seconds, flagged runs."""
    out: dict[str, dict] = {}
    for model in sorted({r["model"] for r in results}):
        rows = [r for r in results if r["model"] == model]
        clean = [r for r in rows if not r.get("flags")]
        passed = sum(1 for r in clean if r.get("passed"))
        low, high = wilson(passed, len(clean))
        out[model] = {
            "runs": len(rows),
            "flagged": len(rows) - len(clean),
            "scored": len(clean),
            "passed": passed,
            "rate": passed / len(clean) if clean else None,
            "low": low,
            "high": high,
            "mean_tokens": round(sum(r.get("tokens") or 0 for r in clean) / max(1, len(clean))),
            "mean_seconds": round(sum(r.get("seconds") or 0 for r in clean) / max(1, len(clean))),
        }
    return out


def per_case(results: list[dict]) -> dict[str, dict[str, str]]:
    """For each case and model, the passes out of runs, such as '2/3'."""
    table: dict[str, dict[str, str]] = {}
    for r in results:
        cell = table.setdefault(r["case"], {})
        a, b = (int(x) for x in cell.get(r["model"], "0/0").split("/"))
        cell[r["model"]] = f"{a + (1 if r.get('passed') and not r.get('flags') else 0)}/{b + 1}"
    return table


def to_markdown(results: list[dict]) -> str:
    """The pass-rate table and the per-case grid."""
    summary = summarize(results)
    lines = [
        "| Model | Scored runs | Passed | Pass rate (95% interval) | Mean tokens | Mean seconds "
        "| Flagged and left out |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for model, s in summary.items():
        rate = (
            "n/a" if s["rate"] is None else f"{s['rate']:.0%} ({s['low']:.0%} to {s['high']:.0%})"
        )
        lines.append(
            f"| {model} | {s['scored']} | {s['passed']} | {rate} | {s['mean_tokens']:,} "
            f"| {s['mean_seconds']} | {s['flagged']} |"
        )
    models = list(summary)
    lines += [
        "",
        "| Case | " + " | ".join(models) + " |",
        "| --- | " + " | ".join("---" for _ in models) + " |",
    ]
    for case, cell in sorted(per_case(results).items()):
        lines.append(f"| {case} | " + " | ".join(cell.get(m, "") for m in models) + " |")
    return "\n".join(lines)


def save_cases(path: Path, cases: list[Case]) -> None:
    """Write cases as JSON."""
    path.write_text(json.dumps([asdict(c) for c in cases], indent=1))


def load_cases(path: Path) -> list[Case]:
    """Read cases written by `save_cases`."""
    out = []
    for d in json.loads(path.read_text()):
        d["tests"], d["code"] = tuple(d["tests"]), tuple(d["code"])
        out.append(Case(**d))
    return out
