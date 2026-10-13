"""One experiment: every example run `repetitions` times and scored, saved as JSON.

The gate compares two of these, so both the local backend (in process, no network) and the
LangSmith backend write the same shape. A target that raises is recorded as an errored run with
no scores, never a crash: the experiment finished, and the error is part of its result.
"""

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flywheel.dataset import Example, canonical
from flywheel.scores import Evaluator, score_all

SUMMARY_LENGTH = 160
SCHEMA = 1


@dataclass(frozen=True)
class RunRecord:
    """One repetition of one example."""

    example_id: str
    repetition: int
    scores: dict[str, float]
    error: str | None = None
    evaluator_errors: dict[str, str] = field(default_factory=dict)
    # A link to this run's trace, when the backend records one.
    url: str | None = None
    latency_ms: float | None = None


@dataclass(frozen=True)
class Experiment:
    """Every run of one version of the agent over one version of the dataset."""

    label: str
    backend: str
    dataset_version: str
    repetitions: int
    runs: list[RunRecord]
    # Example id -> a one-line summary of its inputs, for the report.
    examples: dict[str, str]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    git_sha: str | None = None
    # The LangSmith experiment, when there is one.
    url: str | None = None
    name: str | None = None
    schema: int = SCHEMA

    def save(self, path: Path) -> None:
        """Write the experiment as JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Experiment":
        """Read an experiment written by `save`."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema") != SCHEMA:
            raise ValueError(f"{path}: experiment schema {raw.get('schema')}, expected {SCHEMA}")
        runs = [RunRecord(**run) for run in raw.pop("runs")]
        return cls(runs=runs, **raw)

    def runs_of(self, example_id: str) -> list[RunRecord]:
        """Every repetition of one example."""
        return [run for run in self.runs if run.example_id == example_id]


def summary(inputs: dict[str, Any]) -> str:
    """A short single-line rendering of an example's inputs."""
    text = canonical(inputs)
    return text if len(text) <= SUMMARY_LENGTH else text[: SUMMARY_LENGTH - 1] + "…"


def run_local(
    target: Callable[[dict[str, Any]], dict[str, Any]],
    evaluators: list[Evaluator],
    examples: list[Example],
    *,
    repetitions: int,
    label: str,
    dataset_version: str,
    git_sha: str | None = None,
    concurrency: int = 1,
) -> Experiment:
    """Run `target` over every example `repetitions` times, in process, and score each run."""
    jobs = [(example, rep) for example in examples for rep in range(1, repetitions + 1)]

    def one(job: tuple[Example, int]) -> RunRecord:
        example, repetition = job
        started = time.perf_counter()
        try:
            outputs = target(dict(example.inputs))
        except Exception as error:  # an errored run is a result, not a crash
            return RunRecord(
                example_id=example.id,
                repetition=repetition,
                scores={},
                error=f"{type(error).__name__}: {error}"[:300],
                latency_ms=round((time.perf_counter() - started) * 1000, 1),
            )
        latency = round((time.perf_counter() - started) * 1000, 1)
        scores, errors = score_all(
            evaluators, dict(example.inputs), dict(outputs or {}), dict(example.reference_outputs)
        )
        return RunRecord(
            example_id=example.id,
            repetition=repetition,
            scores=scores,
            evaluator_errors=errors,
            latency_ms=latency,
        )

    if concurrency > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            runs = list(pool.map(one, jobs))
    else:
        runs = [one(job) for job in jobs]
    return Experiment(
        label=label,
        backend="local",
        dataset_version=dataset_version,
        repetitions=repetitions,
        runs=runs,
        examples={example.id: summary(example.inputs) for example in examples},
        git_sha=git_sha,
    )
