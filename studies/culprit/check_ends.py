"""Run each case's probe at the good end, the bad end and the real fix. Usage: python3 check_ends.py <SET> <cases dir name>
A probe is valid when it reports good, bad, good. Used to score probes written without running code."""
import json, subprocess, sys
from pathlib import Path

s = sys.argv[1]
d = Path("/home/user/fw/culprit") / sys.argv[2]
key = {r["gate_id"]: r for r in json.load(open("/mnt/project-files/flywheel/change-probes/sealed/sets/key.json")) if r["set"] == s and r["kind"] == "regression"}


def at(c, where):
    p = subprocess.run([sys.executable, "/home/user/flywheel/studies/culprit/trace.py", str(c), "--at", where], capture_output=True, text=True)
    first = (p.stdout.strip().splitlines() or ["?: ?"])[0]
    return first.split(": ", 1)[-1].split(" ")[0]


out, ok = {}, 0
for gid in sorted(key):
    c = d / gid
    if not (c / "probe.py").exists():
        out[gid] = ["no probe"]
    else:
        out[gid] = [at(c, "good"), at(c, "bad"), at(c, key[gid]["row"]["fix_sha"])]
    v = out[gid] == ["good", "bad", "good"]
    ok += v
    print(gid, " ".join(out[gid]), "VALID" if v else "", flush=True)
(d.parent / (d.name + "_ends.json")).write_text(json.dumps(out, indent=1))
print("valid probes:", ok, "of", len(out))
