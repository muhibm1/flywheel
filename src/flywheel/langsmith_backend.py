"""Everything that talks to LangSmith. Imported only by commands that need it.

- `fetch_traced_runs` reads a tracing project's root runs, their feedback, and (for failures
  only, to keep the number of calls down) the LangGraph nodes they passed through.
- `sync_dataset` mirrors the repository's dataset file into a LangSmith dataset and tags the
  synced state with the file's version, so an experiment can name exactly which cases it ran.
- `run_experiment` runs the agent through LangSmith's own `evaluate`, so every run is a trace
  with the evaluators' scores attached as feedback, and converts the result for the gate.
- `queue_for_review` puts failing runs in an annotation queue, where a person labels them.
- `write_feedback` attaches scores to existing traces (what `flywheel score` does).
"""

import warnings
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from itertools import islice
from typing import Any

from flywheel.config import MineSettings
from flywheel.dataset import Example
from flywheel.experiment import Experiment, RunRecord, summary
from flywheel.mine import NodeStep, TracedRun, failure_reason
from flywheel.scores import Evaluator, normalise

FLYWHEEL_ID = "flywheel_id"
FEEDBACK_SOURCE = {"source": "flywheel"}


def client() -> Any:
    """A LangSmith client configured from the environment (`LANGSMITH_API_KEY`)."""
    from langsmith import Client

    return Client()


def quietly(call: Callable[[], Any]) -> Any:
    """Run `call` with LangSmith's deprecation warnings silenced.

    `list_runs` and `get_run_url` are deprecated in favour of the newer `client.runs` API,
    which is async-only in langsmith 0.14; the synchronous methods stay supported until 2027."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return call()


def feedback_scores(ls: Any, run: Any) -> dict[str, float]:
    """The mean score per feedback key on one run."""
    stats = getattr(run, "feedback_stats", None) or {}
    scores = {
        key: float(value["avg"])
        for key, value in stats.items()
        if isinstance(value, dict) and value.get("avg") is not None
    }
    if scores or stats:
        return scores
    grouped: dict[str, list[float]] = {}
    for item in ls.list_feedback(run_ids=[run.id]):
        if item.score is not None:
            grouped.setdefault(item.key, []).append(float(item.score))
    return {key: sum(values) / len(values) for key, values in grouped.items()}


def node_steps(ls: Any, root: Any) -> list[NodeStep]:
    """The LangGraph nodes a trace passed through, in step order, from the runs' metadata."""
    steps: list[tuple[int, str, str, str | None]] = []
    children = quietly(lambda: list(ls.list_runs(trace_id=root.trace_id)))
    for child in children:
        metadata = (child.extra or {}).get("metadata", {})
        node, step = metadata.get("langgraph_node"), metadata.get("langgraph_step")
        if node and child.name == node and isinstance(step, int):
            steps.append((step, child.start_time.isoformat(), node, child.error))
    steps.sort()
    ordered: list[NodeStep] = []
    for _, _, node, error in steps:
        if ordered and ordered[-1].name == node and not error:
            continue
        ordered.append(NodeStep(name=node, error=error))
    return ordered


def root_runs(ls: Any, project: str, *, since: datetime | None, limit: int) -> list[Any]:
    """Up to `limit` root runs of `project`, newest first.

    The API caps one page at 100 runs, so the client pages and this stops after `limit`."""
    pages = quietly(lambda: ls.list_runs(project_name=project, is_root=True, start_time=since))
    return quietly(lambda: list(islice(pages, limit)))


def fetch_traced_runs(
    ls: Any,
    project: str,
    settings: MineSettings,
    *,
    since: datetime | None = None,
    limit: int = 200,
) -> list[TracedRun]:
    """The project's root runs, newest first, with nodes fetched for the failures only."""
    roots = root_runs(ls, project, since=since, limit=limit)
    runs = []
    for root in roots:
        traced = TracedRun(
            id=str(root.id),
            name=root.name,
            inputs=dict(root.inputs or {}),
            outputs=dict(root.outputs or {}) if root.outputs else None,
            error=root.error,
            feedback=feedback_scores(ls, root),
            url=quietly(lambda root=root: ls.get_run_url(run=root, project_name=project)),
        )
        if failure_reason(traced, settings) is not None:
            traced = TracedRun(**{**traced.__dict__, "nodes": node_steps(ls, root)})
        runs.append(traced)
    return runs


