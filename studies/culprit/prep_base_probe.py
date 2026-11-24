"""Give baseline folders what a blind probe writer needs (case.json, notes, bad link). Usage: python3 prep_base_probe.py <SET> [report-variant suffix]"""
import os, shutil, sys
from pathlib import Path

s = sys.argv[1]
root = Path("/home/user/fw/culprit")
for b in sorted((root / (s + "-base")).iterdir()):
    c = root / s / b.name
    if not b.is_dir() or not (c / "case.json").exists():
        continue
    shutil.copy(c / "case.json", b / "case.json")
    if (c / "SETUP_OLD_NOTES.md").exists():
        shutil.copy(c / "SETUP_OLD_NOTES.md", b / "SETUP_OLD_NOTES.md")
    if not (b / "bad").exists():
        os.symlink((c / "bad").resolve(), b / "bad")
    print(b.name, "ready")
