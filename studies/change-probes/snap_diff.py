"""Run snapshot scenarios on base and head and print what differs between the two sides.

Usage: python snap_diff.py <gate_dir> [--only s_03_name.py] [--timeout 180]

A scenario is `probes/s_*.py`. It drives one ordinary use of the project and writes everything a
user or a downstream system could observe (return values, stored history, exported text, messages
sent to the model, spans and log records emitted, files written, exceptions) as one JSON object to
the path in the environment variable SNAP_OUT. It makes no assertion about what is right.

Each scenario runs twice per side. A value that differs between two runs of the same side is noise
(ids, clocks, addresses) and is left out. What remains and differs between base and head is
printed and saved to snaps/<scenario>.diff.json: each entry is a path into the JSON object with
the base value and the head value.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_probes import run_cmd  # noqa: E402

MISSING = "<absent>"
SECRET_WORDS = ("API_KEY", "TOKEN", "SECRET", "LANGSMITH", "LANGCHAIN_", "ANTHROPIC", "OPENAI")


def flatten(value, prefix: str = "") -> dict[str, object]:
    """Turn nested JSON into {path: leaf value} so two snapshots can be compared path by path."""
    out: dict[str, object] = {}
    if isinstance(value, dict):
        if not value:
            out[prefix or "$"] = {}
        for k in sorted(value, key=str):
            out.update(flatten(value[k], f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(value, list):
        out[f"{prefix}#len"] = len(value)
        for i, item in enumerate(value):
            out.update(flatten(item, f"{prefix}[{i}]"))
    else:
        out[prefix or "$"] = value
    return out


def side_env(gate: Path, gj: dict, side: str, out_path: Path) -> dict[str, str]:
    """The same clean environment the probe runner gives a probe, plus where to write the snapshot."""
    env = dict(os.environ)
    env["PROBE_SIDE"] = side
    env["PROBE_TREE"] = str(gate / side)
    env["SNAP_OUT"] = str(out_path)
    env.pop("PYTHONPATH", None)
    extra = gj.get("pythonpath", {}).get(side)
    if extra:
        env["PYTHONPATH"] = os.pathsep.join(extra)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in list(env):
        if any(t in name.upper() for t in SECRET_WORDS):
            env.pop(name)
    env["LANGSMITH_TRACING"] = "false"
    env["LANGCHAIN_TRACING_V2"] = "false"
    return env


def snapshot(gate: Path, gj: dict, scenario: Path, side: str, rep: int, timeout: int) -> dict[str, object]:
    """Run one scenario once on one side and return its flattened snapshot."""
    python = Path(gj.get("python", {}).get(side) or gate / f"venv-{side}" / "bin" / "python")
    out_path = gate / "snaps" / f"{scenario.stem}.{side}.{rep}.json"
    if out_path.exists():
        out_path.unlink()
    r = run_cmd([str(python), str(scenario)], gate, timeout, side_env(gate, gj, side, out_path))
    flat: dict[str, object] = {"$exit": r["exit"]}
    if out_path.exists():
        try:
            flat.update(flatten(json.loads(out_path.read_text())))
        except ValueError:
            flat["$snapshot"] = "not valid JSON"
    else:
        flat["$snapshot"] = "not written"
        flat["$tail"] = r["tail"][-400:]
    return flat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gate")
    ap.add_argument("--only", action="append")
    ap.add_argument("--timeout", type=int, default=180)
    a = ap.parse_args()
    gate = Path(a.gate).resolve()
    gj = json.loads((gate / "gate.json").read_text()) if (gate / "gate.json").exists() else {}
    (gate / "snaps").mkdir(exist_ok=True)
    scenarios = sorted((gate / "probes").glob("s_*.py"))
    if a.only:
        scenarios = [s for s in scenarios if s.name in a.only]
    for sc in scenarios:
        runs = {side: [snapshot(gate, gj, sc, side, rep, a.timeout) for rep in (1, 2)] for side in ("base", "head")}
        stable = {}
        noisy: set[str] = set()
        for side, (one, two) in runs.items():
            keys = set(one) | set(two)
            noisy |= {k for k in keys if one.get(k, MISSING) != two.get(k, MISSING)}
            stable[side] = one
        diffs = []
        for k in sorted(set(stable["base"]) | set(stable["head"])):
            if k in noisy:
                continue
            b, h = stable["base"].get(k, MISSING), stable["head"].get(k, MISSING)
            if b != h:
                diffs.append({"path": k, "base": b, "head": h})
        (gate / "snaps" / f"{sc.stem}.diff.json").write_text(json.dumps(diffs, indent=1))
        print(f"{sc.name}: {len(diffs)} differing paths, {len(noisy)} noisy paths left out")
        for d in diffs[:40]:
            print("  ", d["path"], "| base:", json.dumps(d["base"])[:160], "| head:", json.dumps(d["head"])[:160])
        if len(diffs) > 40:
            print(f"   ... {len(diffs) - 40} more in snaps/{sc.stem}.diff.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
