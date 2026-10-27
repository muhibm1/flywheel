"""The gate's verdicts, its noise threshold, and its decision."""

from dataclasses import replace

import pytest
from conftest import FAIL, PASS, experiment

from flywheel.config import GateSettings
from flywheel.experiment import pool
from flywheel.gate import close_calls, compare, fisher_drop, metric_verdict, sign_test
from flywheel.grading import GradingChange

SETTINGS = GateSettings(metrics=("ok",))


def test_metric_verdicts():
    """Moves of at least the threshold are broken or fixed; smaller moves are wobbles."""
    assert metric_verdict(1.0, 0.0, 0.5) == "broken"
    assert metric_verdict(1.0, 1 / 3, 0.5) == "broken"
    assert metric_verdict(1.0, 2 / 3, 0.5) == "wobble"
    assert metric_verdict(0.0, 1.0, 0.5) == "fixed"
    assert metric_verdict(1.0, 1.0, 0.5) == "steady_pass"
    assert metric_verdict(0.0, 0.0, 0.5) == "steady_fail"
    assert metric_verdict(None, 0.0, 0.5) == "new"
    assert metric_verdict(1.0, None, 0.5) == "removed"


def test_one_flipped_run_in_three_does_not_block():
    """Noise: one repetition in three failing is a wobble and the gate passes."""
    base = experiment("base", {"a": [PASS, PASS, PASS]})
    head = experiment("head", {"a": [PASS, FAIL, PASS]})
    result = compare(base, head, SETTINGS)
    assert result.passed
    assert result.cases[0].verdict == "wobble"


def test_broken_case_blocks_even_when_the_average_rises():
    """A case that broke blocks, though two other cases were fixed and the total went up."""
    base = experiment("base", {"a": [PASS] * 3, "b": [FAIL] * 3, "c": [FAIL] * 3})
    head = experiment("head", {"a": [FAIL] * 3, "b": [PASS] * 3, "c": [PASS] * 3})
    result = compare(base, head, SETTINGS)
    assert not result.passed
    assert [c.verdict for c in result.cases] == ["broken", "fixed", "fixed"]
    total = result.totals[0]
    assert (total.base_passed, total.head_passed) == (3, 6)
    assert "1 case broke" in result.reasons[0]


def test_allowance():
    """`max_broken` tolerates that many broken cases."""
    base = experiment("base", {"a": [PASS]})
    head = experiment("head", {"a": [FAIL]})
    assert compare(base, head, GateSettings(metrics=("ok",), max_broken=1)).passed


def test_new_error_blocks_and_missing_score_fails():
    """A case that starts raising blocks; a run with no score for the metric is a failure."""
    base = experiment("base", {"a": [PASS], "b": [PASS]})
    head = experiment("head", {"a": ["RuntimeError: boom"], "b": [{"other": 1.0}]})
    result = compare(base, head, SETTINGS)
    assert not result.passed
    assert any("error it did not raise before" in reason for reason in result.reasons)
    assert {c.example_id: c.verdict for c in result.cases} == {"a": "broken", "b": "broken"}


def test_metric_a_case_never_scores_is_left_out():
    """A check that declines a case on both sides is not counted as failing there."""
    settings = GateSettings(metrics=("ok", "reply"))
    reply = {"ok": 1.0, "reply": 1.0}
    base = experiment("base", {"a": [PASS] * 3, "b": [reply] * 3})
    head = experiment("head", {"a": [PASS] * 3, "b": [{"ok": 1.0}] * 3})
    result = compare(base, head, settings)
    cases = {c.example_id: c for c in result.cases}
    assert [m.metric for m in cases["a"].metrics] == ["ok"]
    assert cases["a"].verdict == "steady_pass"
    # Scored before and missing now still counts as a failure: a crash cannot hide a metric.
    assert cases["b"].verdict == "broken"
    reply_total = next(t for t in result.totals if t.metric == "reply")
    assert (reply_total.base_passed, reply_total.base_runs) == (3, 3)


