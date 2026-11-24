"""Pick one matched harmless change (a control) for every proven regression of a project.

usage: pick_controls.py <clone> <project> <sealed folder> [--rows audited|labelled]

A control is a change on the same main line as the regression, close in date and size, touching
source, old enough that a problem would have been reported (30 days before the newest commit), and
never named by a later commit (by pull request number, by hash, or as a revert). It is also never a
change that any mined, candidate or labelled row names as introducing or fixing a regression.
Prints counts only; rows go to <sealed>/controls/<project>.json.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

SINCE = "2026-07-01"
MAX_LINES = 2000
SKIP_SUBJECT = re.compile(
    r"^(chore|docs?|ci|build|style|release|bump|version|deps?|test|tests)[(:! ]|"
    r"^(merge branch|merge remote|update changelog|update readme|bump )|"
    r"^v?\d+\.\d+(\.\d+)?\b", re.I)
REVERT = re.compile(r"^revert\b", re.I)
NOT_SOURCE = re.compile(r"(^|/)(tests?|testing|docs?|examples?|cookbook|benchmarks?|scripts|\.github)/|"
                        r"(^|/)(test_[^/]*|[^/]*_test|conftest)\.py$", re.I)
PR_NUM = re.compile(r"\(#(\d+)\)\s*$|^Merge pull request #(\d+)")


def git(clone, *args, timeout=600):
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True,
                          timeout=timeout).stdout


def is_source(path):
    return path.endswith(".py") and not NOT_SOURCE.search(path)


def shas_in(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and "sha" in k.lower() and re.fullmatch(r"[0-9a-f]{7,40}", v):
                out.add(v)
            else:
                shas_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            shas_in(v, out)


def source_lines(clone, sha):
    n = 0
    for line in git(clone, "diff", "--numstat", f"{sha}^1", sha).splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].isdigit() and is_source(parts[2]):
            n += int(parts[0]) + int(parts[1])
    return n


def main():
    clone, project, sealed = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    rows_dir = sys.argv[sys.argv.index("--rows") + 1] if "--rows" in sys.argv else "labelled"
    rows = [r for r in json.loads((sealed / rows_dir / f"{project}.json").read_text()) if r.get("kept")]
    if not rows:
        print(project, "regressions 0 controls 0")
        return
    named = set()
    for sub in ("mined", "candidates", "labelled", "audited"):
        f = sealed / sub / f"{project}.json"
        if f.exists():
            shas_in(json.loads(f.read_text()), named)

    def is_named(sha):
        return any(sha.startswith(n) or n.startswith(sha[:7]) for n in named)

    # the main line is the line the regressions sit on: walk first parents from the newest fix
    tip = git(clone, "rev-parse", "HEAD").strip()
    log = git(clone, "log", "--first-parent", f"--since={SINCE}", "--raw", "--no-abbrev",
              "--diff-merges=first-parent", "--format=%x01%H%x02%cs%x02%s", tip)
    commits = []
    for block in log.split("\x01")[1:]:
        head, _, raw = block.partition("\n")
        sha, date, subject = head.split("\x02", 2)
        paths = [l.split("\t")[-1] for l in raw.splitlines() if l.startswith(":")]
        commits.append({"sha": sha, "date": date, "subject": subject,
                        "src": sum(1 for p in paths if is_source(p))})
    if not commits:
        print(project, "regressions", len(rows), "controls 0 (no history)")
        return
    newest = datetime.fromisoformat(commits[0]["date"])
    later_text = git(clone, "log", "--all", f"--since={SINCE}", "--format=%x01%H%x02%cs%x02%B")
    later = []
    for block in later_text.split("\x01")[1:]:
        sha, date, body = block.split("\x02", 2)
        later.append((sha, date, body))

    def named_later(c):
        m = PR_NUM.search(c["subject"])
        num = (m.group(1) or m.group(2)) if m else None
        for sha, date, body in later:
            if sha == c["sha"] or date < c["date"]:
                continue
            if c["sha"][:7] in body:
                return True
            if num and re.search(rf"#{num}\b", body):
                return True
            if REVERT.match(body) and c["subject"][:50] in body:
                return True
        return False

    used, out = set(), []
    for r in rows:
        target = datetime.fromisoformat(r["intro_date"][:10])
        size = max(int(r.get("changed_source_lines") or 0), 10)
        pool = [c for c in commits
                if c["src"] and c["sha"] not in used and not is_named(c["sha"])
                and not SKIP_SUBJECT.search(c["subject"]) and not REVERT.match(c["subject"])
                and newest - datetime.fromisoformat(c["date"]) >= timedelta(days=30)
                and abs((datetime.fromisoformat(c["date"]) - target).days) <= 75]
        pool.sort(key=lambda c: abs((datetime.fromisoformat(c["date"]) - target).days))
        best = None
        for c in pool[:40]:
            if named_later(c):
                continue
            n = source_lines(clone, c["sha"])
            if not 5 <= n <= MAX_LINES:
                continue
            ratio = max(n, size) / max(min(n, size), 1)
            if ratio <= 2.5:
                best = (c, n)
                break
            if best is None or ratio < best[2]:
                best = (c, n, ratio)
        if best is None:
            continue
        c, n = best[0], best[1]
        used.add(c["sha"])
        out.append({"repo": r["repo"], "head_sha": c["sha"],
                    "base_sha": git(clone, "rev-parse", f"{c['sha']}^1").strip(),
                    "date": c["date"], "title": c["subject"], "changed_source_lines": n,
                    "paired_intro_sha": r["intro_sha"], "python": r.get("python"),
                    "install": r.get("install"), "source_root": r.get("source_root")})
    dest = sealed / "controls"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{project}.json").write_text(json.dumps(out, indent=1))
    print(project, "regressions", len(rows), "controls", len(out))


if __name__ == "__main__":
    main()
