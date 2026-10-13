"""The dataset file: stable ids, a content version, merging without duplicates."""

import pytest

from flywheel.dataset import DatasetError, Example, inputs_id, load, merge, save, version


def test_id_depends_on_inputs_only():
    """Key order does not change an id; different inputs do."""
    assert inputs_id({"a": 1, "b": 2}) == inputs_id({"b": 2, "a": 1})
    assert inputs_id({"a": 1}) != inputs_id({"a": 2})


def test_round_trip_and_version(tmp_path):
    """What is saved loads back, and the version ignores line order."""
    a = Example.new({"q": "a"}, {"r": 1})
    b = Example.new({"q": "b"}, {"r": 2}, {"source": "seed"})
    path = tmp_path / "d.jsonl"
    save(path, [a, b])
    assert load(path) == [a, b]
    assert version([a, b]) == version([b, a])
    assert version([a]) != version([a, b])


def test_bad_line_is_named(tmp_path):
    """A malformed line raises with its line number."""
    path = tmp_path / "d.jsonl"
    path.write_text('{"id": "x", "inputs": {}}\nnot json\n')
    with pytest.raises(DatasetError, match=":2:"):
        load(path)


def test_duplicate_ids_rejected(tmp_path):
    """Two lines with one id are an error, not a silent overwrite."""
    path = tmp_path / "d.jsonl"
    path.write_text('{"id": "x", "inputs": {}}\n{"id": "x", "inputs": {"a": 1}}\n')
    with pytest.raises(DatasetError, match="duplicate"):
        load(path)


def test_merge_skips_known_inputs():
    """Merging adds only examples whose inputs are new, once each."""
    a, b = Example.new({"q": "a"}), Example.new({"q": "b"})
    merged, added = merge([a], [a, b, b])
    assert merged == [a, b]
    assert added == [b]