def sync_dataset(ls: Any, name: str, examples: list[Example], version: str) -> dict[str, str]:
    """Create or update the LangSmith dataset `name` to hold `examples`, and tag it.

    Examples are matched by their Flywheel id (kept in the example's metadata), so syncing twice
    adds nothing. Returns Flywheel id -> LangSmith example id."""
    if ls.has_dataset(dataset_name=name):
        dataset = ls.read_dataset(dataset_name=name)
    else:
        dataset = ls.create_dataset(
            name, description="Regression cases managed by Flywheel; edit the JSONL file instead."
        )
    present = {
        (example.metadata or {}).get(FLYWHEEL_ID): str(example.id)
        for example in ls.list_examples(dataset_id=dataset.id)
    }
    missing = [example for example in examples if example.id not in present]
    if missing:
        ls.create_examples(
            dataset_id=dataset.id,
            examples=[
                {
                    "inputs": example.inputs,
                    "outputs": example.reference_outputs,
                    "metadata": {**example.metadata, FLYWHEEL_ID: example.id},
                }
                for example in missing
            ],
        )
        present = {
            (example.metadata or {}).get(FLYWHEEL_ID): str(example.id)
            for example in ls.list_examples(dataset_id=dataset.id)
        }
    ls.update_dataset_tag(dataset_id=dataset.id, as_of=datetime.now(UTC), tag=f"fw-{version}")
    return {example.id: present[example.id] for example in examples}


def run_experiment(
    ls: Any,
    target: Callable[[dict[str, Any]], dict[str, Any]],
    evaluators: list[Evaluator],
    examples: list[Example],
    *,
    dataset: str,
    dataset_version: str,
    repetitions: int,
    label: str,
    git_sha: str | None = None,
    concurrency: int = 1,
) -> Experiment:
    """Run `target` with LangSmith's `evaluate` over the synced examples and convert the result.

    The experiment's metadata carries the label, the commit and the dataset version, so the
    LangSmith UI can line up the base and head experiments of one pull request."""
    sync_dataset(ls, dataset, examples, dataset_version)
    wanted = {example.id for example in examples}
    data = [
        example
        for example in ls.list_examples(dataset_name=dataset, as_of=f"fw-{dataset_version}")
        if (example.metadata or {}).get(FLYWHEEL_ID) in wanted
    ]
    results = ls.evaluate(
        target,
        data=data,
        evaluators=evaluators,
        num_repetitions=repetitions,
        experiment_prefix=f"flywheel-{label}",
        metadata={"flywheel_label": label, "git_sha": git_sha, "dataset_version": dataset_version},
        max_concurrency=concurrency,
    )
    rows = list(results)
    project = ls.read_project(project_name=results.experiment_name)
    repetition_of: dict[str, int] = {}
    runs: list[RunRecord] = []
    for row in rows:
        run, example = row["run"], row["example"]
        example_id = (example.metadata or {}).get(FLYWHEEL_ID, str(example.id))
        repetition_of[example_id] = repetition_of.get(example_id, 0) + 1
        scores: dict[str, float] = {}
        errors: dict[str, str] = {}
        for result in row["evaluation_results"]["results"]:
            if getattr(result, "comment", None) and result.score is None:
                errors[result.key] = str(result.comment)[:300]
            elif result.score is not None:
                scores.update(normalise(result.key, {"key": result.key, "score": result.score}))
        latency = None
        if run.end_time and run.start_time:
            latency = round((run.end_time - run.start_time).total_seconds() * 1000, 1)
        runs.append(
            RunRecord(
                example_id=example_id,
                repetition=repetition_of[example_id],
                scores=scores,
                error=run.error[:300] if run.error else None,
                evaluator_errors=errors,
                url=quietly(lambda run=run: ls.get_run_url(run=run, project_id=project.id)),
                latency_ms=latency,
            )
        )
    return Experiment(
        label=label,
        backend="langsmith",
        dataset_version=dataset_version,
        repetitions=repetitions,
        runs=runs,
        examples={example.id: summary(example.inputs) for example in examples},
        git_sha=git_sha,
        url=getattr(results, "url", None) or getattr(project, "url", None),
        name=results.experiment_name,
    )


def queue_for_review(ls: Any, queue: str, run_ids: Iterable[str], rubric: str) -> str:
    """Add runs to the annotation queue `queue`, creating it if needed. Returns the queue id."""
    existing = list(ls.list_annotation_queues(name=queue))
    if existing:
        queue_id = existing[0].id
    else:
        queue_id = ls.create_annotation_queue(name=queue, rubric_instructions=rubric).id
    ids = list(run_ids)
    if ids:
        ls.add_runs_to_annotation_queue(queue_id, run_ids=ids)
    return str(queue_id)


def write_feedback(ls: Any, run: Any, scores: dict[str, float], comment: str | None) -> None:
    """Attach each score to the run as feedback, marked as written by Flywheel."""
    for key, score in scores.items():
        ls.create_feedback(
            run.id,
            key,
            score=score,
            comment=comment,
            source_info=FEEDBACK_SOURCE,
            trace_id=run.trace_id,
            session_id=run.session_id,
        )
