"""Run one gate: the frozen cases on the base and the head, extra runs on close calls, then decide.

    python run_gate.py <project> <gate-id> <base_env> <head_env> [--label-suffix S]

The gate's folder is copied out of the case writers' workspace into runs/<project>/ first, and the
sha256 of every file in it is written to freeze.json before any model call, so the cases that ran
are provably the ones written blind. Base and head run side by side, so time-of-day changes in
the model service hit both equally. Runs that failed in the model endpoint rather than in the
agent are removed and run again (transport.py), on whichever side they happened.
"""

import hashlib
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transport import clean  # noqa: E402

BLIND = Path("/tmp/rr/blind")
RUNS = Path(__file__).resolve().parent / os.environ.get("RR_RUNS", "runs")
CONCURRENCY = "2"


def freeze(project: str, gid: str, dest: Path) -> None:
    """Copy the gate and its suite out of the writers' workspace and hash every file."""
    if (dest / gid / "freeze.json").exists():
        return
    shutil.copytree(BLIND / project / gid, dest / gid, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("smoke*", "__pycache__", "*.pyc"))
    shutil.copytree(BLIND / project / "suite", dest / "suite", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("smoke*", "__pycache__", "*.pyc"))
    files = sorted(p for p in (dest / gid).rglob("*") if p.is_file()) + sorted(
        p for p in (dest / "suite").rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    (dest / gid / "freeze.json").write_text(json.dumps(
        {str(p.relative_to(dest)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=1))


def run_sides(g: Path, jobs: list[tuple[str, str, list[str]]]) -> None:
    """Run several `flywheel run` jobs in parallel: (env, out file, extra args)."""
    procs = []
    for env, out, extra in jobs:
        if (g / out).exists():
            continue
        f = (g / out.replace(".json", ".log")).open("a")
        procs.append(subprocess.Popen([f"{env}/bin/flywheel", "run", "--label", out.split(".")[0], "--out", out,
                                       "--concurrency", CONCURRENCY, *extra], cwd=g, stdout=f,
                                      stderr=subprocess.STDOUT))
    for p in procs:
        p.wait()


def next_rep(g: Path, files: list[str]) -> int:
    """The first repetition number not used yet on this side."""
    reps = [r["repetition"] for f in files if (g / f).exists() for r in json.loads((g / f).read_text())["runs"]]
    return max(reps, default=0) + 1


def top_up(g: Path, side: str, env: str, files: list[str]) -> list[str]:
    """Replace transport-failed runs on one side, up to three rounds; return the side's files."""
    log = []
    for round_ in range(1, 4):
        owed = clean([g / f for f in files], g / f"{side}.clean.json")
        if not owed:
            break
        log.append(owed)
        out = f"{side}-t{round_}.json"
        run_sides(g, [(env, out, ["--only", ",".join(owed), "--repetitions", str(max(owed.values())),
                                   "--first-repetition", str(next_rep(g, files))])])
        files.append(out)
    clean([g / f for f in files], g / f"{side}.clean.json")
    (g / f"transport-{side}.json").write_text(json.dumps(log))
    return files


def timeout_pass(g: Path, side: str, env: str, files: list[str]) -> list[str]:
    """Rerun each TimeoutError run once; a second timeout stands and is scored (Amendment 3)."""
    if (g / f"timeout-{side}.json").exists():
        return files
    tos = [(r["example_id"], r["repetition"]) for f in files if (g / f).exists()
           for r in json.loads((g / f).read_text())["runs"] if "timeout" in str(r.get("error") or "").lower()]
    if tos:
        owed: dict[str, int] = {}
        for cid, _ in tos:
            owed[cid] = owed.get(cid, 0) + 1
        kept = []
        for f in files:  # the same files without the timed-out runs
            e = json.loads((g / f).read_text())
            e["runs"] = [r for r in e["runs"] if (r["example_id"], r["repetition"]) not in tos]
            (g / f.replace(".json", ".nt.json")).write_text(json.dumps(e))
            kept.append(f.replace(".json", ".nt.json"))
        out = f"{side}-to.json"
        run_sides(g, [(env, out, ["--only", ",".join(owed), "--repetitions", str(max(owed.values())),
                                   "--first-repetition", str(next_rep(g, files))])])
        e = json.loads((g / out).read_text())
        seen: dict[str, int] = {}
        runs = []
        for r in e["runs"]:  # keep exactly as many reruns as there were timeouts per case
            if seen.get(r["example_id"], 0) < owed[r["example_id"]]:
                seen[r["example_id"]] = seen.get(r["example_id"], 0) + 1
                runs.append(r)
        e["runs"] = runs
        (g / f"{side}-to.trim.json").write_text(json.dumps(e))
        files = [*kept, f"{side}-to.trim.json"]
        clean([g / f for f in files], g / f"{side}.clean.json")
    (g / f"timeout-{side}.json").write_text(json.dumps({"rerun": [list(t) for t in tos]}))
    return files


def main() -> None:
    """Copy, freeze, run both sides, replace transport failures, rerun close calls, gate."""
    project, gid, base_env, head_env = sys.argv[1:5]
    dest = RUNS / project
    freeze(project, gid, dest)
    g = dest / gid
    run_sides(g, [(base_env, "base.json", []), (head_env, "head.json", [])])
    bases = top_up(g, "base", base_env, ["base.json"])
    heads = top_up(g, "head", head_env, ["head.json"])
    if not (g / "close.json").exists():
        out = subprocess.run([f"{base_env}/bin/flywheel", "close-calls", "--base", "base.clean.json",
                              "--head", "head.clean.json"], cwd=g, capture_output=True, text=True, check=True).stdout
        (g / "close.json").write_text(out)
    close = json.loads((g / "close.json").read_text())
    if close["ids"]:
        args = ["--only", ",".join(close["ids"]), "--repetitions", str(close["repetitions"])]
        run_sides(g, [(base_env, "base-extra.json", [*args, "--first-repetition", str(next_rep(g, bases))]),
                      (head_env, "head-extra.json", [*args, "--first-repetition", str(next_rep(g, heads))])])
        bases = top_up(g, "base", base_env, [*bases, "base-extra.json"])
        heads = top_up(g, "head", head_env, [*heads, "head-extra.json"])
    if os.environ.get("RR_TIMEOUT_RERUN", "1") == "1":
        bases = timeout_pass(g, "base", base_env, bases)
        heads = timeout_pass(g, "head", head_env, heads)
    with (g / "run.log").open("a") as f:
        code = subprocess.run([f"{base_env}/bin/flywheel", "gate", "--base", "base.clean.json", "--head",
                               "head.clean.json", "--report", "gate.md"], cwd=g, stdout=f,
                              stderr=subprocess.STDOUT, check=False).returncode
    (g / "verdict.json").write_text(json.dumps({"gate": gid, "exit": code, "blocked": code == 1}))
    print(gid, "BLOCKED" if code == 1 else ("PASS" if code == 0 else f"exit {code}"), flush=True)


if __name__ == "__main__":
    main()
