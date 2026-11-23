"""Run held-out gates once, at most 3 at a time: python run_heldout.py <gate> [<gate> ...]

Each gate goes through run_gate.py with the head env named in its gate.json, under RR_RUNS
(default runs-heldout). A gate that already has a verdict is skipped, so a restart resumes.
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARALLEL = 3


def run(gid: str) -> str:
    """Run one gate; its printed verdict line."""
    project = gid.rsplit("-g", 1)[0]
    g = json.loads(Path(f"/tmp/rr/blind/{project}/{gid}/gate.json").read_text())
    if (HERE / os.environ.get("RR_RUNS", "runs-heldout") / project / gid / "verdict.json").exists():
        return f"{gid} already done"
    env = dict(os.environ, RR_RUNS=os.environ.get("RR_RUNS", "runs-heldout"))
    done = subprocess.run([sys.executable, "-I", str(HERE / "run_gate.py"), project, gid, g["base_env"], g["head_env"]],
                          env=env, capture_output=True, text=True, check=False)
    return (done.stdout.strip().splitlines() or [f"{gid} exit {done.returncode}: {done.stderr[-300:]}"])[-1]


with ThreadPoolExecutor(PARALLEL) as pool:
    for line in pool.map(run, sys.argv[1:]):
        print(line, flush=True)
