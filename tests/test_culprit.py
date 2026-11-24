"""The culprit tracer: bisecting a throwaway repository, the probe contract, the scoring rule."""

import json
import sys
from pathlib import Path

from flywheel import culprit
from flywheel.cli import main

WORKS = "def f(x):\n    return x * 2\n"
BUGGY = "def f(x):\n    return x + 3\n"
BROKEN = "def f(x:\n    return x\n"

PROBE = """import sys

try:
    import mod
except Exception:
    sys.exit(125)
sys.exit(0 if mod.f(2) == 4 else 1)
"""

FLAKY_PROBE = """import sys
from pathlib import Path

counter = Path({counter!r})
runs = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(runs + 1))
sys.exit(runs % 2)
"""


def make_repo(root: Path, sources: list[str]) -> tuple[Path, list[str]]:
    """A repository with one commit per source text; returns it and the commit ids in order."""
    repo = root / "repo"
    repo.mkdir()
    culprit.git(str(repo), "init", "-q")
    culprit.git(str(repo), "config", "user.name", "Test")
    culprit.git(str(repo), "config", "user.email", "test@example.invalid")
    culprit.git(str(repo), "config", "commit.gpgsign", "false")
    shas = []
    for number, source in enumerate(sources):
        (repo / "mod.py").write_text(source)
        (repo / "step.txt").write_text(f"{number}\n")
        culprit.git(str(repo), "add", "-A")
        culprit.git(str(repo), "commit", "-q", "-m", f"step {number}")
        shas.append(culprit.git(str(repo), "rev-parse", "HEAD"))
    return repo, shas


def history(bug_at: int, broken: tuple[int, ...] = (), length: int = 12) -> list[str]:
    """Twelve source texts: working until `bug_at`, buggy from there, some unimportable."""
    return [
        BROKEN if number in broken else (WORKS if number < bug_at else BUGGY)
        for number in range(length)
    ]


def make_case(root: Path, repo: Path, shas: list[str], probe: str = PROBE) -> Path:
    """A case folder from the first and last commit of the repository."""
    case = root / "case"
    case.mkdir()
    config = {
        "repo": str(repo),
        "good": shas[0],
        "bad": shas[-1],
        "python": sys.executable,
        "source_roots": ["."],
    }
    (case / "case.json").write_text(json.dumps(config))
    (case / "probe.py").write_text(probe)
    return case


def run_tracer(case: Path, reps: int = 1) -> dict:
    """Trace a case and return the result."""
    return culprit.Tracer(case, reps, 60).run()


def test_finds_the_commit_that_introduced_the_bug(tmp_path):
    """A clean history gives status found and the exact introducing commit."""
    repo, shas = make_repo(tmp_path, history(bug_at=7, broken=(3,)))
    case = make_case(tmp_path, repo, shas)
    result = run_tracer(case)
    assert result["status"] == "found"
    assert result["culprit"] == shas[7]
    assert result["candidates"] == [shas[7]]
    assert result["window"] == 11


def test_an_unimportable_commit_exits_125_and_is_skipped(tmp_path):
    """A commit whose module cannot be imported is not judged either way."""
    repo, shas = make_repo(tmp_path, history(bug_at=9, broken=(4, 5, 6)))
    case = make_case(tmp_path, repo, shas)
    tracer = culprit.Tracer(case, 1, 60)
    assert tracer.judge(shas[5]) == culprit.SKIP
    assert tracer.tested[shas[5]]["exits"] == [125]
    assert tracer.run()["culprit"] == shas[9]


def test_ambiguous_when_the_unjudgeable_commit_sits_next_to_the_culprit(tmp_path):
    """The commit before the culprit cannot be judged, so both stay as candidates."""
    repo, shas = make_repo(tmp_path, history(bug_at=6, broken=(5,)))
    case = make_case(tmp_path, repo, shas)
    result = run_tracer(case)
    assert result["status"] == "ambiguous"
    assert result["candidates"] == [shas[5], shas[6]]
    assert result["culprit"] == shas[6]


