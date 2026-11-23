"""Step (c) of the blocked-control rule, fixed search: python upstream_search.py <case-id>

Lists later commits (up to 180 days after the change) that touch any file the change touched and
whose message matches fix|revert|regress|bug|broke|restore. The adjudicator reads this list; it
does not search further.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

CASES = json.loads(Path("/root/sealed/cases.json").read_text())
CASES = {c["id"]: c for c in CASES} if isinstance(CASES, list) else CASES
OSS = Path("/root/sealed/oss")
case = CASES[sys.argv[1]]
repo = next(p for p in OSS.iterdir() if p.is_dir() and (p.name == case["repo"].replace("/", "_")
                                                        or p.name == case["repo"].split("/")[-1]))


def git(*a: str) -> str:
    """Run git in the clone."""
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout


head = case["head_sha"]
files = [f for f in git("diff", "--name-only", case["base_sha"], head).split() if not re.search(r"test|\.md$|docs/", f)]
when = int(git("log", "-1", "--format=%ct", head).strip())
out = []
for line in git("log", "--format=%H\t%ct\t%s", f"{head}..HEAD", "--", *files).splitlines():
    sha, t, subject = line.split("\t", 2)
    if int(t) - when <= 180 * 86400 and re.search(r"fix|revert|regress|bug|broke|restore", subject, re.I):
        out.append({"sha": sha[:10], "days_after": round((int(t) - when) / 86400), "subject": subject})
print(json.dumps({"case": case["id"], "repo": repo.name, "files": files, "candidates": out}, indent=1))
