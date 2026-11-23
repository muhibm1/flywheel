"""List candidate (introducing change, fix) pairs in one clone, from git history alone.

Usage: python find_candidates.py <clone_dir> <out.json> [--since 2026-07-01] [--max-lines 2000]

A candidate is a fix commit on the default branch (subject says fix, revert, regression or
restore; touches source and adds or changes a test) paired with an earlier commit, dated on or
after --since, that last wrote the source lines the fix replaced (git blame on the fix's parent),
or that the fix message names by pull request number or hash. This only proposes pairs. A pair
becomes a regression in the key only after a witness test passes before the introducing change,
fails after it and passes after the fix.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

FIX = re.compile(r"\b(fix(e[sd])?|revert(s|ed)?|regress(ion|ed)?|restore[sd]?|hotfix|broke[n]?)\b", re.I)
SKIP_SUBJECT = re.compile(r"^(chore|docs?|ci|build|style|release|bump|deps?)\b|typo|lint|flaky", re.I)
PR_REF = re.compile(r"#(\d{1,6})\b")
SHA_REF = re.compile(r"\b[0-9a-f]{7,40}\b")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")
TEST = re.compile(r"(^|/)(tests?|testing|__tests__|spec)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
NOT_SOURCE = re.compile(r"(^|/)(docs?|examples?|cookbook|\.github|benchmarks?|scripts)/|\.(md|rst|txt|lock|toml|ya?ml|json|cfg|ini|ipynb)$")


def git(clone: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True,
                          errors="replace").stdout


def is_test(path: str) -> bool:
    return bool(TEST.search(path))


def is_source(path: str) -> bool:
    return path.endswith(".py") and not is_test(path) and not NOT_SOURCE.search(path)


def numstat(clone: Path, sha: str) -> list[tuple[int, int, str]]:
    rows = []
    for line in git(clone, "show", "--numstat", "--format=", "--no-renames", sha).splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]), parts[2]))
    return rows


def replaced_lines(clone: Path, sha: str, path: str) -> list[tuple[int, int]]:
    """Old-side line ranges of `path` that the commit deleted or replaced."""
    out = []
    for line in git(clone, "show", "--unified=0", "--format=", "--no-renames", sha, "--", path).splitlines():
        m = HUNK.match(line)
        if m:
            start, count = int(m.group(1)), int(m.group(2) or "1")
            if count:
                out.append((start, count))
    return out


def blame(clone: Path, rev: str, path: str, start: int, count: int) -> list[str]:
    text = git(clone, "blame", "--line-porcelain", "-w", "-L", f"{start},+{count}", rev, "--", path)
    return [ln.split()[0] for ln in text.splitlines() if re.match(r"^[0-9a-f]{40} \d+ \d+", ln)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("clone")
    ap.add_argument("out")
    ap.add_argument("--since", default="2026-07-01")
    ap.add_argument("--max-lines", type=int, default=2000)
    a = ap.parse_args()
    clone = Path(a.clone)

    log = git(clone, "log", "--first-parent", f"--since={a.since}", "--no-merges",
              "--format=%H%x1f%cI%x1f%s%x1f%b%x1e")
    commits = {}
    order = []
    for rec in log.split("\x1e"):
        parts = rec.strip("\n").split("\x1f")
        if len(parts) < 4:
            continue
        sha, date, subject, body = parts[0], parts[1], parts[2], parts[3]
        commits[sha] = {"sha": sha, "date": date[:10], "subject": subject, "body": body}
        order.append(sha)
    by_pr = {}
    for sha in order:
        m = re.search(r"\(#(\d+)\)\s*$", commits[sha]["subject"])
        if m:
            by_pr[m.group(1)] = sha

    rows = []
    for sha in order:
        c = commits[sha]
        if not FIX.search(c["subject"]) or SKIP_SUBJECT.search(c["subject"]):
            continue
        stat = numstat(clone, sha)
        src = [(add, rem, p) for add, rem, p in stat if is_source(p)]
        tests = [p for add, rem, p in stat if is_test(p) and p.endswith(".py") and add > 0]
        if not src or not tests or sum(add + rem for add, rem, _ in src) > 400:
            continue
        votes: Counter[str] = Counter()
        for add, rem, path in src:
            for start, count in replaced_lines(clone, sha, path):
                for owner in blame(clone, sha + "^", path, start, count):
                    votes[owner] += 1
        text = c["subject"] + "\n" + c["body"]
        own_pr = re.search(r"\(#(\d+)\)\s*$", c["subject"])
        named = set()
        for n in PR_REF.findall(text):
            if own_pr and n == own_pr.group(1):
                continue
            if n in by_pr and by_pr[n] != sha:
                named.add(by_pr[n])
        for h in SHA_REF.findall(text):
            for full in order:
                if full.startswith(h) and full != sha:
                    named.add(full)
        total = sum(votes.values())
        intros = []
        for owner in set(votes) | named:
            if owner not in commits or owner == sha:
                continue  # older than --since, or off the default branch
            ic = commits[owner]
            if ic["date"] > c["date"]:
                continue
            istat = numstat(clone, owner)
            isrc = sum(add + rem for add, rem, p in istat if is_source(p))
            if isrc == 0 or isrc > a.max_lines:
                continue
            intros.append({"intro_sha": owner, "intro_date": ic["date"], "intro_title": ic["subject"],
                           "base_sha": git(clone, "rev-parse", owner + "^").strip(),
                           "changed_source_lines": isrc, "blamed_lines": votes.get(owner, 0),
                           "blame_share": round(votes.get(owner, 0) / total, 2) if total else 0.0,
                           "named_in_fix": owner in named})
        intros = [i for i in intros if i["named_in_fix"] or i["blame_share"] >= 0.5]
        if not intros:
            continue
        intros.sort(key=lambda i: (i["named_in_fix"], i["blame_share"]), reverse=True)
        rows.append({"fix_sha": sha, "fix_date": c["date"], "fix_title": c["subject"],
                     "fix_body": c["body"][:3000], "fix_test_paths": tests,
                     "fix_source_paths": [p for _, _, p in src], "intros": intros[:2]})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rows, indent=1))
    print(f"{clone.name}: {len(order)} commits since {a.since}, {len(rows)} candidate fixes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