def test_errors_on_both_sides_are_not_new():
    """A case that already raised on the base branch is not a new error."""
    base = experiment("base", {"a": ["ValueError: x"]})
    head = experiment("head", {"a": ["ValueError: x"]})
    result = compare(base, head, SETTINGS)
    assert result.passed
    assert result.cases[0].new_error is None


def test_new_failing_case_does_not_block():
    """A case added in the pull request that fails is reported as new, not blocked."""
    base = experiment("base", {"a": [PASS]})
    head = experiment("head", {"a": [PASS], "b": [FAIL]})
    result = compare(base, head, SETTINGS)
    assert result.passed
    assert result.cases[0].verdict == "new"
    assert result.totals[0].head_runs == 1  # totals compare shared cases only


def test_metrics_default_to_binary_scores():
    """Without configured metrics, only scores that are always 0 or 1 are gated."""
    base = experiment("base", {"a": [{"ok": 1.0, "latency": 120.0}]})
    head = experiment("head", {"a": [{"ok": 1.0, "latency": 90.0}]})
    result = compare(base, head, GateSettings())
    assert [t.metric for t in result.totals] == ["ok"]


def test_empty_head_blocks():
    """An experiment with no runs can never pass."""
    result = compare(experiment("base", {"a": [PASS]}), experiment("head", {}), SETTINGS)
    assert not result.passed


def test_sign_test():
    """No moves gives no p-value; a lopsided split gives a small one; an even split gives 1."""
    assert sign_test(0, 0) is None
    assert sign_test(3, 3) == 1.0
    assert sign_test(0, 8) < 0.01
    assert abs(sign_test(1, 0) - 1.0) < 1e-9


def test_pooled_base_calls_a_coin_toss_case_a_wobble():
    """One lucky base run makes a 1-in-3 case look broken; pooled base runs do not."""
    lucky = experiment("main-a", {"c": [PASS, PASS, FAIL]})
    unlucky = experiment("main-b", {"c": [FAIL, FAIL, FAIL]})
    head = experiment("head", {"c": [FAIL, FAIL, FAIL]})
    assert compare(lucky, head, SETTINGS).cases[0].verdict == "broken"
    pooled = pool([lucky, unlucky])
    assert pooled.repetitions == 6
    assert [run.repetition for run in pooled.runs] == [1, 2, 3, 4, 5, 6]
    result = compare(pooled, head, SETTINGS)
    assert result.passed
    assert result.cases[0].verdict == "wobble"


def test_pooled_base_still_blocks_a_real_break():
    """A case that always passed on main and now always fails is broken however many runs."""
    base = pool([experiment("a", {"c": [PASS] * 3}), experiment("b", {"c": [PASS] * 3})])
    result = compare(base, experiment("head", {"c": [FAIL] * 3}), SETTINGS)
    assert not result.passed


def test_pool_refuses_different_datasets():
    """Pooling runs over different datasets would mix cases that are not the same."""
    other = replace(experiment("b", {"c": [PASS]}), dataset_version="v2")
    with pytest.raises(ValueError):
        pool([experiment("a", {"c": [PASS]}), other])


def test_close_calls_are_the_cases_one_more_run_could_change():
    """A wobble and a two-run flip are close calls; a full flip and a steady case are not."""
    base = experiment(
        "base",
        {"wob": [PASS] * 3, "two": [PASS] * 3, "all": [PASS] * 3, "same": [PASS, FAIL, FAIL]},
    )
    head = experiment(
        "head",
        {
            "wob": [PASS, PASS, FAIL],
            "two": [PASS, FAIL, FAIL],
            "all": [FAIL] * 3,
            "same": [FAIL, PASS, FAIL],
        },
    )
    assert close_calls(base, head, SETTINGS) == ["wob", "two"]


def test_close_calls_skip_new_cases():
    """A case only the pull request runs has no before to be close to."""
    base = experiment("base", {"a": [PASS] * 3})
    head = experiment("head", {"a": [PASS] * 3, "b": [PASS, FAIL, FAIL]})
    assert close_calls(base, head, SETTINGS) == []


