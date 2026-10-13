"""Every result shape LangSmith accepts reduces to `{key: float}`."""

from types import SimpleNamespace

import pytest

from flywheel.scores import ScoreError, normalise, score_all


def test_bool_and_numbers():
    """Booleans become 1 or 0 and numbers pass through, under the evaluator's name."""
    assert normalise("ok", True) == {"ok": 1.0}
    assert normalise("ok", False) == {"ok": 0.0}
    assert normalise("latency", 12) == {"latency": 12.0}


def test_dict_shapes():
    """A keyed dict, a results list, and an EvaluationResult-like object all normalise."""
    assert normalise("x", {"key": "k", "score": True}) == {"k": 1.0}
    assert normalise("x", {"score": 0.5}) == {"x": 0.5}
    assert normalise("x", {"results": [{"key": "a", "score": 1}, {"key": "b", "score": 0}]}) == {
        "a": 1.0,
        "b": 0.0,
    }
    assert normalise("x", SimpleNamespace(key="k", score=0.25)) == {"k": 0.25}
    assert normalise("x", {"key": "k", "score": None}) == {}


def test_not_a_score():
    """A string is not a score."""
    with pytest.raises(ScoreError):
        normalise("x", "yes")


def test_raising_evaluator_scores_nothing_and_is_recorded():
    """One evaluator raising leaves the others' scores and names the one that raised."""

    def good(inputs, outputs, reference_outputs):
        """Always passes."""
        return True

    def bad(inputs, outputs, reference_outputs):
        """Always raises."""
        raise KeyError("team")

    scores, errors = score_all([good, bad], {}, {}, {})
    assert scores == {"good": 1.0}
    assert errors["bad"].startswith("KeyError")
