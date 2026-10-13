"""The Markdown report opens in plain words and lists what needs attention."""

from conftest import FAIL, PASS, experiment

from flywheel.config import GateSettings
from flywheel.experiment import Experiment
from flywheel.gate import compare
from flywheel.report import MARKER, comparison_url, render

SETTINGS = GateSettings(metrics=("ok",))


def test_blocked_report():
    """A broken case is named with its before and after pass counts."""
    base = experiment("base", {"a": [PASS] * 3, "b": [PASS] * 3})
    head = experiment("head", {"a": [FAIL] * 3, "b": [PASS, FAIL, PASS]})
    text = render(compare(base, head, SETTINGS))
    assert text.startswith(MARKER)
    assert "❌" in text
    assert "1 case that passed before now fails" in text
    assert "`ok` 3/3 → 0/3" in text
    assert "Wobbling" in text


def test_clean_report():
    """No change says so."""
    base = experiment("base", {"a": [PASS]})
    text = render(compare(base, experiment("head", {"a": [PASS]}), SETTINGS))
    assert "✅ Flywheel: no regressions" in text
    assert "Nothing changed." in text


def test_comparison_url_only_for_one_dataset():
    """Both experiments on one LangSmith dataset get one side-by-side link."""
    page = "https://smith.example/o/1/datasets/9/compare?selectedSessions="
    base = Experiment("b", "langsmith", "v", 1, [], {}, url=page + "aaa")
    head = Experiment("h", "langsmith", "v", 1, [], {}, url=page + "bbb")
    assert comparison_url(base, head) == page + "aaa,bbb"
    other = Experiment("h", "langsmith", "v", 1, [], {}, url=page.replace("/9/", "/8/") + "c")
    assert comparison_url(base, other) is None
