"""Base-against-base noise gates for one project: python noise_project.py <project>.

Each gate's frozen cases run on the base version on BOTH sides, so any block is pure noise."""
import glob, json, os, subprocess, sys
from pathlib import Path
project = sys.argv[1]
here = Path(__file__).resolve().parent
env = dict(os.environ, RR_RUNS=os.environ.get("RR_RUNS", "runs-r2") + "-noise")
for gate_json in sorted(glob.glob(f"/tmp/rr/blind/{project}/{project}-g*/gate.json")):
    g = json.loads(Path(gate_json).read_text())
    subprocess.run([sys.executable, "-I", str(here / "run_gate.py"), project, g["gate"], g["base_env"], g["base_env"]], env=env, check=False)
