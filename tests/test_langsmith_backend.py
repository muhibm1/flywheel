"""The LangSmith backend against a fake client: no network."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from flywheel import langsmith_backend as backend
from flywheel import spend
from flywheel.config import FailureRule, MineSettings
from flywheel.dataset import Example

T0 = datetime(2026, 10, 13, tzinfo=UTC)


def child(name, step, error=None, offset=0, node=None):
    """A run inside a LangGraph node as LangSmith records it; `node` defaults to `name`."""
    return SimpleNamespace(
        name=name,
        error=error,
        start_time=T0 + timedelta(seconds=offset),
        extra={"metadata": {"langgraph_node": node or name, "langgraph_step": step}},
    )


class FakeClient:
    """Just enough of `langsmith.Client`."""

    def __init__(self):
        self.examples = []
        self.tags = []
        self.datasets = set()
        self.roots = [
            SimpleNamespace(
                id="ok",
                name="graph",
                trace_id="t-ok",
                inputs={"q": 1},
                outputs={"a": 1},
                error=None,
                feedback_stats={"correct": {"n": 1, "avg": 1.0}},
            ),
            SimpleNamespace(
                id="bad",
                name="graph",
                trace_id="t-bad",
                inputs={"q": 2},
                outputs={"a": 2},
                error=None,
                feedback_stats={"correct": {"n": 1, "avg": 0.0}},
            ),
        ]
        self.children = {
            "t-bad": [
                child("triage", 1, offset=0),
                child("ChatModel", 2, node="rca"),  # not a node: name differs from langgraph_node
                child("rca", 2, offset=1),
                child("rca", 2, offset=2),
                child("escalate", 3, offset=3),
            ]
        }
        self.trace_queries = []

    def list_runs(
        self, *, project_name=None, is_root=None, start_time=None, limit=None, trace_id=None
    ):
        """Roots for a project query, children for a trace query."""
        if trace_id:
            self.trace_queries.append(trace_id)
            return iter(self.children.get(trace_id, []))
        return iter(self.roots)

    def get_run_url(self, *, run, project_name=None, project_id=None):
        """A fake URL."""
        return f"https://smith.example/{run.id}"

    def has_dataset(self, *, dataset_name):
        """Whether the dataset exists."""
        return dataset_name in self.datasets

    def create_dataset(self, name, description=None):
        """Create a dataset."""
        self.datasets.add(name)
        return SimpleNamespace(id=name)

    def read_dataset(self, *, dataset_name):
        """Read a dataset."""
        return SimpleNamespace(id=dataset_name)

    def list_examples(self, dataset_id=None, dataset_name=None, as_of=None):
        """Every example."""
        return iter(self.examples)

    def create_examples(self, *, dataset_id, examples):
        """Store examples with generated ids."""
        for example in examples:
            self.examples.append(
                SimpleNamespace(id=f"ls-{len(self.examples)}", metadata=example["metadata"])
            )

    def update_dataset_tag(self, *, dataset_id, as_of, tag):
        """Record the tag."""
        self.tags.append(tag)


def test_fetch_traced_runs_reads_nodes_for_failures_only():
    """Only the failing trace is walked, and its nodes come back in step order, deduplicated."""
    ls = FakeClient()
    settings = MineSettings(rules=(FailureRule("correct"),))
    runs = backend.fetch_traced_runs(ls, "proj", settings)
    assert ls.trace_queries == ["t-bad"]
    bad = next(run for run in runs if run.id == "bad")
    assert [step.name for step in bad.nodes] == ["triage", "rca", "escalate"]
    assert bad.feedback == {"correct": 0.0}
    assert bad.url == "https://smith.example/bad"


def test_sync_dataset_is_idempotent_and_tags_the_version():
    """Syncing twice creates each example once and tags each sync with the version."""
    ls = FakeClient()
    examples = [Example.new({"q": 1}), Example.new({"q": 2})]
    first = backend.sync_dataset(ls, "regressions", examples, "abc")
    second = backend.sync_dataset(ls, "regressions", examples, "abc")
    assert len(ls.examples) == 2
    assert first == second
    assert ls.tags == ["fw-abc", "fw-abc"]


class Results(list):
    """What `evaluate` returns, as far as `run_experiment` reads it before converting."""

    experiment_name = "flywheel-head"


def test_a_spend_stop_is_raised_once_evaluate_has_kept_it_as_an_errored_run():
    """`evaluate` keeps a target's error and goes on, so a refused call is raised after it."""
    ls = FakeClient()
    kept = []

    def evaluate(target, *, data, **options):
        """Like `langsmith.Client.evaluate`: a target's error is kept, never raised."""
        for _ in data:
            try:
                target({"q": 1})
            except Exception as error:
                kept.append(type(error).__name__)
        return Results()

    ls.evaluate = evaluate

    def refused(inputs):
        raise spend.SpendRefused("a call to claude-haiku-5-5 refused: paid calls are off")

    examples = [Example.new({"q": 1}), Example.new({"q": 2})]
    with pytest.raises(spend.SpendRefused):
        backend.run_experiment(
            ls,
            refused,
            [],
            examples,
            dataset="regressions",
            dataset_version="abc",
            repetitions=1,
            label="head",
        )
    assert kept == ["SpendRefused", "SpendRefused"]
