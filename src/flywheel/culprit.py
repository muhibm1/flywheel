"""Find the change that introduced a reported bug, by proof, and score the answers.

    flywheel culprit trace <case> [--reps 3] [--timeout 180]
    flywheel culprit trace <case> --at good|bad|<sha>     run the probe once at one commit
    flywheel culprit score <key.json> <SET> <cases_dir> [--answers file] [--out file]

A case folder holds:
  case.json   {"repo": path to a clone with history, "good": sha where the behaviour worked,
               "bad": sha where the bug shows, "python": interpreter with the project's
               dependencies, "source_roots": [folders inside the tree to put on the import path]}
  probe.py    the reproduction. Exit 0 = the behaviour works. Exit 1 = the reported bug shows.
              Exit 125 (or anything else) = this commit cannot be judged (setup trouble).

The tool checks the probe passes at `good` and fails at `bad`, then bisects the first-parent
history between them. No model takes part: the answer is the first commit at which the probe
fails while it passes at that commit's parent. The result goes to result.json:
  status   found | ambiguous | invalid_probe
  culprit  the commit (found), with `candidates` listing the commits that could not be told
           apart when some could not be judged (ambiguous)

Scoring: without --answers, each case's result.json is scored. With --answers, a JSON file
{gate_id: sha} is scored instead. A case is correct when the named commit is the one that brought
the introducing change into the first-parent history: the introducing commit itself, or the merge
commit that merged it. In git terms: the introducing commit is an ancestor of the answer and not
of the answer's first parent. An ambiguous or invalid result is wrong.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

SECRET_WORDS = ("API_KEY", "TOKEN", "SECRET", "LANGSMITH", "LANGCHAIN_", "ANTHROPIC", "OPENAI")
GOOD, BAD, SKIP = "good", "bad", "skip"
MEM_LIMIT_GB = 6


def _limits() -> None:
    """Cap a probe's memory so a runaway probe fails alone instead of taking the machine down."""
    import resource

    cap = MEM_LIMIT_GB * 1024**3
    with contextlib.suppress(ValueError, OSError):
        resource.setrlimit(resource.RLIMIT_DATA, (cap, cap))


def run_cmd(cmd: list[str], cwd: Path, timeout: int, env: dict[str, str]) -> dict:
    """Run one probe process and return its exit code and output tail, killing it on timeout."""
    import signal

    with tempfile.TemporaryFile() as out:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=out,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            preexec_fn=_limits,
        )
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            return {"exit": "timeout", "tail": f"timed out after {timeout}s"}
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)  # stray children of a finished probe
        size = out.seek(0, 2)
        out.seek(max(0, size - 6000))
        return {"exit": code, "tail": out.read().decode("utf-8", "replace")[-1500:]}


def git(repo: str, *args: str) -> str:
    """Run one git command in a repository and return its trimmed output."""
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


