"""Run a Python script or module against the project source in the current directory.

Usage (from inside a checkout of the project, e.g. your case's repo/ folder):
  python3 /home/user/fw/loop/run_in_tree.py <case folder> <script.py> [args...]
  python3 /home/user/fw/loop/run_in_tree.py <case folder> -m pytest [args...]

Uses the interpreter named in <case folder>/case.json (it has the project's dependencies; the
project itself is not installed) and puts the case's source_roots, relative to the current
directory, on the import path. Credential-looking environment variables are removed. The exit code
of the script is passed through, so this works with `git bisect run`.
"""
import json, os, re, subprocess, sys
from pathlib import Path

case = Path(sys.argv[1]).resolve()
cfg = json.loads((case / "case.json").read_text())
here = Path.cwd()
roots = [str(here / r) if r not in ("", ".") else str(here) for r in cfg.get("source_roots") or ["."]]
env = {k: v for k, v in os.environ.items() if not re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", k, re.I)}
env["PYTHONPATH"] = os.pathsep.join(roots)
env["PYTHONDONTWRITEBYTECODE"] = "1"
sys.exit(subprocess.run([cfg["python"], *sys.argv[2:]], env=env, cwd=here).returncode)
