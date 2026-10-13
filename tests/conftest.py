"""Shared builders for experiments and runs."""

from flywheel.experiment import Experiment, RunRecord


def experiment(label: str, cases: dict[str, list[dict | str]], repetitions: int | None = None):
    """An experiment from `{example_id: [scores or an error string per repetition]}`."""
    runs = []
    for example_id, reps in cases.items():
        for number, rep in enumerate(reps, start=1):
            if isinstance(rep, str):
                runs.append(RunRecord(example_id, number, {}, error=rep))
            else:
                runs.append(RunRecord(example_id, number, dict(rep)))
    reps = repetitions or max((len(r) for r in cases.values()), default=1)
    return Experiment(
        label=label,
        backend="local",
        dataset_version="v1",
        repetitions=reps,
        runs=runs,
        examples={example_id: f"case {example_id}" for example_id in cases},
    )


PASS = {"ok": 1.0}
FAIL = {"ok": 0.0}
