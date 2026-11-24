"""Move files between the stages of building held-out cases. Prints names and counts only, never text.

Usage: python3 h_stage.py <SET> detailed|terse|notes
  detailed  <SET>-reports/<id>/report.txt   -> <SET>-terse/<id>/REPORT.md   (input of the short-note writer)
  terse     <SET>-terse/<id>/terse.txt      -> <SET>/<id>/REPORT.md         (what the tool and baselines see)
  notes     envprep/<SET>/<project>/notes.txt -> SETUP_OLD_NOTES.md in each case of that project
"""
import json, shutil, sys
from pathlib import Path

s, stage = sys.argv[1], sys.argv[2]
root = Path("/home/user/fw/culprit")
done, missing = 0, []
if stage == "notes":
    for h in sorted((Path("/home/user/fw/envprep") / s).glob("*/hints.json")):
        n = h.parent / "notes.txt"
        for c in json.loads(h.read_text())["cases"]:
            if n.exists():
                shutil.copy(n, Path(c["folder"]) / "SETUP_OLD_NOTES.md")
                done += 1
            else:
                missing.append(Path(c["folder"]).name)
else:
    for c in sorted((root / s).iterdir()):
        if not (c / "case.json").exists():
            continue
        if stage == "detailed":
            src, dst = root / (s + "-reports") / c.name / "report.txt", root / (s + "-terse") / c.name / "REPORT.md"
        else:
            src, dst = root / (s + "-terse") / c.name / "terse.txt", c / "REPORT.md"
        if src.exists() and src.read_text().strip():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
            done += 1
        else:
            missing.append(c.name)
print(stage, "copied", done, "missing", len(missing), " ".join(missing))
