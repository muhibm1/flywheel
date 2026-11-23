"""Run every gate of one project in turn: python run_project.py <project> [heads_dir]."""

import glob
import os
import json
import subprocess
import sys
from pathlib import Path

project = sys.argv[1]
heads = sys.argv[2] if len(sys.argv) > 2 else "/root/rr-heads/envs"
here = Path(__file__).resolve().parent
for gate_json in sorted(glob.glob(f"/tmp/rr/blind/{project}/{project}-g*/gate.json")):
    g = json.loads(Path(gate_json).read_text())
    gid = g["gate"]
    if (here / os.environ.get("RR_RUNS", "runs") / project / gid / "verdict.json").exists():
        continue
    head = glob.glob(f"{heads}/{gid}-*")
    if not head or not Path(head[0], ".ok").exists():
        print(gid, "no head env", flush=True)
        continue
    subprocess.run([sys.executable, "-I", str(here / "run_gate.py"), project, gid, g["base_env"], head[0]], check=False)
