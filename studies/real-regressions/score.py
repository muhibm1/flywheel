"""Score the study once: python score.py <runs-dir> <out.json> [gate ...]

For every gate under <runs-dir>/<project>/<gate>/ with a verdict, re-decide the gate on each arm by
filtering the pooled runs (base.clean.json, head.clean.json) to the arm's case sources, using the
gate's own flywheel.toml and Flywheel's own `gate` command, so every arm uses identical rules:

  arm 2  standing                (written from docs only)
  arm 3  + change                (written from the diff, base only)   <- primary
  arm 4  + diff                  (explored; writer may have seen head)
  arm 5  + fault                 (scripted bad model reply on the first tool turn)
  arm 6  + sweep                 (input-condition sweep, base only; Amendment 4)
  <arm>c the arm's block confirmed by confirm.py (reproduces, base against base passes)
  avg    averages only: block when the head's share of fully passing runs over all cases is lower
         than the base's with one-sided Fisher p < 0.05 (no per-case comparison)

The key (/root/sealed) is read only here. A gate with no verdict counts as a miss for a regression
and is reported, not counted, for a control. Wilson 95% intervals throughout.
"""

import json
import math
import subprocess
import sys
from pathlib import Path

KEY = json.loads(Path("/root/sealed/gate-key.json").read_text())
CASES = {c["id"]: c for c in json.loads(Path("/root/sealed/cases.json").read_text())} \
    if isinstance(json.loads(Path("/root/sealed/cases.json").read_text()), list) \
    else json.loads(Path("/root/sealed/cases.json").read_text())
ARMS = {"arm2": {"standing"}, "arm3": {"standing", "change"}, "arm4": {"standing", "change", "diff"},
        "arm5": {"standing", "change", "diff", "fault"}, "arm6": {"standing", "change", "sweep"}}


def wilson(k: int, n: int) -> list[float]:
    """95% Wilson interval for k of n."""
    if n == 0:
        return [0.0, 1.0]
    z, p = 1.96, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 3), round(c + h, 3)]


def fisher_less(a: int, b: int, c: int, d: int) -> float:
    """One-sided Fisher p that head (c of c+d passing) is worse than base (a of a+b passing)."""
    n1, n2, k = a + b, c + d, a + c

    def hyp(x: int) -> float:
        return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(n1 + n2, k)
    return sum(hyp(x) for x in range(max(0, k - n2), min(k, n1) + 1) if x >= a)


def sources(g: Path) -> dict[str, str]:
    """Case id -> metadata.source, from the frozen dataset."""
    out = {}
    for line in (g / "dataset.jsonl").read_text().splitlines():
        if line.strip():
            c = json.loads(line)
            out[c["id"]] = (c.get("metadata") or {}).get("source", "standing")
    return out


def arm_blocked(g: Path, env: str, keep: set[str], src: dict[str, str]) -> bool | None:
    """Re-run Flywheel's gate on the arm's cases; True blocked, False passed, None no cases."""
    ids = {i for i, s in src.items() if s in keep}
    if not ids or (keep - {"standing", "change"} and not any(s in keep - {"standing", "change"} for s in src.values())):
        return None
    for side in ("base", "head"):
        e = json.loads((g / f"{side}.clean.json").read_text())
        e["runs"] = [r for r in e["runs"] if r["example_id"] in ids]
        e["examples"] = {k: v for k, v in e["examples"].items() if k in ids}
        (g / f"score-{side}.json").write_text(json.dumps(e))
    code = subprocess.run([f"{env}/bin/flywheel", "gate", "--base", "score-base.json", "--head", "score-head.json"],
                          cwd=g, capture_output=True, text=True, check=False).returncode
    return code == 1


def averages_blocked(g: Path) -> bool:
    """Head's share of fully passing runs is lower than base's (one-sided Fisher p < 0.05)."""
    def tally(side: str) -> tuple[int, int]:
        runs = json.loads((g / f"{side}.clean.json").read_text())["runs"]
        ok = sum(1 for r in runs if not r.get("error") and r["scores"] and all(v >= 1 for v in r["scores"].values()))
        return ok, len(runs) - ok
    (a, b), (c, d) = tally("base"), tally("head")
    return fisher_less(a, b, c, d) < 0.05


def main() -> None:
    """Score every gate and write the summary."""
    runs, out = Path(sys.argv[1]), Path(sys.argv[2])
    only = set(sys.argv[3:])
    rows = []
    for gid, cid in sorted(KEY.items()):
        if only and gid not in only:
            continue
        project = gid.rsplit("-g", 1)[0]
        case = CASES[cid]
        g = runs / project / gid
        row = {"gate": gid, "case": cid, "kind": case["kind"], "stratum": case.get("stratum"),
               "title": case.get("title")}
        if not (g / "verdict.json").exists():
            row["ran"] = False
        else:
            env = json.loads((g / "gate.json").read_text())["base_env"]
            src = sources(g)
            row["ran"] = True
            row["full"] = json.loads((g / "verdict.json").read_text())["blocked"]
            for arm, keep in ARMS.items():
                row[arm] = arm_blocked(g, env, keep, src)
            conf = g / "confirm" / "result.json"
            conf = json.loads(conf.read_text())["arms"] if conf.exists() else None
            for arm in ARMS:
                if row[arm] is not None:
                    row[arm + "c"] = bool(row[arm]) and (conf is not None and conf[arm]["confirmed"]) \
                        if row[arm] else False
            row["avg"] = averages_blocked(g)
            row["n_cases"] = {s: sum(1 for v in src.values() if v == s) for s in ("standing", "change", "diff", "fault", "sweep")}
            diff_seen = [json.loads(line) for line in (g / "dataset.jsonl").read_text().splitlines()
                         if line.strip() and (json.loads(line).get("metadata") or {}).get("source") == "diff"]
            row["diff_seen_fail_on_head"] = sum(1 for c in diff_seen if c["metadata"].get("seen_on_head") in ("fail", "error"))
        rows.append(row)
    summary = {}
    names = [a for a in ("arm2", "arm3", "arm4", "arm5", "arm6") if any(r.get(a) is not None for r in rows)]
    for arm in names + [a + "c" for a in names] + ["avg"]:
        regs = [r for r in rows if r["kind"] == "regression"]
        ctrl = [r for r in rows if r["kind"] == "control" and r["ran"]]
        caught = sum(1 for r in regs if r["ran"] and r.get(arm))
        fb = sum(1 for r in ctrl if r.get(arm))
        summary[arm] = {"caught": caught, "regressions": len(regs), "catch_ci": wilson(caught, len(regs)),
                        "false_blocks": fb, "controls_run": len(ctrl), "false_block_ci": wilson(fb, len(ctrl))}
        for s in ("B", "C"):
            rs = [r for r in regs if r["stratum"] == s]
            summary[arm][f"stratum_{s}"] = f"{sum(1 for r in rs if r['ran'] and r.get(arm))}/{len(rs)}"
    out.write_text(json.dumps({"summary": summary, "gates": rows}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
