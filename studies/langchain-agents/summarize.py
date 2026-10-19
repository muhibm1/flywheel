"""Print an experiment's pass counts per check, overall and per case.

Usage: python summarize.py EXPERIMENT.json [DATASET.jsonl]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

exp = json.loads(Path(sys.argv[1]).read_text())
meta = {}
if len(sys.argv) > 2:
    for line in Path(sys.argv[2]).read_text().splitlines():
        row = json.loads(line)
        meta[row["id"]] = row.get("metadata", {})
totals = defaultdict(lambda: [0, 0])
per_case = defaultdict(lambda: defaultdict(lambda: [0, 0]))
errors = 0
for run in exp["runs"]:
    if run["error"]:
        errors += 1
    for key, score in run["scores"].items():
        totals[key][0] += score >= 1
        totals[key][1] += 1
        per_case[run["example_id"]][key][0] += score >= 1
        per_case[run["example_id"]][key][1] += 1
print(f"{exp['label']}: {len(exp['runs'])} runs, {errors} errored")
for key, (ok, n) in sorted(totals.items()):
    print(f"  {key}: {ok}/{n}")
for case, scores in per_case.items():
    if any(ok < n for ok, n in scores.values()):
        tag = meta.get(case, {}).get("name") or meta.get(case, {}).get("level") or ""
        cells = " ".join(f"{k}={ok}/{n}" for k, (ok, n) in sorted(scores.items()))
        print(f"  {case} {tag} {cells} :: {exp['examples'][case][:90]}")
