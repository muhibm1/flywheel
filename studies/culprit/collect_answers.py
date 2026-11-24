"""Collect baseline answer.json files into one {gate_id: sha} file. Usage: python3 collect_answers.py <SET>"""
import json, sys
from pathlib import Path

d = Path("/home/user/fw/culprit") / (sys.argv[1] + "-base")
out = {}
for c in sorted(d.iterdir()):
    f = c / "answer.json"
    if f.exists():
        try:
            out[c.name] = json.loads(f.read_text()).get("sha")
        except Exception:
            out[c.name] = None
(d / "answers.json").write_text(json.dumps(out, indent=1))
print(len(out), "answers")
