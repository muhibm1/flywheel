"""Run each case's probe at the real fix commit; a faithful reproducer must report good there. Usage: python3 check_fix.py <SET> [cases dir name]"""
import json, subprocess, sys
from pathlib import Path

s = sys.argv[1]
d = Path("/home/user/fw/culprit") / (sys.argv[2] if len(sys.argv) > 2 else s)
key = {r["gate_id"]: r for r in json.load(open("/mnt/project-files/flywheel/change-probes/sealed/sets/key.json")) if r["set"] == s and r["kind"] == "regression"}
out = {}
for gid in sorted(key):
    c = d / gid
    if not (c / "probe.py").exists():
        out[gid] = "no probe"
    else:
        p = subprocess.run([sys.executable, "/home/user/flywheel/studies/culprit/trace.py", str(c), "--at", key[gid]["row"]["fix_sha"]], capture_output=True, text=True)
        first = (p.stdout.strip().splitlines() or ["?: ?"])[0]
        out[gid] = first.split(": ", 1)[-1].split(" ")[0]
    print(gid, out[gid], flush=True)
(d.parent / (d.name + "_fixcheck.json")).write_text(json.dumps(out, indent=1))
print("good at fix:", sum(v == "good" for v in out.values()), "of", len(out))