def export_tree(repo: str, sha: str, dest: Path) -> None:
    """Write the source tree of one commit into dest, without touching the clone's work tree."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    p = subprocess.run(["git", "-C", repo, "archive", "--format=tar", sha], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"git archive {sha}: {p.stderr.decode('utf-8', 'replace')[:300]}")
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as tf:
        tf.extractall(dest, filter="tar")


def probe_env(tree: Path, roots: list[str]) -> dict[str, str]:
    """The environment a probe runs in: secrets removed, the tree's source roots on the path."""
    env = dict(os.environ)
    for name in list(env):
        if any(t in name.upper() for t in SECRET_WORDS):
            env.pop(name)
    env["PROBE_TREE"] = str(tree)
    env["PYTHONPATH"] = os.pathsep.join(
        str(tree / r) if r not in ("", ".") else str(tree) for r in roots
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["LANGSMITH_TRACING"] = "false"
    env["LANGCHAIN_TRACING_V2"] = "false"
    return env


class Tracer:
    """Bisects the first-parent history of a case to the commit that introduced the bug."""

    def __init__(self, case: Path, reps: int, timeout: int):
        """Load the case folder's case.json and set the repetitions and timeout per probe run."""
        self.case = case
        self.cfg = json.loads((case / "case.json").read_text())
        self.reps, self.timeout = reps, timeout
        self.probe = case / "probe.py"
        self.tested: dict[str, dict] = {}

    def judge(self, sha: str, reps: int | None = None) -> str:
        """Run the probe at one commit: good if every run exits 0, bad if every run exits 1."""
        if sha in self.tested:
            return self.tested[sha]["state"]
        tree = self.case / "trees" / sha[:12]
        export_tree(self.cfg["repo"], sha, tree)
        env = probe_env(tree, self.cfg.get("source_roots") or ["."])
        # A project's dependencies drift over a long window. `python_fallbacks` lists further
        # interpreters; a version that cannot be judged under one is tried under the next, and the
        # first clear verdict stands.
        for python in [self.cfg["python"], *(self.cfg.get("python_fallbacks") or [])]:
            runs = [
                run_cmd([python, str(self.probe)], tree, self.timeout, env)
                for _ in range(reps or self.reps)
            ]
            exits = [r["exit"] for r in runs]
            state = (
                GOOD if all(e == 0 for e in exits) else BAD if all(e == 1 for e in exits) else SKIP
            )
            if state != SKIP:
                break
        shutil.rmtree(tree, ignore_errors=True)
        self.tested[sha] = {"state": state, "exits": exits, "tail": runs[-1]["tail"][-600:]}
        return state

    def run(self) -> dict:
        """Check the probe at both ends, bisect between them, and return the result."""
        good, bad = self.cfg["good"], self.cfg["bad"]
        chain = git(
            self.cfg["repo"], "rev-list", "--first-parent", "--reverse", f"{good}..{bad}"
        ).split()
        g, b = self.judge(good), self.judge(bad)
        if g != GOOD or b != BAD:
            return {
                "status": "invalid_probe",
                "good_state": g,
                "bad_state": b,
                "good_tail": self.tested[good]["tail"],
                "bad_tail": self.tested[bad]["tail"],
            }
        # commits[i] for i in 0..n-1; index -1 is `good`. Invariant: lo is good, hi is bad.
        lo, hi = -1, len(chain) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            order = sorted(range(lo + 1, hi), key=lambda i: abs(i - mid))
            for i in order:
                s = self.judge(chain[i])
                if s == GOOD:
                    lo = i
                    break
                if s == BAD:
                    hi = i
                    break
            else:
                break  # every commit strictly between lo and hi could not be judged
        cands = chain[lo + 1 : hi + 1]
        out = {
            "status": "found" if len(cands) == 1 else "ambiguous",
            "culprit": chain[hi],
            "candidates": cands,
            "parent_state": GOOD,
            "window": len(chain),
            "commits_tested": len(self.tested),
        }
        return out


def trace(case_dir: str, reps: int = 3, timeout: int = 180, at: str | None = None) -> int:
    """Trace one case folder, print what the study script printed and write result.json."""
    case = Path(case_dir).resolve()
    t = Tracer(case, reps, timeout)
    if at:
        sha = t.cfg.get(at, at)
        state = t.judge(sha, reps=1)
        r = t.tested[sha]
        print(f"{at}: {state} exit={r['exits']}")
        print(r["tail"])
        return 0
    out = t.run()
    out["tested"] = {
        k[:12]: {"state": v["state"], "exits": v["exits"]} for k, v in t.tested.items()
    }
    (case / "result.json").write_text(json.dumps(out, indent=1))
    shown = {k: v for k, v in out.items() if k not in ("tested", "culprit", "candidates")}
    print(json.dumps(shown, indent=1))
    return 0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def is_anc(repo: str, a: str, b: str) -> bool:
    """Whether commit a is an ancestor of commit b."""
    return (
        subprocess.run(
            ["git", "-C", repo, "merge-base", "--is-ancestor", a, b], capture_output=True
        ).returncode
        == 0
    )


def is_correct(repo: str, intro: str, sha: str) -> bool:
    """Whether sha is the introducing commit or the first-parent commit that brought it in."""
    known = (
        subprocess.run(
            ["git", "-C", repo, "cat-file", "-e", sha + "^{commit}"], capture_output=True
        ).returncode
        == 0
    )
    return known and is_anc(repo, intro, sha) and not is_anc(repo, intro, sha + "~1")


def score(
    key: str,
    set_name: str,
    cases: str,
    answers_file: str | None = None,
    out_file: str | None = None,
) -> int:
    """Score the cases of one set against the sealed key and print the summary."""
    rows = [
        r
        for r in json.loads(Path(key).read_text())
        if r["set"] == set_name and r["kind"] == "regression"
    ]
    answers = json.loads(Path(answers_file).read_text()) if answers_file else None
    right, wrong, detail = [], [], {}
    for r in sorted(rows, key=lambda x: x["gate_id"]):
        gid, intro = r["gate_id"], r["row"]["intro_sha"]
        case = Path(cases) / gid
        cfg = (
            json.loads((case / "case.json").read_text()) if (case / "case.json").exists() else None
        )
        if cfg is None:
            wrong.append(gid)
            detail[gid] = "no case"
            continue
        if answers is not None:
            sha, status = answers.get(gid), "answered" if answers.get(gid) else "no answer"
        else:
            res = (
                json.loads((case / "result.json").read_text())
                if (case / "result.json").exists()
                else {}
            )
            status = res.get("status", "no result")
            sha = res.get("culprit") if status == "found" else None
        ok = bool(sha) and is_correct(cfg["repo"], intro, sha)
        (right if ok else wrong).append(gid)
        detail[gid] = "correct" if ok else f"wrong ({status})"
    n = len(rows)
    lo, hi = wilson(len(right), n)
    print(
        f"{set_name}: correct culprit {len(right)}/{n} = {100 * len(right) / max(n, 1):.1f}% "
        f"(95% interval {100 * lo:.1f} to {100 * hi:.1f})"
    )
    print("  wrong:", " ".join(f"{g}[{detail[g]}]" for g in wrong) or "none")
    if out_file:
        Path(out_file).write_text(
            json.dumps(
                {"set": set_name, "n": n, "correct": right, "wrong": wrong, "detail": detail},
                indent=1,
            )
        )
    return 0


def add_trace_args(ap: argparse.ArgumentParser) -> None:
    """Add the arguments of the trace command to a parser."""
    ap.add_argument("case")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--at")


def add_score_args(ap: argparse.ArgumentParser) -> None:
    """Add the arguments of the score command to a parser."""
    ap.add_argument("key")
    ap.add_argument("set_name", metavar="SET")
    ap.add_argument("cases")
    ap.add_argument("--answers")
    ap.add_argument("--out")


def trace_main(argv: list[str] | None = None) -> int:
    """Command line entry point of the trace script."""
    ap = argparse.ArgumentParser()
    add_trace_args(ap)
    a = ap.parse_args(argv)
    return trace(a.case, a.reps, a.timeout, a.at)


def score_main(argv: list[str] | None = None) -> int:
    """Command line entry point of the score script."""
    ap = argparse.ArgumentParser()
    add_score_args(ap)
    a = ap.parse_args(argv)
    return score(a.key, a.set_name, a.cases, a.answers, a.out)


if __name__ == "__main__":
    sys.exit(trace_main())
