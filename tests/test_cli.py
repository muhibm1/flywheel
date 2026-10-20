"""The command line, end to end, on the quickstart agent: no network, no keys."""

import json
import shutil
from pathlib import Path

import pytest

from flywheel.cli import main, parse_since
from flywheel.config import ConfigError
from flywheel.dataset import load

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
