"""Undo the report swap between h2-034 and h2-044 and clear both arms' outputs for those two cases."""
import shutil, subprocess
from pathlib import Path

R = Path("/home/user/fw/culprit")
a, b = "h2-034", "h2-044"
for d, f in [("H2-reports", "report.txt"), ("H2-terse", "REPORT.md"), ("H2-terse", "terse.txt"), ("H2", "REPORT.md"), ("H2-loop", "REPORT.md")]:
    pa, pb = R / d / a / f, R / d / b / f
    if pa.exists() and pb.exists():
        ta, tb = pa.read_text(), pb.read_text()
        pa.write_text(tb)
        pb.write_text(ta)
        print("swapped", d, f)
for c in (a, b):
    for f in ("probe.py", "result.json", "REPRO_NOTES.md"):
        (R / "H2" / c / f).unlink(missing_ok=True)
    for f in ("proof.py", "answer.json"):
        (R / "H2-loop" / c / f).unlink(missing_ok=True)
    repo = R / "H2-loop" / c / "repo"
    subprocess.run(["git", "-C", str(repo), "bisect", "reset"], capture_output=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-f", "main"])
    subprocess.run(["git", "-C", str(repo), "clean", "-qfdx"])
    for extra in (R / "H2-loop" / c).iterdir():
        if extra.name not in ("REPORT.md", "SETUP_OLD_NOTES.md", "case.json", "repo"):
            print("leftover", extra)
print("cleared")
