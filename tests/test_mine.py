"""Mining: which runs are failures, where they failed, and what becomes a candidate."""

from flywheel.config import FailureRule, MineSettings
from flywheel.dataset import Example
from flywheel.mine import NodeStep, TracedRun, failing_node, failure_reason, mine, render

SETTINGS = MineSettings(rules=(FailureRule("correct", 1.0),))


def run(run_id, inputs, **kwargs):
    """A traced run with defaults."""
    return TracedRun(id=run_id, name="agent", inputs=inputs, **kwargs)


def test_failure_reasons():
    """An error, or a feedback score under its threshold, is a failure; a pass is not."""
    assert failure_reason(run("1", {}, error="ValueError: bad"), SETTINGS) == "error: ValueError"
    assert failure_reason(run("2", {}, feedback={"correct": 0.0}), SETTINGS) == "correct < 1"
    assert failure_reason(run("3", {}, feedback={"correct": 1.0}), SETTINGS) is None
    assert failure_reason(run("4", {}), SETTINGS) is None
    off = MineSettings(fail_on_error=False)
    assert failure_reason(run("5", {}, error="ValueError: bad"), off) is None


def test_failing_node():
    """The node that raised wins; else the last node reached; else the run's name."""
    steps = [NodeStep("triage"), NodeStep("rca", error="boom"), NodeStep("escalate")]
    assert failing_node(run("1", {}, nodes=steps)) == "rca"
    assert (
        failing_node(run("1", {}, nodes=[NodeStep("triage"), NodeStep("escalate")])) == "escalate"
    )
    assert failing_node(run("1", {})) == "agent"


def test_mine_groups_dedupes_and_skips_covered():
    """Signatures are counted, one candidate per input, and covered inputs are skipped."""
    covered = Example.new({"q": "old"})
    runs = [
        run("1", {"q": "a"}, feedback={"correct": 0}, nodes=[NodeStep("escalate")]),
        run("2", {"q": "a"}, feedback={"correct": 0}, nodes=[NodeStep("escalate")]),
        run("3", {"q": "b"}, feedback={"correct": 0}, nodes=[NodeStep("escalate")]),
        run("4", {"q": "old"}, error="TimeoutError: slow"),
        run("5", {"q": "fine"}, feedback={"correct": 1}),
    ]
    result = mine(runs, SETTINGS, existing=[covered], reference_of=lambda i: {"q": i["q"]})
    assert result.scanned == 5
    assert result.signatures == [("correct < 1 @ escalate", 3), ("error: TimeoutError @ agent", 1)]
    assert [c.inputs for c in result.candidates] == [{"q": "a"}, {"q": "b"}]
    assert result.already_covered == 1
    assert result.candidates[0].reference_outputs == {"q": "a"}
    assert result.candidates[0].metadata["needs_review"] is False
    assert "3 | `correct < 1 @ escalate`" in render(result)


def test_inputs_mapper_can_skip_runs():
    """A run the inputs mapper rejects becomes no candidate."""
    runs = [run("1", {"junk": 1}, error="X: y")]
    result = mine(runs, SETTINGS, inputs_of=lambda inputs: None)
    assert result.candidates == []
    assert len(result.failures) == 1
