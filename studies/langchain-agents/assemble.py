"""Build a Flywheel experiment from the answers an adapter logged, scoring them afresh.

A long subscription run can be cut short by a spent usage window. Every finished answer is in
`runs/<label>*.outputs.jsonl`; this keeps each case that has all its repetitions, scores them
with the config's evaluators, and writes `runs/<label>.json`. It prints the cases still missing,
for a `flywheel run --only` of the rest.

Usage (from an agent folder): python ../assemble.py LABEL [--missing]
"""

import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

from flywheel import config, dataset
from flywheel.dataset import inputs_id
from flywheel.experiment import Experiment, RunRecord, summary
from flywheel.scores import score_all

label = sys.argv[1]
cfg = config.load(Path("flywheel.toml"))
examples = dataset.load(cfg.dataset)
answers = defaultdict(list)
for path in sorted(glob.glob(f"runs/{label}.outputs.jsonl")) + sorted(
    glob.glob(f"runs/{label}-rest*.outputs.jsonl")
):
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        answers[inputs_id(row["inputs"])].append(row["outputs"])
missing = [e.id for e in examples if len(answers[e.id]) < cfg.repetitions]
if "--missing" in sys.argv:
    print(",".join(missing))
    sys.exit(0)
if missing:
    sys.exit(f"cases still missing: {','.join(missing)}")
evaluators = cfg.evaluator_callables()
runs = []
for e in examples:
    for rep, out in enumerate(answers[e.id][: cfg.repetitions], start=1):
        scores, errors = score_all(evaluators, e.inputs, out, e.reference_outputs)
        runs.append(RunRecord(e.id, rep, scores, evaluator_errors=errors))
Experiment(
    label=label,
    backend="local",
    dataset_version=dataset.version(examples),
    repetitions=cfg.repetitions,
    runs=runs,
    examples={e.id: summary(e.inputs) for e in examples},
).save(Path(f"runs/{label}.json"))
print(f"{label}: {len(runs)} runs assembled")
