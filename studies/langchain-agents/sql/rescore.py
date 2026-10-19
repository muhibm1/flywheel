"""Re-grade a finished experiment from its outputs log, after a fix to a code-only check.

Flywheel's experiment file keeps scores, not answers; the adapter logs every answer to
`runs/<label>.outputs.jsonl`. This recomputes each run's scores from those answers with the
current evaluators. Runs that errored (no answer) are left as they were.

Usage: python rescore.py runs/LABEL.json
"""

import json
import sys
from collections import defaultdict

import adapter
from flywheel.dataset import inputs_id

path = sys.argv[1]
exp = json.load(open(path))
refs = {json.loads(line)["id"]: json.loads(line)["reference_outputs"] for line in open("dataset.jsonl")}
answers = defaultdict(list)
for line in open(path.replace(".json", ".outputs.jsonl")):
    row = json.loads(line)
    answers[inputs_id(row["inputs"])].append(row["outputs"])
for run in exp["runs"]:
    if run["error"]:
        continue
    out = answers[run["example_id"]].pop(0)
    ref = refs[run["example_id"]]
    run["scores"] = {
        "correct": float(adapter.correct({}, out, ref)),
        "read_only": float(adapter.read_only({}, out, ref)),
    }
left = sum(len(v) for v in answers.values())
assert left == 0, f"{left} logged answers had no run"
json.dump(exp, open(path, "w"), indent=2, sort_keys=True)
print("rescored", path)
