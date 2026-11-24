"""Build plain-model baseline folders: the report plus the first-parent history of the window. Usage: python3 make_baseline.py <SET>"""
import json, shutil, subprocess, sys
from pathlib import Path

s = sys.argv[1]
src, dst = Path("/home/user/fw/culprit") / s, Path("/home/user/fw/culprit") / (s + "-base")
for c in sorted(src.iterdir()):
    if not (c / "case.json").exists() or not (c / "REPORT.md").exists():
        continue
    cfg = json.loads((c / "case.json").read_text())
    out = dst / c.name
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(c / "REPORT.md", out / "REPORT.md")
    log = subprocess.run(
        ["git", "-C", cfg["repo"], "log", "--first-parent", "--date=short", "--format=%n%H %ad %s", "--stat=120", cfg["good"] + ".." + cfg["bad"]],
        capture_output=True, text=True, check=True).stdout
    (out / "history.txt").write_text(log)
    shas = subprocess.run(["git", "-C", cfg["repo"], "rev-list", "--first-parent", cfg["good"] + ".." + cfg["bad"]], capture_output=True, text=True, check=True).stdout.split()
    (out / "window.json").write_text(json.dumps({"repo": cfg["repo"], "shas": shas, "bad_tree": str(c / "bad")}))
    print(c.name, len(shas), "commits", len(log) // 1024, "KB")
