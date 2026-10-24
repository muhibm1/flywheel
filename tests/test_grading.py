"""Edits a pull request makes to its own grading: found, listed, and held for a person."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import PASS, experiment

from flywheel.config import load
from flywheel.grading import changes, fingerprints

QUICKSTART = Path(__file__).parent.parent / "examples" / "quickstart"


@pytest.fixture
def branches(tmp_path):
    """Two copies of the quickstart: the base branch and the pull request."""
    base = tmp_path / "base"
    head = tmp_path / "head"
    for target in (base, head):
        shutil.copytree(QUICKSTART, target, ignore=shutil.ignore_patterns("__pycache__"))
    return base, head


def edit_dataset(folder: Path, edit) -> None:
    """Rewrite the dataset file, passing each example's dict through `edit` (None drops it)."""
    path = folder / "dataset.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    kept = [row for row in (edit(row) for row in rows) if row is not None]
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in kept))


def kinds(found) -> list[tuple[str, str]]:
    """The (kind, subject) pairs of a list of changes."""
    return [(change.kind, change.subject) for change in found]


def test_unchanged_branches_have_no_changes(branches):
    """Same config, same dataset, same evaluator code: nothing to approve."""
    base, head = branches
    run = experiment("x", {"a": [PASS]})
    assert changes(run, run, load(head / "flywheel.toml"), load(base / "flywheel.toml")) == []


def test_evaluator_code_change_is_found_from_the_recorded_hashes():
    """A different hash for the same evaluator on the two sides is an edit to the check."""
    base = replace(experiment("base", {"a": [PASS]}), graders={"m:check": "aaa", "m:other": "x"})
    head = replace(experiment("head", {"a": [PASS]}), graders={"m:check": "bbb", "m:other": "x"})
    cfg = load(QUICKSTART / "flywheel.toml")
    assert kinds(changes(base, head, cfg)) == [("evaluator_code", "m:check")]


def test_fingerprints_cover_every_evaluator():
    """`flywheel run` records one hash per configured evaluator."""
    cfg = load(QUICKSTART / "flywheel.toml")
    prints = fingerprints(cfg)
    assert set(prints) == set(cfg.evaluators)
    assert all(len(value) == 12 for value in prints.values())


def test_reference_and_removed_case_are_found(branches):
    """A rewritten expected answer and a deleted case are both edits to the grading."""
    base, head = branches
    rows = [json.loads(line) for line in (base / "dataset.jsonl").read_text().splitlines()]
    first, second = rows[0]["id"], rows[1]["id"]

    def edit(row):
        if row["id"] == first:
            return {**row, "reference_outputs": {"team": "general"}}
        return None if row["id"] == second else row

    edit_dataset(head, edit)
    run = experiment("x", {"a": [PASS]})
    found = changes(run, run, load(head / "flywheel.toml"), load(base / "flywheel.toml"))
    assert sorted(kinds(found)) == sorted([("reference", first), ("case_removed", second)])


def test_added_case_is_not_a_change(branches):
    """Adding a case can only make the gate stricter."""
    base, head = branches
    with (head / "dataset.jsonl").open("a") as handle:
        handle.write(
            json.dumps(
                {
                    "id": "new0000000ab",
                    "inputs": {"message": "new"},
                    "metadata": {},
                    "reference_outputs": {"team": "general"},
                },
                sort_keys=True,
            )
            + "\n"
        )
    run = experiment("x", {"a": [PASS]})
    assert changes(run, run, load(head / "flywheel.toml"), load(base / "flywheel.toml")) == []


def test_removed_evaluator_and_looser_gate_are_found(branches):
    """Dropping a check or raising the tolerance in flywheel.toml needs a person's approval."""
    base, head = branches
    toml = (head / "flywheel.toml").read_text()
    toml = toml.replace(', "agent:not_general_when_specific"', "")
    toml = toml.replace("max_broken = 0", "max_broken = 2")
    (head / "flywheel.toml").write_text(toml)
    run = experiment("x", {"a": [PASS]})
    found = changes(run, run, load(head / "flywheel.toml"), load(base / "flywheel.toml"))
    assert kinds(found) == [
        ("evaluator_removed", "agent:not_general_when_specific"),
        ("gate_setting", "max_broken"),
    ]
    assert found[1].detail == "0 → 2"
