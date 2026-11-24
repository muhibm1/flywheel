"""Build the plain-Opus-loop case folders for the quick test. Usage: python3 prep_loop.py [repo|files]

repo:  /home/user/fw/culprit/H2-loop/<id>/repo, a fresh shallow clone from GitHub that ends at the
       broken version (no later commits, no tags, no remote), with history from a month before
       the working version.
files: copies REPORT.md and SETUP_OLD_NOTES.md from the Flywheel case folder and writes case.json
       (good, bad, python, source_roots). Prints ids only.
"""
import json, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

q = json.load(open("/home/user/fw/Q.json"))
src, dst = Path("/home/user/fw/culprit/H2"), Path("/home/user/fw/culprit/H2-loop")
repos = dict(l.split() for l in Path("/home/user/fw/h2_repos.txt").read_text().splitlines() if l.strip())


def g(d, *a):
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, check=True).stdout.strip()


def repo(x):
    gid = x["gate_id"]
    cfg = json.loads((src / gid / "case.json").read_text())
    r = dst / gid / "repo"
    if (r / ".git").exists():
        return gid + " exists"
    r.mkdir(parents=True)
    day = g(cfg["repo"], "log", "-1", "--format=%cs", cfg["good"])
    since = subprocess.run(["date", "-d", f"{day} -30 days", "+%Y-%m-%d"], capture_output=True, text=True).stdout.strip()
    g(r, "init", "-q")
    g(r, "fetch", "-q", "--no-tags", f"--shallow-since={since}", f"https://github.com/{repos[x['project']]}.git", f"{cfg['bad']}:refs/heads/main")
    g(r, "checkout", "-q", "main")
    ok = subprocess.run(["git", "-C", str(r), "cat-file", "-e", cfg["good"]]).returncode == 0
    n = g(r, "rev-list", "--count", "HEAD")
    return f"{gid} commits {n} good_present {ok}"


def files(x):
    gid = x["gate_id"]
    cfg = json.loads((src / gid / "case.json").read_text())
    d = dst / gid
    for f in ("REPORT.md", "SETUP_OLD_NOTES.md"):
        if (src / gid / f).exists():
            shutil.copy(src / gid / f, d / f)
    (d / "case.json").write_text(json.dumps({"good": cfg["good"], "bad": cfg["bad"], "python": cfg["python"],
                                             "python_fallbacks": cfg.get("python_fallbacks", []),
                                             "source_roots": cfg["source_roots"]}, indent=1))
    return gid + " files " + " ".join(sorted(p.name for p in d.iterdir()))


fn = repo if sys.argv[1] == "repo" else files
with ThreadPoolExecutor(4) as ex:
    for line in ex.map(fn, q):
        print(line, flush=True)
