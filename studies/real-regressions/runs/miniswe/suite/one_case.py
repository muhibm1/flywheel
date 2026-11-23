"""Run one case from a gate's dataset through the gate's adapter and print the check results."""

import json
import sys
from pathlib import Path

gate, case_id = Path(sys.argv[1]).resolve(), sys.argv[2]
sys.path.insert(0, str(gate))
import adapter  # noqa: E402

for line in (gate / "dataset.jsonl").read_text().splitlines():
    case = json.loads(line)
    if case["id"] == case_id:
        out = adapter.target(case["inputs"])
        ref = case["reference_outputs"]
        print({k: out[k] for k in ("exit_status", "n_calls")})
        for name in ("check_exit_status", "check_verify", "check_files", "check_trajectory", "check_limits"):
            print(name, getattr(adapter, name)(case["inputs"], out, ref))
