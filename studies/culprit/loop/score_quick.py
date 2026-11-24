"""Score the quick head-to-head (Flywheel vs a plain Opus loop) on the cases in /home/user/fw/Q.json.

Usage: python3 score_quick.py

Flywheel: proven when result.json says `found` and the commit is right; `found` with a wrong
commit is a false proof. Opus loop: the named commit is checked the same way; its proof.py is run
3 times at the named commit and 3 times at that commit's first parent (exit 1 every time at the
commit, 0 every time at the parent). Proven = right commit and a proof that holds; a false proof =
a proof that holds at a wrong commit. Prints per-case lines and totals; writes quick_scores.json.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, "/home/user/flywheel/src")
from flywheel.culprit import export_tree, git, is_correct, wilson  # noqa: E402

KEY = "/mnt/project-files/flywheel/change-probes/sealed/sets/key.json"
key = {r["gate_id"]: r for r in json.load(open(KEY)) if r["set"] == "H2" and r["kind"] == "regression"}
ids = [x["gate_id"] for x in json.load(open("/home/user/fw/Q.json"))]
FW, LOOP = Path("/home/user/fw/culprit/H2"), Path("/home/user/fw/culprit/H2-loop")
RUN = "/home/user/flywheel/studies/culprit/loop/run_in_tree.py"


def run_proof(case: Path, repo: str, sha: str) -> list:
    """Run proof.py three times in an exported tree at sha; return the exit codes."""
    d = Path(tempfile.mkdtemp(prefix="qproof-"))
    try:
        export_tree(repo, sha, d / "t")
        shutil.copy(case / "proof.py", d / "proof.py")
        codes = []
        for _ in range(3):
            try:
                codes.append(subprocess.run(["python3", RUN, str(case), str(d / "proof.py")], cwd=d / "t",
                                            capture_output=True, timeout=300).returncode)
            except subprocess.TimeoutExpired:
                codes.append("timeout")
        return codes
    finally:
        shutil.rmtree(d, ignore_errors=True)


out, tot = {}, {"fw_proven": 0, "fw_false": 0, "loop_named": 0, "loop_proven": 0, "loop_false": 0, "loop_proof_holds": 0}
for gid in ids:
    r = key[gid]
    repo = json.loads((FW / gid / "case.json").read_text())["repo"]
    intro = r["row"]["intro_sha"]
    res = json.loads((FW / gid / "result.json").read_text()) if (FW / gid / "result.json").exists() else {}
    st, c = res.get("status", "no result"), res.get("culprit")
    fw_ok = st == "found" and bool(c) and is_correct(repo, intro, c)
    tot["fw_proven"] += fw_ok
    tot["fw_false"] += st == "found" and not fw_ok
    a = {}
    if (LOOP / gid / "answer.json").exists():
        try:
            a = json.loads((LOOP / gid / "answer.json").read_text())
        except ValueError:
            a = {}
    sha = a.get("sha")
    named = bool(sha) and is_correct(repo, intro, sha)
    holds, codes = False, None
    if sha and (LOOP / gid / "proof.py").exists():
        try:
            parent = git(repo, "rev-parse", f"{sha}^1")
            codes = {"culprit": run_proof(LOOP / gid, repo, sha), "parent": run_proof(LOOP / gid, repo, parent)}
            holds = codes["culprit"] == [1, 1, 1] and codes["parent"] == [0, 0, 0]
        except Exception as e:  # unresolvable sha and the like
            codes = {"error": str(e)[:200]}
    tot["loop_named"] += named
    tot["loop_proof_holds"] += holds
    tot["loop_proven"] += named and holds
    tot["loop_false"] += holds and not named
    out[gid] = {"flywheel": {"status": st, "correct": fw_ok}, "loop": {"named_correct": named, "proof_holds": holds,
                                                                     "codes": codes, "confidence": a.get("confidence")}}
    print(gid, "| flywheel", st, "RIGHT" if fw_ok else "-", "| loop named", "RIGHT" if named else "wrong",
          "proof", "holds" if holds else f"fails {codes}", flush=True)
n = len(ids)
for k in ("fw_proven", "loop_proven", "loop_named"):
    lo, hi = wilson(tot[k], n)
    print(f"{k}: {tot[k]}/{n} (95% interval {100*lo:.0f} to {100*hi:.0f})")
print("false proofs: flywheel", tot["fw_false"], "loop", tot["loop_false"], "| loop proofs that hold:", tot["loop_proof_holds"])
Path("/home/user/fw/quick_scores.json").write_text(json.dumps({"totals": tot, "cases": out}, indent=1))
