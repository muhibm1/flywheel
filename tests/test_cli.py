"""The command line, end to end, on the quickstart agent: no network, no keys."""

import json
import shutil
from pathlib import Path

import pytest
from conftest import experiment

from flywheel import spend
from flywheel.cli import main, parse_since
from flywheel.config import Config, ConfigError
from flywheel.dataset import load
from flywheel.experiment import Experiment

QUICKSTART = Path(__file__).parent.parent / "examples" / "quickstart"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A copy of the quickstart, so tests can change its dataset."""
    target = tmp_path / "quickstart"
    shutil.copytree(QUICKSTART, target, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.chdir(target)
    monkeypatch.setenv("FLYWHEEL_GIT_SHA", "0" * 40)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return target


def test_gate_passes_with_no_change(workspace, capsys):
    """The same agent on both sides passes."""
    assert main(["run", "--label", "base", "--out", "base.json"]) == 0
    assert main(["run", "--label", "head", "--out", "head.json"]) == 0
    assert main(["gate", "--base", "base.json", "--head", "head.json"]) == 0
    assert "no regressions" in capsys.readouterr().out


def test_gate_pools_several_base_runs(workspace, capsys):
    """`--base` takes several runs of main and pools them."""
    main(["run", "--label", "base1", "--out", "b1.json"])
    main(["run", "--label", "base2", "--out", "b2.json"])
    main(["run", "--label", "head", "--out", "head.json"])
    assert main(["gate", "--base", "b1.json", "b2.json", "--head", "head.json"]) == 0
    assert "`base1 + base2`" in capsys.readouterr().out


def test_gate_blocks_the_regression(workspace, monkeypatch, tmp_path):
    """The refund rule dropped: the refund case breaks and the gate exits 1 with a report."""
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    main(["run", "--label", "base", "--out", "base.json"])
    monkeypatch.setenv("QUICKSTART_REGRESSION", "1")
    main(["run", "--label", "head", "--out", "head.json"])
    code = main(["gate", "--base", "base.json", "--head", "head.json", "--report", "r.md"])
    assert code == 1
    report = Path("r.md").read_text()
    assert "I want a refund" in report
    assert summary.read_text() == report


def test_a_spend_stop_exits_1_in_one_line_and_saves_nothing(workspace, monkeypatch, capsys):
    """A refused call ends `flywheel run` before an experiment a gate could read is written."""

    def refused(inputs):
        raise spend.SpendRefused("a call to claude-haiku-5-5 refused: paid calls are off")

    monkeypatch.setattr(Config, "target_callable", lambda self: refused)
    assert main(["run", "--label", "head", "--out", "head.json"]) == 1
    assert "flywheel: the run stopped: SpendRefused: a call to" in capsys.readouterr().err
    assert not Path("head.json").exists()


def test_mine_then_promote(workspace, capsys):
    """Failing traces exported to a file become candidates, then dataset cases."""
    runs = [
        {
            "id": "r1",
            "name": "router",
            "inputs": {"message": "My card was charged twice"},
            "feedback": {"correct_team": 0},
            "nodes": [{"name": "route"}],
            "url": "https://smith.example/r1",
        },
        {
            "id": "r2",
            "name": "router",
            "inputs": {"message": "hi"},
            "feedback": {"correct_team": 1},
        },
    ]
    Path("runs.json").write_text(json.dumps(runs))
    assert main(["mine", "--from-file", "runs.json", "--out", "cand.jsonl"]) == 0
    candidates = load(Path("cand.jsonl"))
    assert len(candidates) == 1
    assert candidates[0].metadata["trace"] == "https://smith.example/r1"

    # No reference yet: promotion refuses until a person writes one.
    assert main(["promote", "cand.jsonl"]) == 2
    line = json.loads(Path("cand.jsonl").read_text())
    line["reference_outputs"] = {"team": "billing"}
    Path("cand.jsonl").write_text(json.dumps(line) + "\n")
    before = len(load(Path("dataset.jsonl")))
    assert main(["promote", "cand.jsonl"]) == 0
    after = load(Path("dataset.jsonl"))
    assert len(after) == before + 1
    assert after[-1].metadata["needs_review"] is False
    # Promoting twice adds nothing.
    assert main(["promote", "cand.jsonl"]) == 0
    assert len(load(Path("dataset.jsonl"))) == before + 1


def test_config_errors_exit_2(workspace, capsys):
    """A missing config is a usage error."""
    assert main(["--config", "nope.toml", "run", "--label", "x", "--out", "x.json"]) == 2
    assert "flywheel:" in capsys.readouterr().err


def test_parse_since():
    """Durations parse; nonsense is a config error."""
    assert parse_since(None) is None
    assert parse_since("7d") is not None
    with pytest.raises(ConfigError):
        parse_since("a week")


def test_run_only_keeps_the_whole_files_version_so_runs_pool(workspace, capsys):
    """A run of a few cases names the same dataset version, so it pools with a full run."""
    main(["run", "--label", "base", "--out", "base.json"])
    first = load(Path("dataset.jsonl"))[0].id
    main(["run", "--label", "extra", "--only", first, "--out", "extra.json"])
    full = json.loads(Path("base.json").read_text())
    extra = json.loads(Path("extra.json").read_text())
    assert full["dataset_version"] == extra["dataset_version"]
    assert set(extra["examples"]) == {first}
    assert full["graders"] and full["graders"] == extra["graders"]
    main(["run", "--label", "head", "--out", "head.json"])
    capsys.readouterr()
    code = main(["gate", "--base", "base.json", "extra.json", "--head", "head.json", "extra.json"])
    assert code == 0
    assert "and 2 times for the 1 close call" in capsys.readouterr().out


def test_close_calls_prints_json(workspace, capsys):
    """`close-calls` prints the ids, the repetitions and where to number them from; with
    repetitions 0 it lists none."""
    main(["run", "--label", "base", "--out", "base.json"])
    main(["run", "--label", "head", "--out", "head.json"])
    capsys.readouterr()
    assert main(["close-calls", "--base", "base.json", "--head", "head.json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "ids": [],
        "repetitions": 0,
        "first_repetition": 1,
    }


def test_extra_runs_are_numbered_after_the_first_ones(workspace, capsys):
    """A close call's extra runs start after the runs it has, so recorded answers keyed by
    repetition are not replayed as new runs; `run --first-repetition` numbers them."""
    passed, failed = {"correct_team": 1.0}, {"correct_team": 0.0}
    base = experiment("base", {"x": [passed] * 3})
    head = experiment("head", {"x": [passed, passed, failed]})
    base.save(Path("base.json"))
    head.save(Path("head.json"))
    args = ["close-calls", "--base", "base.json", "--head", "head.json", "--repetitions", "2"]
    assert main(args) == 0
    calls = json.loads(capsys.readouterr().out)
    assert calls == {"ids": ["x"], "repetitions": 2, "first_repetition": 4}
    more = ["run", "--label", "more", "--out", "more.json", "--repetitions", "2"]
    assert main([*more, "--first-repetition", "4"]) == 0
    assert {run.repetition for run in Experiment.load(Path("more.json")).runs} == {4, 5}


def test_gate_holds_an_edited_expected_answer_until_approved(workspace, tmp_path, capsys):
    """A pull request that rewrites an expected answer is blocked until a person approves."""
    base_branch = tmp_path / "base-branch"
    shutil.copytree(workspace, base_branch)
    rows = [json.loads(line) for line in Path("dataset.jsonl").read_text().splitlines()]
    rows[0]["reference_outputs"] = {"team": "general"}
    Path("dataset.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    main(["run", "--label", "base", "--out", "base.json"])
    main(["run", "--label", "head", "--out", "head.json"])
    capsys.readouterr()
    args = ["gate", "--base", "base.json", "--head", "head.json"]
    args += ["--base-config", str(base_branch / "flywheel.toml")]
    assert main(args) == 1
    out = capsys.readouterr().out
    assert "changes how it is graded" in out
    assert f"Expected answer changed: `{rows[0]['id']}`" in out
    assert main([*args, "--approve-grading"]) == 0
    assert "A person approved these edits." in capsys.readouterr().out