def test_invalid_probe_when_the_probe_fails_at_the_good_end(tmp_path):
    """A probe that already reports the bug at `good` proves nothing."""
    repo, shas = make_repo(tmp_path, [BUGGY] * 12)
    case = make_case(tmp_path, repo, shas)
    result = run_tracer(case)
    assert result["status"] == "invalid_probe"
    assert result["good_state"] == culprit.BAD
    assert result["bad_state"] == culprit.BAD
    assert "culprit" not in result


def test_invalid_probe_when_the_good_end_cannot_be_judged(tmp_path):
    """An unimportable `good` commit is not a good commit."""
    repo, shas = make_repo(tmp_path, history(bug_at=7, broken=(0,)))
    result = run_tracer(make_case(tmp_path, repo, shas))
    assert result["status"] == "invalid_probe"
    assert result["good_state"] == culprit.SKIP


def test_a_flaky_probe_is_treated_as_skip(tmp_path):
    """Alternating exits are neither good nor bad."""
    repo, shas = make_repo(tmp_path, history(bug_at=7))
    counter = tmp_path / "counter.txt"
    case = make_case(tmp_path, repo, shas, FLAKY_PROBE.format(counter=str(counter)))
    tracer = culprit.Tracer(case, 2, 60)
    assert tracer.judge(shas[4]) == culprit.SKIP
    assert sorted(tracer.tested[shas[4]]["exits"]) == [0, 1]
    result = culprit.Tracer(case, 2, 60).run()
    assert result["status"] == "invalid_probe"
    assert result["good_state"] == culprit.SKIP


def test_the_at_mode_runs_the_probe_once(tmp_path, capsys):
    """`--at bad` prints the state and exit code, then the output tail, and writes nothing."""
    repo, shas = make_repo(tmp_path, history(bug_at=7))
    case = make_case(tmp_path, repo, shas)
    assert culprit.trace(str(case), at="bad") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "bad: bad exit=[1]"
    assert not (case / "result.json").exists()


def test_the_cli_prints_and_writes_what_the_script_did(tmp_path, capsys):
    """`flywheel culprit trace` writes result.json and prints it without the long fields."""
    repo, shas = make_repo(tmp_path, history(bug_at=7, broken=(3,)))
    case = make_case(tmp_path, repo, shas)
    assert main(["culprit", "trace", str(case), "--reps", "1", "--timeout", "60"]) == 0
    written = json.loads((case / "result.json").read_text())
    assert written["culprit"] == shas[7]
    assert set(written["tested"]) <= {sha[:12] for sha in shas}
    shown = json.loads(capsys.readouterr().out)
    assert shown == {
        key: value
        for key, value in written.items()
        if key not in ("tested", "culprit", "candidates")
    }
    assert (case / "result.json").read_text() == json.dumps(written, indent=1)


