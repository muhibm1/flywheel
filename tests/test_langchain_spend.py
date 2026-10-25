"""The spend guard and replay on a LangChain chat model, through LangChain's cache slot."""

import asyncio
import re

import pytest

pytest.importorskip("langchain_core")

from langchain_core.caches import BaseCache  # noqa: E402
from langchain_core.language_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult  # noqa: E402

from flywheel import spend  # noqa: E402
from flywheel.langchain_spend import SpendCache, guard_model, request_key  # noqa: E402

SENT: list[object] = []
USAGE = {
    "input_tokens": 100,
    "cache_creation_input_tokens": 50,
    "cache_read_input_tokens": 1000,
    "output_tokens": 50,
}
# Haiku 5.5: $0.10 a million input, $0.125 cache writes, $0.01 cache reads, $0.50 output.
PRICE = (100 * 0.10 + 50 * 0.125 + 1000 * 0.01 + 50 * 0.50) / 1e6


class FakeClaude(BaseChatModel):
    """A serializable chat model shaped like ChatAnthropic that answers without a network."""

    model: str = "claude-haiku-5-5"
    max_tokens: int = 100
    max_retries: int = 2

    @classmethod
    def is_lc_serializable(cls) -> bool:
        """Described by its settings, as ChatAnthropic is."""
        return True

    @property
    def _llm_type(self) -> str:
        """LangChain's name for the model type."""
        return "fake-claude"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Answer `answer <n>` for the n-th call sent, with the API's own usage."""
        SENT.append(messages[-1].content)
        message = AIMessage(content=f"answer {len(SENT)}")
        output = {"model_name": f"{self.model}-20261001", "usage": USAGE}
        return ChatResult(generations=[ChatGeneration(message=message)], llm_output=output)

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        """Stream the same answer in one chunk."""
        SENT.append(messages[-1].content)
        yield ChatGenerationChunk(message=AIMessageChunk(content=f"answer {len(SENT)}"))


@pytest.fixture(autouse=True)
def nothing_sent():
    """Each test starts with no calls sent."""
    SENT.clear()


def test_a_call_without_a_cap_is_refused_before_anything_is_sent(tmp_path):
    """No cap, no call, whether the model is invoked or streamed."""
    model = guard_model(FakeClaude(), spend.Guard(0, tmp_path / "ledger.jsonl"))
    with pytest.raises(spend.SpendRefused, match="paid calls are off"):
        model.invoke("hello")
    with pytest.raises(spend.SpendRefused, match="paid calls are off"):
        list(model.stream("hello"))
    assert SENT == []


def test_streaming_skips_a_bare_cache_which_is_why_guard_model_turns_it_off(tmp_path):
    """LangChain does not ask the cache when a model streams, so a cache alone guards nothing."""
    bare = FakeClaude(cache=SpendCache(spend.Guard(0, tmp_path / "ledger.jsonl")))
    assert "".join(chunk.content for chunk in bare.stream("hello")) == "answer 1"
    assert SENT == ["hello"]


def test_a_live_call_is_priced_in_the_ledger_and_recorded(tmp_path):
    """The provider's usage is priced at the model that answered; a repeat is a new sample."""
    ledger = tmp_path / "ledger.jsonl"
    guard = spend.Guard(1.0, ledger, project="demo")
    model = guard_model(FakeClaude(), guard, spend.Recorder(tmp_path / "rec"), label="triage")
    assert model.invoke("hello").content == "answer 1"
    assert model.invoke("hello").content == "answer 2"
    first, second = spend.read_ledger([ledger])
    assert (first["project"], first["label"], first["model"], first["route"]) == (
        "demo",
        "triage",
        "claude-haiku-5-5",
        "api",
    )
    assert (first["input"], first["cache_write_5m"], first["cache_read"], first["output"]) == (
        100,
        50,
        1000,
        50,
    )
    assert first["billed"] == pytest.approx(PRICE)
    assert second["key"] == first["key"] + ".1"
    assert len(list((tmp_path / "rec").rglob("*.json"))) == 2


def test_a_rerun_replays_the_recordings_in_order_for_free(tmp_path):
    """Replay answers each use of a request with its own recording and never goes live."""
    ledger, root = tmp_path / "ledger.jsonl", tmp_path / "rec"
    recording = guard_model(FakeClaude(), spend.Guard(1.0, ledger), spend.Recorder(root))
    recording.invoke("hello")
    recording.invoke("hello")
    SENT.clear()
    rerun = guard_model(FakeClaude(), spend.Guard(0, ledger), spend.Recorder(root, "replay"))
    assert [rerun.invoke("hello").content for _ in range(2)] == ["answer 1", "answer 2"]
    with pytest.raises(spend.ReplayMiss):
        rerun.invoke("hello")
    assert SENT == []
    rows = spend.read_ledger([ledger])
    assert [row["route"] for row in rows] == ["api", "api", "replay", "replay"]
    assert rows[2]["usd"] == pytest.approx(PRICE) and rows[2]["billed"] == 0


