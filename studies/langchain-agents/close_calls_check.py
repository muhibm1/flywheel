"""Replay the email study's six-run experiments to test close calls, with no new model calls.

Every pair of the four six-run experiments (three Sonnet 4.5 runs of main, one Haiku 4.5 run of
the change) is gated three ways: on the first 3 runs a side, on all 6, and on the first 3 plus
runs 4 to 6 of only the close calls. A close-call round is good if it reaches the 6-run decision
and the same broken cases while running fewer runs.

    python close_calls_check.py        # from this folder, with flywheel installed
"""

import itertools
from dataclasses import replace
from pathlib import Path

from flywheel.config import load
from flywheel.experiment import Experiment
from flywheel.gate import close_calls, compare

HERE = Path(__file__).parent / "email"
RUNS = ["main-a-x6", "main-b-x6", "main-c", "head-haiku-x6"]


def first(experiment: Experiment, last: int, only: set[str] | None = None) -> list:
    """The runs numbered 1..`last` (or `last`+1..6 when `only` is given) of `experiment`."""
    low, high = (last + 1, 6) if only is not None else (1, last)
    return [
        run
        for run in experiment.runs
        if low <= run.repetition <= high and (only is None or run.example_id in only)
    ]


def broken(result) -> list[str]:
    """The ids of the broken cases, shortened."""
    return [case.example_id[:4] for case in result.cases if case.verdict == "broken"]


def main() -> None:
    """Print one line per pair and the run totals."""
    settings = load(HERE / "flywheel.toml").gate
    runs = {name: Experiment.load(HERE / "runs" / f"{name}.json") for name in RUNS}
    six_total = adaptive_total = same_decision = same_broken = three_same = 0
    pairs = list(itertools.permutations(RUNS, 2))
    for base_name, head_name in pairs:
        base, head = runs[base_name], runs[head_name]
        base3 = replace(base, runs=first(base, 3), repetitions=3)
        head3 = replace(head, runs=first(head, 3), repetitions=3)
        calls = set(close_calls(base3, head3, settings))
        base_more = replace(base, runs=base3.runs + first(base, 3, calls))
        head_more = replace(head, runs=head3.runs + first(head, 3, calls))
        six = compare(base, head, settings)
        three = compare(base3, head3, settings)
        adaptive = compare(base_more, head_more, settings)
        cases = len(head.examples)
        six_runs, adaptive_runs = 2 * 6 * cases, 2 * (3 * cases + 3 * len(calls))
        six_total += six_runs
        adaptive_total += adaptive_runs
        same_decision += adaptive.passed == six.passed
        same_broken += broken(adaptive) == broken(six)
        three_same += three.passed == six.passed and broken(three) == broken(six)
        print(
            f"{base_name:>13} vs {head_name:<13} close calls {len(calls):2}  "
            f"runs {adaptive_runs}/{six_runs}  "
            f"broken: 3 runs {broken(three)}, close calls {broken(adaptive)}, 6 runs {broken(six)}"
        )
    print(
        f"\n{len(pairs)} pairs. Close calls matched the 6-run decision in {same_decision} and the "
        f"6-run broken cases in {same_broken}; 3 runs alone matched both in {three_same}."
    )
    print(
        f"Runs: {adaptive_total} with close calls against {six_total} at 6 everywhere "
        f"({1 - adaptive_total / six_total:.0%} fewer)."
    )


if __name__ == "__main__":
    main()
