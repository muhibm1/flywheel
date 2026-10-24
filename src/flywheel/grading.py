"""What a pull request changed about how it is graded.

A gate is only as honest as its checks. A pull request can turn a failing case into a passing one
without touching the agent: loosen an evaluator, rewrite a case's expected answer, delete the
case, or raise the gate's tolerance. Each side of the comparison is graded by its own checkout, so
the gate alone would report that as a fix. This module lists those edits so the gate can hold the
pull request until a person approves them.

What it compares:

- **Evaluator code**: a hash of the source of the module that defines each evaluator, recorded by
  `flywheel run`. A helper the evaluator imports from another module is not covered.
- **Evaluator list**: an evaluator the base branch configured and the pull request dropped.
- **Gate settings**: any change to `[gate]`, in either direction.
- **Expected answers**: a case on both branches whose `reference_outputs` differ.
- **Removed cases**: a case the base branch's dataset has and the pull request's does not.

Adding cases or evaluators is not listed: it can only make the gate stricter.
"""

import hashlib
import inspect
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from flywheel import dataset
from flywheel.config import Config, ConfigError, load, resolve
from flywheel.experiment import Experiment

Kind = Literal["evaluator_code", "evaluator_removed", "gate_setting", "reference", "case_removed"]
KIND_TITLES: dict[Kind, str] = {
    "evaluator_code": "Evaluator code changed",
    "evaluator_removed": "Evaluator removed",
    "gate_setting": "Gate setting changed",
    "reference": "Expected answer changed",
    "case_removed": "Case removed",
}


@dataclass(frozen=True)
class GradingChange:
    """One edit to how the pull request is graded."""

    kind: Kind
    subject: str
    detail: str = ""


def fingerprint(spec: str, root: Path) -> str:
    """A short hash of the source of the module that defines the evaluator `spec`."""
    module = inspect.getmodule(resolve(spec, root))
    try:
        source = inspect.getsource(module) if module else ""
    except (OSError, TypeError):
        return "unreadable"
    return hashlib.sha256(source.encode()).hexdigest()[:12]


def fingerprints(cfg: Config) -> dict[str, str]:
    """Every configured evaluator's fingerprint."""
    return {spec: fingerprint(spec, cfg.root) for spec in cfg.evaluators}


def changes(
    base: Experiment,
    head: Experiment,
    head_cfg: Config,
    base_cfg: Config | None = None,
) -> list[GradingChange]:
    """Every edit the pull request made to its own grading.

    Evaluator code is compared from the hashes both experiments recorded. The rest needs the
    base branch's config; without it only evaluator code is compared."""
    found: list[GradingChange] = []
    for spec in sorted(set(base.graders) & set(head.graders)):
        if base.graders[spec] != head.graders[spec]:
            found.append(GradingChange("evaluator_code", spec))
    if base_cfg is None:
        return found

    for spec in base_cfg.evaluators:
        if spec not in head_cfg.evaluators:
            found.append(GradingChange("evaluator_removed", spec))
    base_gate, head_gate = asdict(base_cfg.gate), asdict(head_cfg.gate)
    for key, before in base_gate.items():
        after = head_gate[key]
        if before != after:
            found.append(GradingChange("gate_setting", key, f"{before!r} → {after!r}"))

    if not base_cfg.dataset.exists():
        return found
    before_cases = {example.id: example for example in dataset.load(base_cfg.dataset)}
    after_cases = {example.id: example for example in dataset.load(head_cfg.dataset)}
    for example_id, example in before_cases.items():
        if example_id not in after_cases:
            found.append(GradingChange("case_removed", example_id))
        elif example.reference_outputs != after_cases[example_id].reference_outputs:
            found.append(GradingChange("reference", example_id))
    return found


def load_base_config(path: Path) -> Config | None:
    """The base branch's config, or None when the base branch has none yet."""
    if not path.exists():
        return None
    try:
        return load(path)
    except ConfigError:
        return None
