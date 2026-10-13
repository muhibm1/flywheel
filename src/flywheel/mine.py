"""Find the traced runs that went wrong, group them by where they went wrong, and propose
each group's runs as new test cases.

A *traced run* is one LangSmith trace of the agent: its inputs, its outputs or error, the
feedback scores attached to it (by an online evaluator, a person, or `flywheel score`), and
the LangGraph nodes it passed through. A run is a *failure* when it raised, or when one of the
configured feedback keys scored below its threshold.

Failures are grouped by *signature*: the reason (which score failed, or which exception was
raised) and the node where the run went wrong (the node that raised, or else the last node the
run reached). Ten failures with one signature are usually one bug; the summary ranks
signatures by count, so the first fix is the one that clears the most failures.

Every failure becomes a *candidate* example. Candidates are deduplicated by their inputs and
against the existing dataset, and carry a link to the trace they came from. A person reviews
them (in a LangSmith annotation queue, or in the candidates file) before `flywheel promote`
adds them to the dataset.
"""

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from flywheel.config import MineSettings
from flywheel.dataset import Example


@dataclass(frozen=True)
class NodeStep:
    """One LangGraph node the run passed through, in order."""

    name: str
    error: str | None = None


@dataclass(frozen=True)
class TracedRun:
    """What mining needs from one trace."""

    id: str
    name: str
    inputs: dict[str, Any]
    outputs: dict[str, Any] | None = None
    error: str | None = None
    feedback: dict[str, float] = field(default_factory=dict)
    nodes: list[NodeStep] = field(default_factory=list)
    url: str | None = None


@dataclass(frozen=True)
class Failure:
    """A run that failed, and why."""

    run: TracedRun
    reason: str
    node: str

    @property
    def signature(self) -> str:
        """The group this failure belongs to."""
        return f"{self.reason} @ {self.node}"


@dataclass(frozen=True)
class MineResult:
    """Everything one mining pass found."""

    scanned: int
    failures: list[Failure]
    candidates: list[Example]
    # Signature -> how many failures share it, most common first.
    signatures: list[tuple[str, int]]
    # Candidates dropped because the dataset already has their inputs.
    already_covered: int


def failure_reason(run: TracedRun, settings: MineSettings) -> str | None:
    """Why `run` counts as a failure, or None when it does not."""
    if run.error and settings.fail_on_error:
        return "error: " + run.error.split(":", 1)[0].strip()
    for rule in settings.rules:
        score = run.feedback.get(rule.key)
        if score is not None and score < rule.below:
            return f"{rule.key} < {rule.below:g}"
    return None


def failing_node(run: TracedRun) -> str:
    """The node that raised, else the last node the run reached, else the run's own name."""
    for step in run.nodes:
        if step.error:
            return step.name
    if run.nodes:
        return run.nodes[-1].name
    return run.name


def mine(
    runs: Iterable[TracedRun],
    settings: MineSettings,
    *,
    existing: Iterable[Example] = (),
    inputs_of: Callable[[dict[str, Any]], dict[str, Any] | None] = lambda inputs: inputs,
    reference_of: Callable[[dict[str, Any]], dict[str, Any] | None] = lambda inputs: None,
) -> MineResult:
    """Scan `runs`, keep the failures, and propose one candidate per distinct input.

    `inputs_of` maps a trace's inputs to the dataset's inputs (None skips the run);
    `reference_of` fills a candidate's reference outputs when they can be derived (None leaves
    them for a person to write)."""
    scanned = 0
    failures: list[Failure] = []
    for run in runs:
        scanned += 1
        reason = failure_reason(run, settings)
        if reason is not None:
            failures.append(Failure(run=run, reason=reason, node=failing_node(run)))

    known = {example.id for example in existing}
    candidates: dict[str, Example] = {}
    counts: Counter[str] = Counter(failure.signature for failure in failures)
    already_covered = 0
    for failure in failures:
        inputs = inputs_of(failure.run.inputs)
        if inputs is None:
            continue
        reference = reference_of(inputs)
        example = Example.new(
            inputs,
            reference,
            {
                "source": "flywheel mine",
                "signature": failure.signature,
                "trace": failure.run.url or failure.run.id,
                "needs_review": reference is None,
            },
        )
        if example.id in known:
            already_covered += 1
            continue
        candidates.setdefault(example.id, example)
    return MineResult(
        scanned=scanned,
        failures=failures,
        candidates=list(candidates.values()),
        signatures=counts.most_common(),
        already_covered=already_covered,
    )


def render(result: MineResult) -> str:
    """A Markdown summary: what was scanned, the signatures by count, the new candidates."""
    lines = [
        "## Flywheel mining report",
        "",
        f"Scanned {result.scanned} traced run(s); {len(result.failures)} failed. "
        f"{len(result.candidates)} new candidate test case(s); "
        f"{result.already_covered} failure(s) were already covered by the dataset.",
        "",
    ]
    if result.signatures:
        lines += ["| Failures | Signature (reason @ node) |", "|---:|---|"]
        lines += [f"| {count} | `{signature}` |" for signature, count in result.signatures]
        lines.append("")
    for example in result.candidates:
        review = " (needs a reference before promotion)" if example.metadata["needs_review"] else ""
        signature, trace = example.metadata["signature"], example.metadata["trace"]
        lines.append(f"- `{example.id}` `{signature}`{review}: {trace}")
    return "\n".join(lines) + "\n"
