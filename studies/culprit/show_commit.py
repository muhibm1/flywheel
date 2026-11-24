"""Print one commit of a baseline case's window. Usage: python3 show_commit.py <baseline case folder> <sha>"""
import json, subprocess, sys
from pathlib import Path

w = json.loads((Path(sys.argv[1]) / "window.json").read_text())
want = sys.argv[2]
hit = [x for x in w["shas"] if x.startswith(want)] if len(want) >= 7 else []
if len(hit) != 1:
    sys.exit("not a commit in this window")
out = subprocess.run(["git", "-C", w["repo"], "show", "--first-parent", "--format=%H %ad %s%n%b", "--date=short", hit[0]], capture_output=True, text=True).stdout
print(out[:60000])
