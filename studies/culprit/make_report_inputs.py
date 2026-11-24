"""Give each bug-report writer what a reporting user would know. Usage: python3 make_report_inputs.py <SET>

Writes /home/user/fw/culprit/<SET>-reports/<gate_id>/symptom.json and witness_test.py. No commit
ids, titles or fix text go in.
"""
import json, re, shutil, sys
from pathlib import Path

s = sys.argv[1]
key = [r for r in json.load(open("/mnt/project-files/flywheel/change-probes/sealed/sets/key.json")) if r["set"] == s and r["kind"] == "regression"]
root = Path("/home/user/fw/culprit") / (s + "-reports")
for r in sorted(key, key=lambda x: x["gate_id"]):
    row = r["row"]
    c = root / r["gate_id"]
    c.mkdir(parents=True, exist_ok=True)
    what = re.sub(r"#\d+", "an earlier change", row.get("what_broke") or "")
    (c / "symptom.json").write_text(json.dumps({"project": row.get("repo"), "what_broke": what,
                                                "witness_tests": (row.get("witness") or {}).get("tests")}, indent=1))
    w = (row.get("witness") or {}).get("path")
    if w and not Path(w).is_absolute():
        w = "/mnt/project-files/flywheel/change-probes/sealed/" + w
    if w and Path(w).exists():
        shutil.copy(w, c / "witness_test.py")
    (c / "failure.txt").write_text((row.get("witness") or {}).get("head_failure") or "")
    print(r["gate_id"], "witness" if (c / "witness_test.py").exists() else "NO WITNESS FILE")
