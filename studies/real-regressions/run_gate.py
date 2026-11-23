"""Run one gate: the frozen cases on the base and the head, extra runs on close calls, then decide.

    python run_gate.py <project> <gate-id> <base_env> <head_env>

The gate's folder is copied out of the case writers' workspace into runs/<project>/ first, and the
sha256 of every file in it is written to freeze.json before any model call, so the cases that ran
are provably the ones written blind. Base and head run side by side, so time-of-day changes in
the model service hit both equally.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

BLIND = Path("/tmp/rr/blind")
RUNS = Path(__file__).resolve().parent / "runs"
CONCURRENCY = "2"


def sh(args: list[str], cwd: Path, log: Path) -> int:
    """Run a command, appending its output to `log`."""
    with log.open("a") as f:
        f.write("$ " + " ".join(args) + "\n")
        f.flush()
        return subprocess.run(args, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, check=False).returncode


def main() -> None:
    """Copy, freeze, run both sides, rerun close calls, gate."""
    project, gid, base_env, head_env = sys.argv[1:5]
    src = BLIND / project
    dest = RUNS / project
    if not (dest / gid / "freeze.json").exists():
        shutil.copytree(src, dest, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("smoke*", "__pycache__", "*.pyc"))
        # Only this gate's folder and the shared suite are kept; other gates stay where they are.
        for other in dest.iterdir():
            if other.is_dir() and other.name not in (gid, "suite") and other.name.startswith(project + "-g"):
                if not (other / "freeze.json").exists():
                    shutil.rmtree(other)
        files = sorted(p for p in (dest / gid).rglob("*") if p.is_file()) + sorted(
            p for p in (dest / "suite").rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        (dest / gid / "freeze.json").write_text(json.dumps(
            {str(p.relative_to(dest)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=1))
    g = dest / gid
    log = g / "run.log"
    procs = []
    for label, env in (("base", base_env), ("head", head_env)):
        if not (g / f"{label}.json").exists():
            f = (g / f"{label}.log").open("a")
            procs.append(subprocess.Popen([f"{env}/bin/flywheel", "run", "--label", label, "--out", f"{label}.json",
                                           "--concurrency", CONCURRENCY], cwd=g, stdout=f, stderr=subprocess.STDOUT))
    for p in procs:
        p.wait()
    bases, heads = ["base.json"], ["head.json"]
    if not (g / "close.json").exists():
        out = subprocess.run([f"{base_env}/bin/flywheel", "close-calls", "--base", "base.json", "--head", "head.json"],
                             cwd=g, capture_output=True, text=True, check=True).stdout
        (g / "close.json").write_text(out)
    close = json.loads((g / "close.json").read_text())
    if close["ids"]:
        procs = []
        for label, env in (("base", base_env), ("head", head_env)):
            out = f"{label}-extra.json"
            if not (g / out).exists():
                f = (g / f"{label}-extra.log").open("a")
                procs.append(subprocess.Popen(
                    [f"{env}/bin/flywheel", "run", "--label", label, "--out", out, "--concurrency", CONCURRENCY,
                     "--only", ",".join(close["ids"]), "--repetitions", str(close["repetitions"]),
                     "--first-repetition", str(close["first_repetition"])], cwd=g, stdout=f, stderr=subprocess.STDOUT))
        for p in procs:
            p.wait()
        bases.append("base-extra.json")
        heads.append("head-extra.json")
    code = sh([f"{base_env}/bin/flywheel", "gate", "--base", *bases, "--head", *heads, "--report", "gate.md"], g, log)
    (g / "verdict.json").write_text(json.dumps({"gate": gid, "exit": code, "blocked": code == 1}))
    print(gid, "BLOCKED" if code == 1 else ("PASS" if code == 0 else f"exit {code}"))


if __name__ == "__main__":
    main()