def test_extra_runs_settle_a_close_call():
    """A two-run flip blocks at 3 runs; three more runs a side that pass call it a wobble."""
    base = experiment("base", {"c": [PASS] * 3})
    head = experiment("head", {"c": [PASS, FAIL, FAIL]})
    assert not compare(base, head, SETTINGS).passed
    more_base = experiment("base-extra", {"c": [PASS] * 3})
    more_head = experiment("head-extra", {"c": [PASS] * 3})
    result = compare(pool([base, more_base]), pool([head, more_head]), SETTINGS)
    assert result.passed
    assert result.cases[0].verdict == "wobble"


def test_grading_changes_block_until_approved():
    """An edit to the checks blocks even when every case passes, unless a person approved it."""
    change = GradingChange("reference", "a")
    base = experiment("base", {"a": [PASS]})
    head = experiment("head", {"a": [PASS]})
    blocked = compare(base, head, SETTINGS, grading_changes=[change])
    assert not blocked.passed
    assert "changes how it is graded" in blocked.reasons[0]
    assert compare(base, head, SETTINGS, grading_changes=[change], grading_approved=True).passed


def test_fisher_drop_matches_known_values():
    """The one-sided Fisher p-value matches the hypergeometric tail worked by hand."""
    assert fisher_drop(3, 3, 0, 3) == pytest.approx(1 / 20)
    assert fisher_drop(3, 3, 1, 3) == pytest.approx(4 / 20)
    # 12 of 12 against 3 of 6: draw 6 of 18 runs holding 15 passes; P(at most 3 passes).
    assert fisher_drop(12, 12, 3, 6) == pytest.approx(455 * 1 / 18564)
    assert fisher_drop(2, 3, 2, 3) == pytest.approx(16 / 20)


def test_max_p_keeps_a_noisy_fall_as_a_wobble():
    """With `max_p`, a fall the counts cannot tell from noise is a wobble and does not block."""
    base = experiment("base", {"a": [PASS, PASS, PASS]})
    head = experiment("head", {"a": [PASS, FAIL, FAIL]})
    assert not compare(base, head, SETTINGS).passed
    result = compare(base, head, replace(SETTINGS, max_p=0.05))
    assert result.passed
    assert result.cases[0].verdict == "wobble"
    assert result.cases[0].metrics[0].p_value == pytest.approx(0.2)


def test_max_p_still_blocks_a_full_flip_and_counts_fixes():
    """A 3/3 to 0/3 flip reaches p = 0.05 and still blocks; the rising side is tested too."""
    base = experiment("base", {"a": [PASS] * 3, "b": [FAIL] * 3})
    head = experiment("head", {"a": [FAIL] * 3, "b": [PASS] * 3})
    result = compare(base, head, replace(SETTINGS, max_p=0.05))
    assert not result.passed
    assert [c.verdict for c in result.cases] == ["broken", "fixed"]
    assert [c.metrics[0].p_value for c in result.cases] == [pytest.approx(0.05)] * 2


def test_max_p_uses_a_pooled_base():
    """A pooled base gives the test its power: 12/12 to 3/6 blocks, 12/12 to 5/6 does not."""
    base = experiment("base", {"a": [PASS] * 12})
    settings = replace(SETTINGS, max_p=0.05)
    assert not compare(base, experiment("head", {"a": [PASS] * 3 + [FAIL] * 3}), settings).passed
    assert compare(base, experiment("head", {"a": [PASS] * 5 + [FAIL]}), settings).passed


def test_max_p_off_leaves_no_p_value():
    """Without `max_p` the gate is unchanged and reports no p-value."""
    base = experiment("base", {"a": [PASS, PASS, PASS]})
    head = experiment("head", {"a": [FAIL, FAIL, FAIL]})
    assert compare(base, head, SETTINGS).cases[0].metrics[0].p_value is None


def test_max_p_replaces_min_change():
    """With `max_p`, a fall smaller than `min_change` blocks when the counts make it unlikely."""
    base = experiment("base", {"a": [PASS] * 30})
    head = experiment("head", {"a": [PASS] * 4 + [FAIL] * 2})
    assert compare(base, head, SETTINGS).passed
    result = compare(base, head, replace(SETTINGS, max_p=0.05))
    assert not result.passed
    assert result.cases[0].metrics[0].p_value == pytest.approx(46376 / 1947792)
