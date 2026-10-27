"""Estimate how often the gate blocks a change that did nothing, with no new model calls.

Every stored run of the unchanged agent (Sonnet 4.5) is pooled per case: 18 repetitions a case
for the email agent (three six-run experiments), 6 for the SQL agent (two three-run ones). Each
trial draws disjoint repetitions for the two sides, without replacement, and gates them with the
study's own settings. Both sides come from the same agent, so every block is a false block.

The same draws, with Haiku 4.5's six runs as the head, give how often the gate catches the one
break the study reports (the school-deadline email, case 16e8...).

Each split runs twice: with the study's settings (a fall of `min_change` blocks), and with
`max_p = 0.05` added (the fall must also pass a one-sided Fisher exact test).

It assumes a case's repetitions are exchangeable: any run of main is as likely as any other.
The three email experiments were made on different days, so this is the best case for noise.

    python false_block_check.py        # from this folder, with flywheel installed
"""

import random
from dataclasses import replace
from pathlib import Path

from flywheel.config import load
from flywheel.experiment import Experiment, RunRecord
from flywheel.gate import compare

HERE = Path(__file__).parent
TRIALS = 2000
SEED = 7
DEADLINE = "16e8"
# Agent -> (the unchanged agent's experiments, the six-run change or None).
STUDIES = {
    "email": (["main-a-x6", "main-b-x6", "main-c"], "head-haiku-x6"),
    "sql": (["base-a", "base-b"], None),
}
# Base repetitions, head repetitions: one run a side at 3 and 6, and a pooled main.
SPLITS = {"email": [(3, 3), (6, 6), (12, 6)], "sql": [(3, 3)]}
MAX_P = 0.05


def by_case(experiments: list[Experiment]) -> dict[str, list[RunRecord]]:
    """Every repetition of every case, across experiments."""
    cases: dict[str, list[RunRecord]] = {}
    for experiment in experiments:
        for run in experiment.runs:
            cases.setdefault(run.example_id, []).append(run)
    return cases


def side(template: Experiment, runs: list[RunRecord], repetitions: int) -> Experiment:
    """An experiment holding `runs`, numbered per case from 1."""
    seen: dict[str, int] = {}
    numbered = []
    for run in runs:
        seen[run.example_id] = seen.get(run.example_id, 0) + 1
        numbered.append(replace(run, repetition=seen[run.example_id]))
    return replace(template, runs=numbered, repetitions=repetitions)


def draw(cases: dict[str, list[RunRecord]], base_n: int, head_n: int, rng: random.Random):
    """Disjoint base and head repetitions of every case."""
    base, head = [], []
    for runs in cases.values():
        picked = rng.sample(runs, base_n + head_n)
        base += picked[:base_n]
        head += picked[base_n:]
    return base, head


def main() -> None:
    """Print the false-block rate for each agent and split, then the deadline catch rate."""
    for agent, (names, change) in STUDIES.items():
        study = load(HERE / agent / "flywheel.toml").gate
        for rule, settings in [("min_change", study), ("Fisher", replace(study, max_p=MAX_P))]:
            run_study(agent, rule, settings, names, change)


def run_study(agent, rule, settings, names, change) -> None:
    """The false-block rate for each split, then the deadline catch rate, under one rule."""
    rng = random.Random(SEED)  # the same draws for both rules
    experiments = [Experiment.load(HERE / agent / "runs" / f"{n}.json") for n in names]
    cases = by_case(experiments)
    template = experiments[0]
    for base_n, head_n in SPLITS[agent]:
        blocks = broken = 0
        for _ in range(TRIALS):
            base, head = draw(cases, base_n, head_n, rng)
            result = compare(side(template, base, base_n), side(template, head, head_n), settings)
            blocks += not result.passed
            broken += result.count("broken")
        print(
            f"{agent:5} {rule:10} {len(cases)} cases, main {base_n} vs main {head_n}: "
            f"blocked {blocks / TRIALS:.1%} of {TRIALS} no-change gates, "
            f"{broken / TRIALS:.2f} broken cases a gate"
        )
    if change is None:
        return
    haiku = Experiment.load(HERE / agent / "runs" / f"{change}.json")
    haiku_cases = by_case([haiku])
    for base_n, head_n in [(3, 3), (12, 3), (12, 6)]:
        caught = blocked = 0
        for _ in range(TRIALS):
            base, _ = draw(cases, base_n, 0, rng)
            head, _ = draw(haiku_cases, head_n, 0, rng)
            result = compare(side(template, base, base_n), side(haiku, head, head_n), settings)
            blocked += not result.passed
            caught += any(
                c.example_id.startswith(DEADLINE) and c.verdict == "broken" for c in result.cases
            )
        print(
            f"{agent:5} {rule:10} main {base_n} vs Haiku {head_n}: the deadline break caught in "
            f"{caught / TRIALS:.1%} of {TRIALS} gates, and the gate blocked Haiku in "
            f"{blocked / TRIALS:.1%}"
        )


if __name__ == "__main__":
    main()
