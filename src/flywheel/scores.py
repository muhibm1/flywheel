"""Evaluator results in every shape LangSmith accepts, reduced to one `{key: float}` mapping.

An evaluator is any callable `(inputs, outputs, reference_outputs) -> result`, the signature
LangSmith's own `evaluate` calls, so the same function scores a local run and a LangSmith
experiment. A result may be a bool, a number, `{"key", "score"}`, or `{"results": [...]}`.
"""

from collections.abc import Callable, Mapping
from typing import Any

Evaluator = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], Any]


class ScoreError(ValueError):
    """An evaluator returned something that is not a score."""


def normalise(name: str, result: Any) -> dict[str, float]:
    """Every score an evaluator named `name` returned, keyed by metric name."""
    if isinstance(result, bool):
        return {name: 1.0 if result else 0.0}
    if isinstance(result, int | float):
        return {name: float(result)}
    if hasattr(result, "key") and hasattr(result, "score"):  # langsmith EvaluationResult
        return normalise(name, {"key": result.key, "score": result.score})
    if isinstance(result, Mapping):
        if "results" in result:
            scores: dict[str, float] = {}
            for item in result["results"]:
                scores.update(normalise(name, item))
            return scores
        if "score" in result:
            key = str(result.get("key") or name)
            score = result["score"]
            if score is None:
                return {}
            return normalise(key, score)
    raise ScoreError(f"evaluator {name!r} returned {type(result).__name__}, not a score")


def evaluator_name(evaluator: Evaluator) -> str:
    """The metric name a bare bool or number from `evaluator` is recorded under."""
    return getattr(evaluator, "__name__", type(evaluator).__name__)


def score_all(
    evaluators: list[Evaluator],
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> tuple[dict[str, float], dict[str, str]]:
    """Every evaluator over one run: the scores, and the evaluators that raised, by name.

    An evaluator that raises scores nothing; the gate treats a missing score as a failure, so a
    broken evaluator can never make a regression look like a pass."""
    scores: dict[str, float] = {}
    errors: dict[str, str] = {}
    for evaluator in evaluators:
        name = evaluator_name(evaluator)
        try:
            scores.update(normalise(name, evaluator(inputs, outputs, reference_outputs)))
        except Exception as error:  # recorded per evaluator; the run's other scores stand
            errors[name] = f"{type(error).__name__}: {error}"[:300]
    return scores, errors
