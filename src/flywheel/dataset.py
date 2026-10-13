"""The regression dataset: a JSONL file in the repository, versioned by its own content.

Each line is one example: the `inputs` the agent receives, the `reference_outputs` evaluators
grade against, and `metadata` saying where the example came from (for a mined example, the
trace it was mined from). The file lives next to the code it tests, so a pull request that
adds a case and the fix for it are reviewed together, and the version a run used is the hash
of the file, which the run records.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class DatasetError(ValueError):
    """The dataset file is malformed."""


def canonical(value: Any) -> str:
    """`value` as JSON with sorted keys and no spacing, so equal data hashes equally."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def inputs_id(inputs: dict[str, Any]) -> str:
    """A stable id for an example, derived from its inputs: the same inputs never enter twice."""
    return hashlib.sha256(canonical(inputs).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class Example:
    """One test case."""

    id: str
    inputs: dict[str, Any]
    reference_outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        inputs: dict[str, Any],
        reference_outputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Example":
        """An example whose id is derived from its inputs."""
        return cls(inputs_id(inputs), inputs, reference_outputs or {}, metadata or {})

    def to_json(self) -> str:
        """One JSONL line."""
        return canonical(asdict(self))


def load(path: Path) -> list[Example]:
    """Every example in `path`, in file order. Raises `DatasetError` naming the bad line."""
    examples: list[Example] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            example = Example(
                id=str(raw["id"]),
                inputs=dict(raw["inputs"]),
                reference_outputs=dict(raw.get("reference_outputs") or {}),
                metadata=dict(raw.get("metadata") or {}),
            )
        except (ValueError, KeyError, TypeError) as error:
            raise DatasetError(f"{path}:{number}: {type(error).__name__}: {error}") from error
        if example.id in seen:
            raise DatasetError(f"{path}:{number}: duplicate example id {example.id}")
        seen.add(example.id)
        examples.append(example)
    return examples


def save(path: Path, examples: list[Example]) -> None:
    """Write `examples` to `path`, one per line, in the given order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(example.to_json() + "\n" for example in examples), encoding="utf-8")


def version(examples: list[Example]) -> str:
    """The dataset's version: a hash of its examples, independent of line order and spacing."""
    lines = sorted(example.to_json() for example in examples)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:12]


def merge(existing: list[Example], new: list[Example]) -> tuple[list[Example], list[Example]]:
    """`existing` plus every example of `new` whose inputs are not already there.

    Returns the merged list and the examples actually added."""
    known = {example.id for example in existing}
    added = []
    for example in new:
        if example.id not in known:
            known.add(example.id)
            added.append(example)
    return [*existing, *added], added
