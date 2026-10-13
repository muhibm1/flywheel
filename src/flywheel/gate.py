"""Compare a pull request's experiment with its base branch's, case by case, and decide.

The question a reviewer asks is "which cases did this change break?", not "did the average
move?". An average hides a case that went from always passing to always failing behind one that
went the other way. So the gate works per case and per metric:

- Each case's *pass rate* is the share of its repetitions that passed a metric.
- A case is **broken** when its pass rate fell by at least `min_change` (by default 0.5: with
  three repetitions, at least two runs flipped from pass to fail), and **fixed** when it rose by
  as much.
- A smaller move is a **wobble**: reported, never blocking. Live models are not deterministic,
  and one run in three flipping is what noise looks like.
- A case present only in the pull request is **new**; a failing new case is reported, not
  blocked, because adding a test for a known bug is how the bug gets fixed.

The gate fails when more than `max_broken` cases broke, or (by default) when a case raises
that did not raise on the base branch. It also reports a sign test over broken and fixed cases:
how often a split at least that lopsided would appear if the change did nothing at all.
"""

from dataclasses import dataclass, field
from math import comb
from typing import Literal

from flywheel.config import GateSettings
from flywheel.experiment import Experiment, RunRecord

Verdict = Literal["broken", "fixed", "wobble", "steady_pass", "steady_fail", "new", "removed"]
# The order in which a case's worst metric decides its own verdict.
SEVERITY: tuple[Verdict, ...] = (
    "broken",
    "fixed",
    "wobble",
    "new",
    "steady_fail",
    "steady_pass",
    "removed",
)


@dataclass(frozen=True)
class MetricResult:
    """One metric of one case on both sides."""

    metric: str
    base_rate: float | None
    head_rate: float | None
    verdict: Verdict


@dataclass(frozen=True)
class CaseResult:
    """One case: its verdict, the metrics behind it, and links to the pull request's traces."""

    example_id: str
    summary: str
    verdict: Verdict
    metrics: list[MetricResult]
    new_error: str | None = None
    head_urls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MetricTotal:
    """One metric over every case both sides ran."""

    metric: str
    base_passed: int
    base_runs: int
    head_passed: int
    head_runs: int


@dataclass(frozen=True)
class GateResult:
    """The decision and everything the report shows."""

    passed: bool
    reasons: list[str]
    cases: list[CaseResult]
    totals: list[MetricTotal]
    sign_test_p: float | None
    base: Experiment
    head: Experiment

    def count(self, verdict: Verdict) -> int:
        """How many cases ended with `verdict`."""
        return sum(1 for case in self.cases if case.verdict == verdict)


def passes(run: RunRecord, metric: str, pass_at: float) -> bool:
    """Whether one run passed one metric; an errored run or a missing score is a failure."""
    if run.error is not None:
        return False
    score = run.scores.get(metric)
    return score is not None and score >= pass_at


def pass_rate(runs: list[RunRecord], metric: str, pass_at: float) -> float | None:
    """The share of `runs` that passed `metric`; None when there are no runs."""
    if not runs:
        return None
    return sum(passes(run, metric, pass_at) for run in runs) / len(runs)


def gated_metrics(base: Experiment, head: Experiment, settings: GateSettings) -> list[str]:
    """The configured metrics, or else every metric whose scores are all 0 or 1."""
    if settings.metrics:
        return list(settings.metrics)
    observed: dict[str, bool] = {}
    for run in [*base.runs, *head.runs]:
        for key, score in run.scores.items():
            observed[key] = observed.get(key, True) and score in (0.0, 1.0)
    return sorted(key for key, binary in observed.items() if binary)


def metric_verdict(base_rate: float | None, head_rate: float | None, min_change: float) -> Verdict:
    """What happened to one metric of one case."""
    if base_rate is None:
        return "new"
    if head_rate is None:
        return "removed"
    change = head_rate - base_rate
    if change <= -min_change:
        return "broken"
    if change >= min_change:
        return "fixed"
    if change != 0:
        return "wobble"
    return "steady_pass" if head_rate >= 0.5 else "steady_fail"


def sign_test(broken: int, fixed: int) -> float | None:
    """Two-sided exact sign test: the chance of a split at least this uneven under no effect."""
    n = broken + fixed
    if n == 0:
        return None
    k = min(broken, fixed)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def compare(base: Experiment, head: Experiment, settings: GateSettings) -> GateResult:
    """Every case's verdict, the per-metric totals, and the decision."""
    metrics = gated_metrics(base, head, settings)
    ids = list(dict.fromkeys([*head.examples, *base.examples]))
    cases: list[CaseResult] = []
    for example_id in ids:
        base_runs = base.runs_of(example_id) if example_id in base.examples else []
        head_runs = head.runs_of(example_id) if example_id in head.examples else []
        results = [
            MetricResult(
                metric=metric,
                base_rate=pass_rate(base_runs, metric, settings.pass_at),
                head_rate=pass_rate(head_runs, metric, settings.pass_at),
                verdict=metric_verdict(
                    pass_rate(base_runs, metric, settings.pass_at),
                    pass_rate(head_runs, metric, settings.pass_at),
                    settings.min_change,
                ),
            )
            for metric in metrics
        ]
        verdict = min((r.verdict for r in results), key=SEVERITY.index, default="steady_pass")
        base_errored = any(run.error for run in base_runs)
        head_error = next((run.error for run in head_runs if run.error), None)
        cases.append(
            CaseResult(
                example_id=example_id,
                summary=head.examples.get(example_id) or base.examples.get(example_id, ""),
                verdict=verdict,
                metrics=results,
                new_error=head_error if base_runs and head_error and not base_errored else None,
                head_urls=[run.url for run in head_runs if run.url],
            )
        )
    cases.sort(key=lambda case: (SEVERITY.index(case.verdict), case.example_id))

    shared = [
        example_id
        for example_id in ids
        if example_id in base.examples and example_id in head.examples
    ]
    totals = []
    for metric in metrics:
        base_runs = [run for run in base.runs if run.example_id in shared]
        head_runs = [run for run in head.runs if run.example_id in shared]
        totals.append(
            MetricTotal(
                metric=metric,
                base_passed=sum(passes(run, metric, settings.pass_at) for run in base_runs),
                base_runs=len(base_runs),
                head_passed=sum(passes(run, metric, settings.pass_at) for run in head_runs),
                head_runs=len(head_runs),
            )
        )

    broken = [case for case in cases if case.verdict == "broken"]
    fixed = [case for case in cases if case.verdict == "fixed"]
    errored = [case for case in cases if case.new_error]
    reasons = []
    if not head.runs:
        reasons.append("the pull request's experiment has no runs")
    if not metrics:
        reasons.append("no pass/fail metric to gate on")
    if len(broken) > settings.max_broken:
        noun = "case" if len(broken) == 1 else "cases"
        reasons.append(f"{len(broken)} {noun} broke (at most {settings.max_broken} allowed)")
    if settings.block_on_new_errors and errored:
        noun = "case raises" if len(errored) == 1 else "cases raise"
        reasons.append(f"{len(errored)} {noun} an error it did not raise before")
    return GateResult(
        passed=not reasons,
        reasons=reasons,
        cases=cases,
        totals=totals,
        sign_test_p=sign_test(len(broken), len(fixed)),
        base=base,
        head=head,
    )
