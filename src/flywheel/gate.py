"""Compare a pull request's experiment with its base branch's, case by case, and decide.

The question a reviewer asks is "which cases did this change break?", not "did the average
move?". An average hides a case that went from always passing to always failing behind one that
went the other way. So the gate works per case and per metric:

- Each case's *pass rate* is the share of its repetitions that passed a metric.
- A case is **broken** when its pass rate fell by at least `min_change` (by default 0.5: with
  three repetitions, at least two runs flipped from pass to fail), and **fixed** when it rose by
  as much.
- With `max_p` set, a test on the counts decides instead of `min_change`: a case is broken
  (or fixed) when a one-sided Fisher exact test on its pass counts gives a p-value of at most
  `max_p`, the chance a fall (or rise) at least that large shows up when nothing changed. Any
  other move is a wobble. Off by default; it needs more runs a side to have power, which a
  pooled base supplies.
- A smaller move is a **wobble**: reported, never blocking. Live models are not deterministic,
  and one run in three flipping is what noise looks like.
- A case present only in the pull request is **new**; a failing new case is reported, not
  blocked, because adding a test for a known bug is how the bug gets fixed.

The gate fails when more than `max_broken` cases broke, or (by default) when a case raises
that did not raise on the base branch, or when the pull request changed how it is graded
(`flywheel.grading`) and no person approved that. It also reports a sign test over broken
and fixed cases: how often a split at least that lopsided would appear if the change did
nothing at all.

When the agent counts its model calls (`flywheel.spend`), the gate also compares what a run
costs on each side: calls, tokens, the share of the prompt read from the cache and, for priced
calls, dollars. Those checks block only when their settings are set.
"""

from dataclasses import dataclass, field
from math import comb
from typing import Literal

from flywheel.config import GateSettings
from flywheel.experiment import Experiment, RunRecord
from flywheel.grading import GradingChange

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
    # The one-sided Fisher exact p-value for the move, when `max_p` is set and the rate moved.
    p_value: float | None = None


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
class CostSide:
    """What one side's runs of the shared cases used, on average per run."""

    runs: int
    calls: float
    tokens: float
    cache_share: float | None
    # List-price dollars per run; None unless every call of every run was priced.
    usd: float | None
    # Dollars these runs actually spent, in total: nothing for replayed or subscription calls.
    billed: float
    replayed: int


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
    grading_changes: list[GradingChange] = field(default_factory=list)
    grading_approved: bool = False
    base_cost: CostSide | None = None
    head_cost: CostSide | None = None

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


def scored(runs: list[RunRecord], metric: str) -> bool:
    """Whether `metric` applies to a case: some run scored it, or some run errored.

    An evaluator may decline to score a case (a check on replies, for an email that needs no
    reply). A metric no run of a case scored on either side is left out of that case and of the
    totals, so a check that only applies to some cases is not counted as failing on the rest.
    A run that errored still counts, so a crash can never hide a metric."""
    return any(run.error is not None or metric in run.scores for run in runs)


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


def fisher_drop(base_passed: int, base_runs: int, head_passed: int, head_runs: int) -> float:
    """One-sided Fisher exact test: the chance the head passes this few times under no change.

    The case's passes are pooled across both sides; under no change, which runs are the head's
    is chance, so the head's passes follow a hypergeometric draw. The p-value is the chance of
    a draw at most `head_passed`."""
    total, passed = base_runs + head_runs, base_passed + head_passed
    low = max(0, head_runs - (total - passed))
    tail = sum(
        comb(passed, x) * comb(total - passed, head_runs - x) for x in range(low, head_passed + 1)
    )
    return tail / comb(total, head_runs)


def sign_test(broken: int, fixed: int) -> float | None:
    """Two-sided exact sign test: the chance of a split at least this uneven under no effect."""
    n = broken + fixed
    if n == 0:
        return None
    k = min(broken, fixed)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def cost_side(experiment: Experiment, example_ids: set[str]) -> CostSide | None:
    """The average run's model use over `example_ids`; None when no run counted a call.

    Every run of those cases is in the average, so a run that made no call counts as zero."""
    runs = [run for run in experiment.runs if run.example_id in example_ids]
    used = [run.usage or {} for run in runs]
    if not any(used):
        return None
    n = len(runs)

    def total(key: str) -> float:
        return sum(u.get(key) or 0 for u in used)

    prompt = total("input") + total("cache_write") + total("cache_read")
    priced = all("usd" in u for u in used if u)
    return CostSide(
        runs=n,
        calls=total("calls") / n,
        tokens=(prompt + total("output")) / n,
        cache_share=total("cache_read") / prompt if prompt else None,
        usd=total("usd") / n if priced else None,
        billed=total("billed"),
        replayed=int(total("replayed")),
    )


