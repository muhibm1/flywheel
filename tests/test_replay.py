"""Tests for replay: mining, hiding the future, the fairness check and scoring."""

import json
import subprocess
from pathlib import Path

import pytest

from flywheel import replay


def git(root: Path, *args: str) -> str:
    """Run git in `root`."""
    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path):
    """A repository with one fix commit that changes code and its test."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "a@b.c")
    git(root, "config", "user.name", "t")
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (root / "tests" / "test_calc.py").write_text("print('placeholder')\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "start")
    (root / "src" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "tests" / "test_calc.py").write_text(
        "import sys\nsys.path.insert(0, 'src')\nfrom calc import add\nassert add(2, 3) == 5\n"
    )
    git(root, "add", "-A")
    git(root, "commit", "-qm", "fix: add subtracted instead of adding\n\nadd(2, 3) gave -1.")
    spec = replay.RepoSpec(
        "toy", str(root), "python3 {tests}", ("src/**/*.py",), ("tests/**/test_*.py",), {}
    )
    return spec


def test_mine_finds_the_fix_commit(repo):
    cases = replay.mine(repo, since="2000-01-01")
    assert [c.subject for c in cases] == ["fix: add subtracted instead of adding"]
    assert cases[0].tests == ("tests/test_calc.py",)
    assert "add(2, 3) gave -1." in cases[0].task


def test_future_is_hidden_and_tests_are_overlaid(repo, tmp_path):
    case = replay.mine(repo, since="2000-01-01")[0]
    work = tmp_path / "work"
    replay.materialize(repo, case, work, at="parent", tests=False)
    assert "a - b" in (work / "src" / "calc.py").read_text()
    assert not (work / ".git").exists()  # no history to read the fix from
    replay.overlay_tests(repo, case, work)
    assert "assert add(2, 3) == 5" in (work / "tests" / "test_calc.py").read_text()


def test_fair_case_fails_before_and_passes_after(repo, tmp_path):
    case = replay.mine(repo, since="2000-01-01")[0]
    verdict = replay.check_fair(repo, case, tmp_path / "scratch")
    assert verdict["fair"], verdict


def test_case_needing_a_new_name_is_not_fair(repo, tmp_path):
    case = replay.mine(repo, since="2000-01-01")[0]
    root = Path(repo.path)
    (root / "src" / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b\n"
    )
    (root / "tests" / "test_calc.py").write_text("from calc import mul\nassert mul(2, 3) == 6\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "fix: add mul")
    cases = replay.mine(repo, since="2000-01-01")
    verdict = replay.check_fair(repo, cases[0], tmp_path / "scratch")
    assert not verdict["fair"]
    assert "name or option" in verdict["reason"]
    assert case.id != cases[0].id


def stream(result: dict, tool_input: dict | None = None) -> str:
    """A fake `claude --output-format stream-json` output."""
    events = []
    if tool_input:
        events.append(
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "input": tool_input}]},
            }
        )
    events.append({"type": "result", **result})
    return "\n".join(json.dumps(e) for e in events)


def fake_agent(fixed: bool, tool_input: dict | None = None):
    """A runner that edits the working copy like an agent would, then reports usage."""

    def runner(cmd, cwd, **_):
        assert "bypassPermissions" not in cmd
        if fixed:
            path = Path(cwd) / "src" / "calc.py"
            path.write_text(path.read_text().replace("a - b", "a + b"))
        out = stream(
            {"num_turns": 3, "usage": {"input_tokens": 10, "output_tokens": 5}}, tool_input
        )
        return subprocess.CompletedProcess(cmd, 0, out, "")

    return runner


def test_agent_run_passes_when_the_real_tests_pass(repo, tmp_path):
    case = replay.mine(repo, since="2000-01-01")[0]
    rec = replay.run_agent(
        repo, case, model="m", rep=0, out_dir=tmp_path / "o", runner=fake_agent(True)
    )
    assert rec["passed"] and rec["tokens"] == 15 and not rec["flags"]


def test_agent_run_fails_when_the_change_is_wrong(repo, tmp_path):
    case = replay.mine(repo, since="2000-01-01")[0]
    rec = replay.run_agent(
        repo, case, model="m", rep=0, out_dir=tmp_path / "o", runner=fake_agent(False)
    )
    assert not rec["passed"]


def test_peeking_at_history_is_flagged_and_left_out_of_the_rate(repo, tmp_path):
    case = replay.mine(repo, since="2000-01-01")[0]
    peek = {"command": f"git -C {repo.path} log -p"}
    rec = replay.run_agent(
        repo, case, model="m", rep=0, out_dir=tmp_path / "o", runner=fake_agent(True, peek)
    )
    assert rec["flags"]
    summary = replay.summarize([rec])["m"]
    assert summary["scored"] == 0 and summary["flagged"] == 1


def test_wilson_interval_brackets_the_rate():
    low, high = replay.wilson(18, 20)
    assert low < 0.9 < high
    assert replay.wilson(0, 0) == (0.0, 0.0)


def test_a_crashed_agent_is_retried_and_not_counted(repo, tmp_path):
    case = replay.mine(repo, since="2000-01-01")[0]

    def crashed(cmd, cwd, **_):
        out = stream({"is_error": True, "result": "usage limit reached", "num_turns": 1})
        return subprocess.CompletedProcess(cmd, 1, out, "")

    out = tmp_path / "o"
    rec = replay.run_agent(repo, case, model="m", rep=0, out_dir=out, runner=crashed)
    assert rec["agent_error"] and "usage limit" in rec["error_text"]
    summary = replay.summarize([rec])["m"]
    assert summary["scored"] == 0 and summary["agent_errors"] == 1
    rec = replay.run_agent(repo, case, model="m", rep=0, out_dir=out, runner=fake_agent(True))
    assert rec["passed"] and not rec["agent_error"]


def test_finish_state_reads_edits_and_checks_from_the_stream(tmp_path):
    def use(i, name, inp):
        return {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]},
        }

    def result(i, error=False):
        return {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": i, "is_error": error}]},
        }

    cwd = str(tmp_path)
    events = [use("1", "Edit", {"file_path": f"{cwd}/a.py"}), result("1")]
    assert replay.finish_state(events, cwd) == {
        "edited_code": True,
        "verified_finish": False,
        "hook_blocks": 0,
    }
    events += [use("2", "Bash", {"command": "pytest -q"}), result("2")]
    assert replay.finish_state(events, cwd)["verified_finish"]
    events += [use("3", "Bash", {"command": "pytest -q"}), result("3", error=True)]
    assert not replay.finish_state(events, cwd)["verified_finish"]


def test_run_all_stops_at_the_usage_limit(repo, tmp_path, monkeypatch):
    case = replay.mine(repo, since="2000-01-01")[0]
    calls = []

    def limited(spec, c, *, model, rep, out_dir, **_):
        calls.append(rep)
        return {
            "case": c.id,
            "model": model,
            "rep": rep,
            "agent_error": True,
            "error_text": "You've hit your 5-hour limit",
        }

    monkeypatch.setattr(replay, "run_agent", limited)
    done = replay.run_all({repo.name: repo}, [case], ["m"], 20, tmp_path, workers=1)
    assert len(done) == 1 and len(calls) < 20
