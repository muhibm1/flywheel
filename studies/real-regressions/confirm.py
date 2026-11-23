"""Reproduction rule (Amendment 4), part of the gate: python confirm.py <runs-dir> <gate> [<gate> ...]

For a gate that blocked, rerun only its broken cases, 3 runs each, on base twice (base-a, base-b)
and head once (head-a), in <gate>/confirm/. For each arm, a broken case that also
breaks base-b against base-a is noise and is dropped; the block stands only if Flywheel's gate
still blocks head-a against base-a on the arm's remaining broken cases.
A gate that passed is left as it is. Writes <gate>/confirm/result.json.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ARMS = {"arm2": {"standing"}, "arm3": {"standing", "change"}, "arm4": {"standing", "change", "diff"},
        "arm5": {"standing", "change", "diff", "fault"}, "arm6": {"standing", "change", "sweep"}}


def flywheel(env: str, cwd: Path, *args: str, log: Path | None = None) -> int:
    """Run a flywheel command; its exit code."""
    out = log.open("w") if log else subprocess.DEVNULL
    return subprocess.run([f"{env}/bin/flywheel", *args], cwd=cwd, stdout=out, stderr=subprocess.STDOUT,
                          check=False).returncode


def filtered(src: Path, dst: Path, ids: set[str]) -> None:
    """Copy a run file keeping only the given case ids."""
    e = json.loads(src.read_text())
    e["runs"] = [r for r in e["runs"] if r["example_id"] in ids]
    e["examples"] = {k: v for k, v in e["examples"].items() if k in ids}
    dst.write_text(json.dumps(e))


def confirm(runs: Path, gid: str, reuse: bool = False) -> dict:
    """Confirm or clear one gate's block, per arm."""
    g = runs / gid.rsplit("-g", 1)[0] / gid
    gate = json.loads((g / "gate.json").read_text())
    verdict = json.loads((g / "verdict.json").read_text())
    if not verdict.get("blocked"):
        return {"gate": gid, "blocked": False}
    report = (g / "gate.md").read_text()
    broken_text = report.split("### Broken", 1)[1].split("\n### ", 1)[0] if "### Broken" in report else ""
    broken = set(re.findall(r"^- `([^`]+)`", broken_text, re.M))
    src = {}
    for line in (g / "dataset.jsonl").read_text().splitlines():
        if line.strip():
            c = json.loads(line)
            src[c["id"]] = (c.get("metadata") or {}).get("source", "standing")
    a = g / "confirm"
    a.mkdir(exist_ok=True)
    if (g.parent / "suite").exists() and not (g / "suite").exists():  # shims import ../suite/adapter.py
        (g / "suite").symlink_to((g.parent / "suite").resolve())
    for f in g.iterdir():
        if f.name in ("flywheel.toml", "dataset.jsonl") or f.suffix == ".py":
            (a / f.name).write_bytes(f.read_bytes())
    procs = []
    for env, out in () if reuse and (a / "base-b.json").exists() else ((gate["base_env"], "base-a.json"), (gate["head_env"], "head-a.json"), (gate["base_env"], "base-b.json")):
        procs.append(subprocess.Popen([f"{env}/bin/flywheel", "run", "--label", out[:-5], "--out", out, "--only",
                                       ",".join(sorted(broken)), "--repetitions", "3", "--concurrency", "2"], cwd=a,
                                      stdout=(a / f"{out}.log").open("w"), stderr=subprocess.STDOUT))
    for p in procs:
        p.wait()
    arms = {}
    for arm, keep in ARMS.items():
        ids = {i for i in broken if src.get(i) in keep}
        if not ids:
            arms[arm] = {"broken": [], "noisy": [], "reproduces": False, "confirmed": False}
            continue
        for name in ("base-a", "head-a", "base-b"):
            filtered(a / f"{name}.json", a / f"{arm}-{name}.json", ids)
        # cases that also break base against base are noise: drop them, then gate the rest
        flywheel(gate["base_env"], a, "gate", "--base", f"{arm}-base-a.json", "--head", f"{arm}-base-b.json",
                 "--report", f"{arm}-bvb.md")
        bvb = (a / f"{arm}-bvb.md").read_text() if (a / f"{arm}-bvb.md").exists() else ""
        bvb = bvb.split("### Broken", 1)[1].split("\n### ", 1)[0] if "### Broken" in bvb else ""
        noisy = set(re.findall(r"^- `([^`]+)`", bvb, re.M)) & ids
        kept = ids - noisy
        rep = False
        if kept:
            for name in ("base-a", "head-a"):
                filtered(a / f"{name}.json", a / f"{arm}-kept-{name}.json", kept)
            rep = flywheel(gate["base_env"], a, "gate", "--base", f"{arm}-kept-base-a.json",
                           "--head", f"{arm}-kept-head-a.json") == 1
        arms[arm] = {"broken": sorted(ids), "noisy": sorted(noisy), "reproduces": rep, "confirmed": rep}
    result = {"gate": gid, "blocked": True, "broken": sorted(broken), "arms": arms}
    (a / "result.json").write_text(json.dumps(result, indent=1))
    return result


if __name__ == "__main__":
    reuse = "--reuse" in sys.argv  # re-decide from existing reruns, run nothing
    args = [x for x in sys.argv[1:] if x != "--reuse"]
    for gid in args[1:]:
        print(json.dumps(confirm(Path(args[0]), gid, reuse)), flush=True)
