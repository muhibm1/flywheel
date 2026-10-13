"""`flywheel.toml`: what to run, how to score it, and when a change counts as a regression.

Every callable is named as `module:attribute` and imported on use, with the config file's own
directory on the import path, so an adapter can sit next to the config in the repository it
tests.
"""

import importlib
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """`flywheel.toml` is missing a field or names something that cannot be imported."""


@dataclass(frozen=True)
class FailureRule:
    """A traced run counts as a failure when feedback `key` scored below `below`."""

    key: str
    below: float = 1.0


@dataclass(frozen=True)
class GateSettings:
    """When a pull request is blocked."""

    # The metrics the gate decides on; empty means every metric the evaluators produce.
    metrics: tuple[str, ...] = ()
    # A run passes a metric when its score is at least this.
    pass_at: float = 1.0
    # A case counts as broken (or fixed) when its pass rate moves by at least this much.
    # With three repetitions, 0.5 means "two of three runs changed", so one noisy run in three
    # is reported as a wobble and never blocks.
    min_change: float = 0.5
    # How many broken cases are tolerated before the gate fails.
    max_broken: int = 0
    # Fail when the change makes a case raise that did not raise before.
    block_on_new_errors: bool = True


@dataclass(frozen=True)
class MineSettings:
    """Which traced runs count as failures worth turning into test cases."""

    project: str | None = None
    fail_on_error: bool = True
    rules: tuple[FailureRule, ...] = ()
    # Optional `module:function` mapping a run's inputs to reference outputs, used by `score`.
    reference: str | None = None
    # Optional `module:function` mapping a run's raw LangSmith inputs to the dataset's inputs.
    inputs: str | None = None


@dataclass(frozen=True)
class Config:
    """The whole file."""

    root: Path
    target: str
    evaluators: tuple[str, ...]
    dataset: Path
    repetitions: int = 3
    langsmith_dataset: str | None = None
    gate: GateSettings = field(default_factory=GateSettings)
    mine: MineSettings = field(default_factory=MineSettings)

    def target_callable(self) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """The agent under test: inputs in, outputs out."""
        return resolve(self.target, self.root)

    def evaluator_callables(self) -> list[Callable[..., Any]]:
        """Every evaluator, in file order."""
        return [resolve(name, self.root) for name in self.evaluators]


def load(path: Path) -> Config:
    """Parse `path`. Raises `ConfigError` for a missing or wrongly typed field."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{path}: {error}") from error
    main = raw.get("flywheel", {})
    gate = raw.get("gate", {})
    mine = raw.get("mine", {})
    root = path.resolve().parent
    try:
        return Config(
            root=root,
            target=required(main, "target"),
            evaluators=tuple(required(main, "evaluators")),
            dataset=root / required(main, "dataset"),
            repetitions=int(main.get("repetitions", 3)),
            langsmith_dataset=main.get("langsmith_dataset"),
            gate=GateSettings(
                metrics=tuple(gate.get("metrics", ())),
                pass_at=float(gate.get("pass_at", 1.0)),
                min_change=float(gate.get("min_change", 0.5)),
                max_broken=int(gate.get("max_broken", 0)),
                block_on_new_errors=bool(gate.get("block_on_new_errors", True)),
            ),
            mine=MineSettings(
                project=mine.get("project"),
                fail_on_error=bool(mine.get("fail_on_error", True)),
                rules=tuple(
                    FailureRule(key=str(rule["key"]), below=float(rule.get("below", 1.0)))
                    for rule in mine.get("rules", ())
                ),
                reference=mine.get("reference"),
                inputs=mine.get("inputs"),
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigError(f"{path}: {error}") from error


def required(table: dict[str, Any], key: str) -> Any:
    """`table[key]`, or a `ConfigError` naming the missing key."""
    if key not in table:
        raise ConfigError(f"[flywheel] needs `{key}`")
    return table[key]


def resolve(spec: str, root: Path) -> Any:
    """Import `module:attribute`, with `root` on the import path."""
    module_name, _, attribute = spec.partition(":")
    if not module_name or not attribute:
        raise ConfigError(f"{spec!r} is not `module:attribute`")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ConfigError(f"cannot import {module_name!r}: {error}") from error
    try:
        return getattr(module, attribute)
    except AttributeError as error:
        raise ConfigError(f"{module_name!r} has no {attribute!r}") from error