def test_an_agent_loop_replays_every_turn(tmp_path):
    """The next turn carries the last answer back; LangChain marks a replayed answer's usage,
    so the key leaves usage out, or a replay would miss from the second turn on."""

    def loop(model):
        """Two turns, the second holding the first answer."""
        first = model.invoke([HumanMessage(content="hello")])
        return model.invoke([HumanMessage(content="hello"), first, HumanMessage(content="next")])

    root = tmp_path / "rec"
    live = loop(
        guard_model(FakeClaude(), spend.Guard(1.0, tmp_path / "ledger.jsonl"), spend.Recorder(root))
    )
    SENT.clear()
    replayed = loop(guard_model(FakeClaude(), None, spend.Recorder(root, "replay")))
    assert replayed.content == live.content == "answer 2"
    assert replayed.usage_metadata["total_cost"] == 0, "LangChain's own mark on a cached answer"
    assert SENT == []


def test_each_repetition_replays_its_own_answers(tmp_path):
    """Inside `meter(sample=r)` a recording belongs to repetition r, as in `flywheel run`."""
    root = tmp_path / "rec"
    recording = guard_model(
        FakeClaude(), spend.Guard(1.0, tmp_path / "ledger.jsonl"), spend.Recorder(root)
    )
    for repetition in (1, 2):
        with spend.meter(sample=repetition):
            recording.invoke("hello")
    rerun = guard_model(FakeClaude(), None, spend.Recorder(root, "replay"))
    with spend.meter(sample=2) as used:
        assert rerun.invoke("hello").content == "answer 2"
    assert (used.calls, used.replayed, used.billed) == (1, 1, 0)


def test_a_marker_that_changes_every_run_can_be_left_out_of_the_key(tmp_path):
    """With `normalize`, a rerun whose prompt differs only by a random marker replays."""

    def blank(text):
        """The prompt with its random marker blanked."""
        return re.sub(r"marker [0-9a-f]{8}", "marker -", text)

    root = tmp_path / "rec"
    guard = spend.Guard(1.0, tmp_path / "ledger.jsonl")
    recording = guard_model(FakeClaude(), guard, spend.Recorder(root), normalize=blank)
    recording.invoke("evidence inside marker 0123abcd")
    rerun = guard_model(FakeClaude(), None, spend.Recorder(root, "replay"), normalize=blank)
    assert rerun.invoke("evidence inside marker ffff9999").content == "answer 1"
    assert SENT == ["evidence inside marker 0123abcd"], "the prompt sent keeps its marker"
    strict = guard_model(FakeClaude(), None, spend.Recorder(root, "replay"))
    with pytest.raises(spend.ReplayMiss):
        strict.invoke("evidence inside marker ffff9999")


def test_a_model_without_a_price_is_refused(tmp_path):
    """No price, no cap can hold the call."""
    model = guard_model(FakeClaude(model="gpt-5"), spend.Guard(1.0, tmp_path / "ledger.jsonl"))
    with pytest.raises(spend.SpendRefused, match="no price"):
        model.invoke("hello")
    assert SENT == []


def test_async_calls_take_the_same_path_and_count_in_the_meter(tmp_path):
    """`ainvoke` is guarded, ledgered and metered like `invoke`."""
    model = guard_model(FakeClaude(), spend.Guard(1.0, tmp_path / "ledger.jsonl"))

    async def run():
        """Two calls inside one meter block."""
        with spend.meter() as used:
            first = await model.ainvoke("hello")
            await model.ainvoke("hello")
        return first, used

    first, used = asyncio.run(run())
    assert first.content == "answer 1"
    assert (used.calls, used.replayed) == (2, 0)
    assert used.billed == pytest.approx(2 * PRICE)


class Capture(BaseCache):
    """A cache that keeps each call's key and answers every call itself."""

    def __init__(self):
        """No keys yet."""
        self.keys = []

    def lookup(self, prompt, llm_string):
        """Keep the key; answer at once."""
        self.keys.append(request_key(prompt, llm_string))
        return [ChatGeneration(message=AIMessage(content="kept"))]

    def update(self, prompt, llm_string, return_val):
        """Never called: every call is answered."""

    def clear(self, **kwargs):
        """Nothing to clear."""


def key_of(model, text="hello", **marker):
    """The key of one call to `model` with one text block."""
    capture = Capture()
    block = {"type": "text", "text": text, **marker}
    model.model_copy(update={"cache": capture}).invoke([HumanMessage(content=[block], id="m-1")])
    return capture.keys[0]


def test_the_key_ignores_ids_cache_markers_and_transport_settings():
    """Only what shapes the answer is in a call's key."""
    base = key_of(FakeClaude())
    assert key_of(FakeClaude()) == base
    assert key_of(FakeClaude(), cache_control={"type": "ephemeral"}) == base
    assert key_of(FakeClaude(max_retries=5, disable_streaming=True)) == base
    assert key_of(FakeClaude(max_tokens=200)) != base
    assert key_of(FakeClaude(model="claude-sonnet-5-5")) != base
    assert key_of(FakeClaude(), text="hello!") != base