def merged_history(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A repository where a feature branch commit reaches main through a merge commit."""
    repo, shas = make_repo(tmp_path, [WORKS] * 3)
    git = culprit.git
    git(str(repo), "checkout", "-q", "-b", "feature")
    (repo / "mod.py").write_text(BUGGY)
    git(str(repo), "commit", "-q", "-am", "introduce the bug")
    intro = git(str(repo), "rev-parse", "HEAD")
    git(str(repo), "checkout", "-q", "-")
    (repo / "other.txt").write_text("other\n")
    git(str(repo), "add", "-A")
    git(str(repo), "commit", "-q", "-m", "work on the main line")
    git(str(repo), "merge", "-q", "--no-ff", "-m", "merge feature", "feature")
    merge = git(str(repo), "rev-parse", "HEAD")
    (repo / "after.txt").write_text("after\n")
    git(str(repo), "add", "-A")
    git(str(repo), "commit", "-q", "-m", "after the merge")
    after = git(str(repo), "rev-parse", "HEAD")
    return repo, {"before": shas[-1], "intro": intro, "merge": merge, "after": after}


def test_scoring_rule_on_a_linear_history(tmp_path):
    """Correct is the introducing commit itself; its parent and its child are wrong."""
    repo, shas = make_repo(tmp_path, history(bug_at=7))
    repo_path = str(repo)
    assert culprit.is_correct(repo_path, shas[7], shas[7])
    assert not culprit.is_correct(repo_path, shas[7], shas[6])
    assert not culprit.is_correct(repo_path, shas[7], shas[8])
    assert not culprit.is_correct(repo_path, shas[7], "0" * 40)


def test_scoring_rule_accepts_the_merge_commit_that_brought_the_change_in(tmp_path):
    """The merge commit counts, the introducing commit counts, what comes after does not."""
    repo, commits = merged_history(tmp_path)
    repo_path, intro = str(repo), commits["intro"]
    assert culprit.is_correct(repo_path, intro, intro)
    assert culprit.is_correct(repo_path, intro, commits["merge"])
    assert not culprit.is_correct(repo_path, intro, commits["after"])
    assert not culprit.is_correct(repo_path, intro, commits["before"])


def write_key_and_cases(
    root: Path, repo: Path, intro: str, result: dict | None
) -> tuple[Path, Path]:
    """A one-case key file and a cases folder holding that case's case.json and result.json."""
    key = root / "key.json"
    key.write_text(
        json.dumps(
            [
                {"gate_id": "c-1", "set": "S", "kind": "regression", "row": {"intro_sha": intro}},
                {
                    "gate_id": "c-2",
                    "set": "OTHER",
                    "kind": "regression",
                    "row": {"intro_sha": intro},
                },
            ]
        )
    )
    cases = root / "cases"
    (cases / "c-1").mkdir(parents=True)
    (cases / "c-1" / "case.json").write_text(json.dumps({"repo": str(repo)}))
    if result is not None:
        (cases / "c-1" / "result.json").write_text(json.dumps(result))
    return key, cases


def test_score_reads_result_json_and_counts_a_merge_as_correct(tmp_path, capsys):
    """`flywheel culprit score` marks a found merge commit correct and writes --out."""
    repo, commits = merged_history(tmp_path)
    key, cases = write_key_and_cases(
        tmp_path, repo, commits["intro"], {"status": "found", "culprit": commits["merge"]}
    )
    out = tmp_path / "score.json"
    assert main(["culprit", "score", str(key), "S", str(cases), "--out", str(out)]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed[0].startswith("S: correct culprit 1/1 = 100.0% (95% interval ")
    assert printed[1] == "  wrong: none"
    saved = json.loads(out.read_text())
    assert saved["correct"] == ["c-1"] and saved["detail"] == {"c-1": "correct"}


def test_score_counts_ambiguous_and_missing_answers_as_wrong(tmp_path, capsys):
    """An ambiguous result, no result and a wrong answer file all score as wrong."""
    repo, commits = merged_history(tmp_path)
    key, cases = write_key_and_cases(
        tmp_path, repo, commits["intro"], {"status": "ambiguous", "culprit": commits["intro"]}
    )
    culprit.score(str(key), "S", str(cases))
    assert "  wrong: c-1[wrong (ambiguous)]" in capsys.readouterr().out
    (cases / "c-1" / "result.json").unlink()
    culprit.score(str(key), "S", str(cases))
    assert "  wrong: c-1[wrong (no result)]" in capsys.readouterr().out
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({"c-1": commits["after"]}))
    culprit.score(str(key), "S", str(cases), str(answers))
    assert "  wrong: c-1[wrong (answered)]" in capsys.readouterr().out
    answers.write_text(json.dumps({"c-1": commits["intro"]}))
    culprit.score(str(key), "S", str(cases), str(answers))
    assert "correct culprit 1/1" in capsys.readouterr().out
