"""Score one set of gates against the sealed key.

Usage: python score.py <key.json> <SET> <gates_dir> [--strict <adjudication.json>] [--out <file>]

Loose catch: a regression gate whose verdict is block.
Strict catch: a regression gate that blocks AND whose blocking findings include the team's own
regression, as judged by the adjudicator (adjudication.json maps gate id to
{"match": true|false, ...}). A gate with no verdict counts as a miss for a regression and is
listed as unfinished; it is never dropped from the denominator.
False block: a control gate whose verdict is block.
Intervals are 95% Wilson score intervals.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Return the Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def rate(k: int, n: int) -> str:
    """Format a count as a rate with its interval."""
    lo, hi = wilson(k, n)
    pct = 100 * k / n if n else 0.0
    return f"{k}/{n} = {pct:.1f}% (95% interval {100 * lo:.1f} to {100 * hi:.1f})"


def main() -> int:
    """Read the key and the gate verdicts and print the score."""
    args = sys.argv[1:]
    strict_file = out_file = None
    if "--strict" in args:
        i = args.index("--strict")
        strict_file = args[i + 1]
        del args[i:i + 2]
    if "--out" in args:
        i = args.index("--out")
        out_file = args[i + 1]
        del args[i:i + 2]
    key_path, set_name, gates_dir = args
    adjud = json.loads(Path(strict_file).read_text()) if strict_file else {}
    rows = [r for r in json.loads(Path(key_path).read_text()) if r["set"] == set_name]
    rep = {"set": set_name, "regressions": [], "controls": [], "unfinished": []}
    for r in sorted(rows, key=lambda x: x["gate_id"]):
        vf = Path(gates_dir) / r["gate_id"] / "verdict.json"
        verdict = json.loads(vf.read_text()).get("verdict") if vf.exists() else None
        if verdict not in ("block", "pass"):
            rep["unfinished"].append(r["gate_id"])
        item = {"gate_id": r["gate_id"], "project": r["project"], "verdict": verdict}
        if r["kind"] == "regression":
            item["strict"] = bool(verdict == "block" and adjud.get(r["gate_id"], {}).get("match") is True)
            rep["regressions"].append(item)
        else:
            rep["controls"].append(item)
    reg, con = rep["regressions"], rep["controls"]
    loose = sum(1 for x in reg if x["verdict"] == "block")
    strict = sum(1 for x in reg if x["strict"])
    fb = sum(1 for x in con if x["verdict"] == "block")
    rep["summary"] = {
        "loose_catch": rate(loose, len(reg)),
        "strict_catch": rate(strict, len(reg)) if strict_file else "not adjudicated",
        "false_blocks": rate(fb, len(con)),
    }
    print(set_name)
    for k, v in rep["summary"].items():
        print(" ", k, v)
    print("  missed regressions:", " ".join(x["gate_id"] for x in reg if x["verdict"] != "block") or "none")
    if strict_file:
        print("  blocked for another reason:",
              " ".join(x["gate_id"] for x in reg if x["verdict"] == "block" and not x["strict"]) or "none")
    print("  blocked controls:", " ".join(x["gate_id"] for x in con if x["verdict"] == "block") or "none")
    print("  unfinished:", " ".join(rep["unfinished"]) or "none")
    if out_file:
        Path(out_file).write_text(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
