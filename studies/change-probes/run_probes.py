"""Run every probe of a gate on base and head, and measure changed-line coverage on head.

Usage: python run_probes.py <gate_dir> [--only p_03_name.py] [--reps 3] [--timeout 180]

Layout of a gate folder:
  base/ head/            exported source trees (no git history)
  venv-base/ venv-head/  one interpreter per side, with that side's tree installed
  change.diff            unified diff base -> head
  probes/p_*.py          probes; exit 0 = behaves as the probe expects, anything else = not

A probe is a confirmed difference only when it passes every run on base and fails every run on
head. Results go to results.json; uncovered changed lines go to coverage.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def changed_lines(diff_text: str) -> dict[str, list[int]]:
    """Lines added or modified on the head side, per file path relative to the tree root."""
    out: dict[str, list[int]] = {}
    path, line = None, 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            name = raw[4:].strip()
            path = None if name == "/dev/null" else re.sub(r"^b/", "", name)
            continue
        m = HUNK.match(raw)
        if m:
            line = int(m.group(1))
            continue
        if path is None or raw.startswith("--- ") or raw.startswith("diff "):
            continue
        if raw.startswith("+"):
            out.setdefault(path, []).append(line)
            line += 1
        elif raw.startswith("-") or raw.startswith("\\"):
            continue
        else:
            line += 1
    return out


def run_once(python: Path, probe: Path, cwd: Path, timeout: int, env: dict[str, str]) -> dict:
    try:
        p = subprocess.run(
            [str(python), str(probe)], cwd=str(cwd), env=env, timeout=timeout,
            capture_output=True, text=True, errors="replace",
        )
        return {"exit": p.returncode, "tail": (p.stdout + "\n" + p.stderr)[-1500:]}
    except subprocess.TimeoutExpired:
        return {"exit": "timeout", "tail": f"timed out after {timeout}s"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gate")
    ap.add_argument("--only", action="append")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=180)
    a = ap.parse_args()

    gate = Path(a.gate).resolve()
    probes = sorted((gate / "probes").glob("p_*.py"))
    if a.only:
        probes = [p for p in probes if p.name in a.only]
    cov_dir = Path(tempfile.mkdtemp(prefix="cov-", dir=str(gate)))
    rc = gate / ".coveragerc"
    rc.write_text(
        "[run]\nparallel = True\nconcurrency = thread\n"
        f"data_file = {cov_dir / '.coverage'}\nsource = {gate / 'head'}\n"
    )
    results = {}
    for probe in probes:
        entry = {}
        for side in ("base", "head"):
            python = gate / f"venv-{side}" / "bin" / "python"
            env = dict(os.environ)
            env["PROBE_SIDE"] = side
            env["PROBE_TREE"] = str(gate / side)
            env.pop("PYTHONPATH", None)
            runs = []
            for i in range(a.reps):
                if side == "head" and i == 0:
                    env_cov = dict(env, COVERAGE_PROCESS_START=str(rc), COVERAGE_RCFILE=str(rc))
                    cmd_env = env_cov
                    wrapper = gate / ".cov_probe.py"
                    wrapper.write_text(
                        "import runpy, sys\n"
                        "try:\n    import coverage\n    c = coverage.Coverage(config_file=%r)\n    c.start()\n"
                        "except Exception:\n    c = None\n"
                        "try:\n    sys.argv = [sys.argv[1]]\n    runpy.run_path(sys.argv[0], run_name='__main__')\n"
                        "finally:\n    if c:\n        c.stop(); c.save()\n" % str(rc)
                    )
                    try:
                        p = subprocess.run(
                            [str(python), str(wrapper), str(probe)], cwd=str(gate), env=cmd_env,
                            timeout=a.timeout, capture_output=True, text=True, errors="replace",
                        )
                        runs.append({"exit": p.returncode, "tail": (p.stdout + "\n" + p.stderr)[-1500:]})
                    except subprocess.TimeoutExpired:
                        runs.append({"exit": "timeout", "tail": f"timed out after {a.timeout}s"})
                else:
                    runs.append(run_once(python, probe, gate, a.timeout, env))
            entry[side] = runs
        base_ok = all(r["exit"] == 0 for r in entry["base"])
        head_fail = all(r["exit"] != 0 for r in entry["head"])
        head_ok = all(r["exit"] == 0 for r in entry["head"])
        entry["status"] = (
            "confirmed_difference" if base_ok and head_fail
            else "same" if base_ok and head_ok
            else "base_not_passing" if not base_ok
            else "flaky"
        )
        results[probe.name] = entry
        print(f"{probe.name}: {entry['status']} base={[r['exit'] for r in entry['base']]} head={[r['exit'] for r in entry['head']]}")

    prior = {}
    out_file = gate / "results.json"
    if a.only and out_file.exists():
        prior = json.loads(out_file.read_text())
    prior.update(results)
    out_file.write_text(json.dumps(prior, indent=1))

    # Changed-line coverage on head.
    cov_json = gate / ".cov.json"
    py = gate / "venv-head" / "bin" / "python"
    subprocess.run([str(py), "-m", "coverage", "combine", f"--rcfile={rc}"], cwd=str(gate), capture_output=True)
    subprocess.run([str(py), "-m", "coverage", "json", f"--rcfile={rc}", "-o", str(cov_json)], cwd=str(gate), capture_output=True)
    changed = changed_lines((gate / "change.diff").read_text(errors="replace"))
    measured = {}
    if cov_json.exists():
        for f, d in json.loads(cov_json.read_text()).get("files", {}).items():
            rel = os.path.relpath(os.path.join(str(gate), f) if not os.path.isabs(f) else f, str(gate / "head"))
            measured[rel] = d
    report = {}
    for path, lines in changed.items():
        if not path.endswith(".py") or "/tests/" in "/" + path or Path(path).name.startswith("test_"):
            continue
        d = measured.get(path)
        if d is None:
            report[path] = {"never_imported": True, "changed": lines}
            continue
        missing = sorted(set(lines) & set(d.get("missing_lines", [])))
        executed = sorted(set(lines) & set(d.get("executed_lines", [])))
        report[path] = {"executed": executed, "uncovered": missing}
    cov_out = gate / "coverage.json"
    if a.only and cov_out.exists():
        old = json.loads(cov_out.read_text())
        for path, d in report.items():
            o = old.get(path)
            if o and "uncovered" in o and "uncovered" in d:
                d["uncovered"] = sorted(set(d["uncovered"]) & set(o["uncovered"]))
                d["executed"] = sorted(set(d["executed"]) | set(o["executed"]))
            elif o and "uncovered" in o and d.get("never_imported"):
                report[path] = o
    cov_out.write_text(json.dumps(report, indent=1))
    total_unc = sum(len(d.get("uncovered", d.get("changed", []))) for d in report.values())
    print(f"changed source lines not yet executed by any probe on head: {total_unc} (see coverage.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
