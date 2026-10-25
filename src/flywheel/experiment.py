"""One experiment: every example run `repetitions` times and scored, saved as JSON.

The gate compares two of these, so both the local backend (in process, no network) and the
LangSmith backend write the same shape. A target that raises is recorded as an errored run with
no scores, never a crash: the experiment finished, and the error is part of its result.

The local backend also keeps what each run's model calls cost, when the agent counts them with
`flywheel.spend`: tokens, cache reads and, for priced calls, dollars.
"""

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flywheel import spend
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
    # The run's model calls, as `flywheel.spend.Meter.summary` counts them; None when the agent
    # counted none.
    usage: dict[str, Any] | None = None


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
    # Evaluator name -> a hash of the source of the module that defines it, so the gate can
    # tell when a pull request changed its own checks.
    graders: dict[str, str] = field(default_factory=dict)
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


def pool(experiments: list[Experiment]) -> Experiment:
    """Several runs of the same version, combined into one experiment with every repetition.

    A case that passes one time in three can pass 3 of 3 on one run of the base branch and 0 of
    3 on the next, so comparing a pull request against one base run can call noise a break.
    Pooling earlier base runs gives each case's pass rate more repetitions to stand on. The runs
    must share a dataset version; each case's repetitions are renumbered in order. The pooled
    experiment keeps the last experiment's evaluator hashes: pass the newest run last."""
    if len(experiments) == 1:
        return experiments[0]
    versions = {e.dataset_version for e in experiments}
    if len(versions) > 1:
        raise ValueError(f"cannot pool experiments over different datasets: {sorted(versions)}")
    runs: list[RunRecord] = []
    examples: dict[str, str] = {}
    seen: dict[str, int] = {}
    for experiment in experiments:
        examples.update(experiment.examples)
        for run in experiment.runs:
            seen[run.example_id] = seen.get(run.example_id, 0) + 1
            runs.append(replace(run, repetition=seen[run.example_id]))
    shas = {e.git_sha for e in experiments}
    return Experiment(
        label=" + ".join(e.label for e in experiments),
        backend="+".join(dict.fromkeys(e.backend for e in experiments)),
        dataset_version=versions.pop(),
        repetitions=sum(e.repetitions for e in experiments),
        runs=runs,
        examples=examples,
        git_sha=shas.pop() if len(shas) == 1 else None,
        graders=experiments[-1].graders,
    )


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
        with spend.meter() as used:
            try:
                outputs = target(dict(example.inputs))
            except Exception as error:  # an errored run is a result, not a crash
                return RunRecord(
                    example_id=example.id,
                    repetition=repetition,
                    scores={},
                    error=f"{type(error).__name__}: {error}"[:300],
                    latency_ms=round((time.perf_counter() - started) * 1000, 1),
                    usage=used.summary(),
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
            usage=used.summary(),
        )

    if concurrency > 1 and len(jobs) > 1:
        # The first run goes alone. Parallel calls cannot read a cache entry that is still being
        # written, so a shared prompt prefix this run writes is then read by every run after it,
        # instead of each parallel run paying to write its own copy.
        runs = [one(jobs[0])]
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            runs += list(pool.map(one, jobs[1:]))
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
