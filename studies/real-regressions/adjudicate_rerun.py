"""Step (a) of the blocked-control rule (Amendment 3): python adjudicate_rerun.py <runs-dir> <gate>

Reruns only the cases that broke, 3 against 3 on base and head, plus a second base, in
<gate>/adjud/, and reports whether the break reproduces and whether base against base passes.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

runs, gid = Path(sys.argv[1]), sys.argv[2]
project = gid.rsplit("-g", 1)[0]
g = runs / project / gid
gate = json.loads((g / "gate.json").read_text())
report = (g / "gate.md").read_text()
broken = report.split("### Broken", 1)[1].split("\n<details>", 1)[0] if "### Broken" in report else ""
ids = re.findall(r"^- `([^`]+)`", broken, re.M)
a = g / "adjud"
a.mkdir(exist_ok=True)
for f in ("flywheel.toml", "dataset.jsonl", "adapter.py"):
    (a / f).write_bytes((g / f).read_bytes())
for extra in g.iterdir():  # helper files the adapter imports from its own folder
    if extra.suffix == ".py" and extra.name != "adapter.py":
        (a / extra.name).write_bytes(extra.read_bytes())


def run(env: str, out: str) -> subprocess.Popen:
    """Start one side."""
    return subprocess.Popen([f"{env}/bin/flywheel", "run", "--label", out[:-5], "--out", out, "--only", ",".join(ids),
                             "--repetitions", "3", "--concurrency", "2"], cwd=a,
                            stdout=(a / f"{out}.log").open("w"), stderr=subprocess.STDOUT)


procs = [run(gate["base_env"], "base-a.json"), run(gate["head_env"], "head-a.json"), run(gate["base_env"], "base-b.json")]
for p in procs:
    p.wait()


def blocked(x: str, y: str) -> bool:
    """Flywheel's own gate on two of the rerun files."""
    return subprocess.run([f"{gate['base_env']}/bin/flywheel", "gate", "--base", x, "--head", y], cwd=a,
                          capture_output=True, text=True, check=False).returncode == 1


result = {"gate": gid, "cases": ids, "reproduces": blocked("base-a.json", "head-a.json"),
          "base_vs_base_passes": not blocked("base-a.json", "base-b.json")}
(a / "result.json").write_text(json.dumps(result, indent=1))
print(json.dumps(result))
