"""Build held-out culprit cases without gate folders. Prints ids, window sizes and counts only.

Usage: python3 make_h_cases.py <SET>

Case folder /home/user/fw/culprit/<SET>/<gate_id>/: case.json and bad/ (tree just before the fix).
Environment inputs /home/user/fw/envprep/<SET>/<project>/hints.json: python version, the recorded
install notes and the case folders of that project. The answer stays in the sealed key. The window
offset is seeded by the gate id (same rule as the practice set).
"""
import hashlib, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, "/home/user/flywheel/studies/culprit")
from trace import export_tree, git  # noqa: E402

s = sys.argv[1]
key = [r for r in json.load(open("/mnt/project-files/flywheel/change-probes/sealed/sets/key.json")) if r["set"] == s and r["kind"] == "regression"]
root = Path("/home/user/fw/culprit") / s
prep = Path("/home/user/fw/envprep") / s
hints, built, skipped = {}, 0, 0
for r in sorted(key, key=lambda x: x["gate_id"]):
    row, gid, proj = r["row"], r["gate_id"], r["project"]
    repo = str(Path("/home/user/fw/clones") / proj)
    offset = 40 + int(hashlib.sha256(gid.encode()).hexdigest(), 16) % 81
    try:
        good = git(repo, "rev-parse", f"{row['intro_sha']}~{offset}")
        bad = git(repo, "rev-parse", f"{row['fix_sha']}~1")
        chain = git(repo, "rev-list", "--first-parent", "--reverse", f"{good}..{bad}").split()
    except RuntimeError:
        print(gid, "SKIPPED cannot resolve the window")
        skipped += 1
        continue
    owners = [c for c in chain if subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", row["intro_sha"], c]).returncode == 0]
    if not owners:
        print(gid, "SKIPPED answer not inside the window")
        skipped += 1
        continue
    c = root / gid
    if not (c / "case.json").exists():
        c.mkdir(parents=True, exist_ok=True)
        (c / "case.json").write_text(json.dumps({"repo": repo, "good": good, "bad": bad,
                                                 "python": f"/home/user/fw/envs/{proj}/bin/python",
                                                 "source_roots": [row.get("source_root") or "."]}, indent=1))
        export_tree(repo, bad, c / "bad")
    day = git(repo, "log", "-1", "--format=%cs", bad)
    h = hints.setdefault(proj, {"project": proj, "env": f"/home/user/fw/envs/{proj}", "python_version": set(), "install_notes": [], "cases": []})
    h["python_version"].add(str(row.get("python")))
    if row.get("install") and row["install"] not in h["install_notes"]:
        h["install_notes"].append(row["install"])
    h["cases"].append({"folder": str(c), "broken_version_date": day})
    built += 1
    print(gid, "window", len(chain))
for proj, h in hints.items():
    h["python_version"] = sorted(h["python_version"])
    d = prep / proj
    d.mkdir(parents=True, exist_ok=True)
    (d / "hints.json").write_text(json.dumps(h, indent=1))
print("built", built, "skipped", skipped, "projects", len(hints))