def cost_reasons(base: CostSide | None, head: CostSide | None, settings: GateSettings) -> list[str]:
    """Why the cost checks block, when they are set and both sides have numbers to compare."""
    if base is None or head is None:
        return []
    reasons = []
    limit = settings.max_cost_increase
    if limit is not None and base.usd and head.usd is not None:
        rise = head.usd / base.usd - 1
        if rise > limit + 1e-9:
            reasons.append(
                f"a run's cost rose {rise:.0%}, from ${base.usd:.4f} to ${head.usd:.4f} "
                f"(at most {limit:.0%} allowed)"
            )
    limit = settings.max_token_increase
    if limit is not None and base.tokens:
        rise = head.tokens / base.tokens - 1
        if rise > limit + 1e-9:
            reasons.append(
                f"a run's tokens rose {rise:.0%}, from {base.tokens:,.0f} to {head.tokens:,.0f} "
                f"(at most {limit:.0%} allowed)"
            )
    limit = settings.max_cache_drop
    if limit is not None and base.cache_share is not None and head.cache_share is not None:
        drop = base.cache_share - head.cache_share
        if drop > limit + 1e-9:
            reasons.append(
                f"the share of the prompt read from the cache fell from {base.cache_share:.0%} "
                f"to {head.cache_share:.0%} (at most {limit * 100:.0f} points allowed)"
            )
    return reasons


def close_calls(base: Experiment, head: Experiment, settings: GateSettings) -> list[str]:
    """The shared cases whose verdict one more run could change, worth running again.

    A metric is a close call when it moved, and its move is within one run's worth of the
    `min_change` threshold. With 3 runs a side and the default threshold of 0.5, a 3/3 to 2/3
    wobble and a 3/3 to 1/3 break are close calls; a 3/3 to 0/3 break and a steady case are not.
    Extra runs go where they can change the answer, not to every case."""
    picked = []
    for example_id in head.examples:
        if example_id not in base.examples:
            continue
        base_runs, head_runs = base.runs_of(example_id), head.runs_of(example_id)
        if not base_runs or not head_runs:
            continue
        step = 1 / min(len(base_runs), len(head_runs))
        for metric in gated_metrics(base, head, settings):
            if not (scored(base_runs, metric) or scored(head_runs, metric)):
                continue
            base_rate = pass_rate(base_runs, metric, settings.pass_at) or 0.0
            head_rate = pass_rate(head_runs, metric, settings.pass_at) or 0.0
            move = abs(head_rate - base_rate)
            if move > 0 and abs(move - settings.min_change) <= step + 1e-9:
                picked.append(example_id)
                break
    return picked


def counts(runs: list[RunRecord], metric: str, pass_at: float) -> tuple[int, int]:
    """How many of `runs` passed `metric`, and how many there are."""
    return sum(passes(run, metric, pass_at) for run in runs), len(runs)


def metric_result(
    metric: str, base_runs: list[RunRecord], head_runs: list[RunRecord], settings: GateSettings
) -> MetricResult:
    """One metric of one case; with `max_p` set, the Fisher test decides instead of `min_change`."""
    base_rate = pass_rate(base_runs, metric, settings.pass_at)
    head_rate = pass_rate(head_runs, metric, settings.pass_at)
    verdict = metric_verdict(base_rate, head_rate, settings.min_change)
    if settings.max_p is None or base_rate is None or head_rate is None or base_rate == head_rate:
        return MetricResult(metric, base_rate, head_rate, verdict)
    base_passed, base_n = counts(base_runs, metric, settings.pass_at)
    head_passed, head_n = counts(head_runs, metric, settings.pass_at)
    if head_rate < base_rate:
        p_value = fisher_drop(base_passed, base_n, head_passed, head_n)
        moved: Verdict = "broken"
    else:
        p_value = fisher_drop(head_passed, head_n, base_passed, base_n)
        moved = "fixed"
    verdict = moved if p_value <= settings.max_p + 1e-12 else "wobble"
    return MetricResult(metric, base_rate, head_rate, verdict, p_value)


def compare(
    base: Experiment,
    head: Experiment,
    settings: GateSettings,
    grading_changes: list[GradingChange] | None = None,
    grading_approved: bool = False,
) -> GateResult:
    """Every case's verdict, the per-metric totals, and the decision."""
    metrics = gated_metrics(base, head, settings)
    ids = list(dict.fromkeys([*head.examples, *base.examples]))
    cases: list[CaseResult] = []
    for example_id in ids:
        base_runs = base.runs_of(example_id) if example_id in base.examples else []
        head_runs = head.runs_of(example_id) if example_id in head.examples else []
        results = [
            metric_result(metric, base_runs, head_runs, settings)
            for metric in metrics
            if scored(base_runs, metric) or scored(head_runs, metric)
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
        applies = {
            example_id
            for example_id in shared
            if scored(base.runs_of(example_id), metric) or scored(head.runs_of(example_id), metric)
        }
        base_runs = [run for run in base.runs if run.example_id in applies]
        head_runs = [run for run in head.runs if run.example_id in applies]
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
    grading_changes = grading_changes or []
    if grading_changes and not grading_approved:
        noun = "edit" if len(grading_changes) == 1 else "edits"
        reasons.append(
            f"it changes how it is graded ({len(grading_changes)} {noun}) and a person has "
            "not approved that"
        )
    base_cost, head_cost = cost_side(base, set(shared)), cost_side(head, set(shared))
    reasons += cost_reasons(base_cost, head_cost, settings)
    return GateResult(
        passed=not reasons,
        reasons=reasons,
        cases=cases,
        totals=totals,
        sign_test_p=sign_test(len(broken), len(fixed)),
        base=base,
        head=head,
        grading_changes=grading_changes,
        grading_approved=grading_approved,
        base_cost=base_cost,
        head_cost=head_cost,
    )
