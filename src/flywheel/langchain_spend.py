"""The spend guard and replay for LangChain chat models, through LangChain's own cache slot.

LangChain asks a chat model's cache before it sends a call and hands the cache the answer after,
which is the shape of `spend.call`. `SpendCache` fills that slot: a call recorded before is
answered from the recording; any other call needs the guard's yes before it is sent, and is added
to the ledger and recorded once it returns. A refusal or a replay miss is raised before anything
is sent.

LangChain does not ask the cache when a model streams through `stream()` or `astream()`, so
`guard_model` also turns the model's streaming off: those calls go through `invoke` instead and
arrive whole. A graph that streams its messages still works, one whole message at a time.

Needs `langchain-core` (the `langchain` extra); the rest of Flywheel does not.
"""

import json
import re
import threading
import warnings
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core._api import LangChainBetaWarning
from langchain_core.caches import BaseCache
from langchain_core.load import dumps, loads

from flywheel import spend

# Model settings that change how a call travels, never what it answers. They are left out of a
# call's key, so a recording made with one endpoint, timeout or retry count replays under another.
TRANSPORT_SETTINGS = frozenset(
    {
        "anthropic_api_key",
        "anthropic_api_url",
        "anthropic_proxy",
        "api_key",
        "base_url",
        "default_request_timeout",
        "timeout",
        "max_retries",
        "stream_usage",
        "streaming",
        "disable_streaming",
    }
)
_MODEL_SETTING = re.compile(r"\('model(?:_name)?', '([^']+)'\)")
# What LangChain rewrites in an answer it takes from a cache: it zeroes the answer's cost in its
# `usage_metadata`. An agent loop sends that answer back in its next request, which would then
# key differently on a replay than on the live run that recorded it. No provider is sent an
# earlier answer's usage, so it is left out of the key.
MESSAGE_METADATA = frozenset({"usage_metadata"})


def describe(llm_string: str) -> tuple[dict[str, Any], str]:
    """What in LangChain's `llm_string` shapes a call's answer, and the model it names.

    A serializable model's string is its JSON description, then `---`, then the call's own
    settings (tools, stop sequences); any other model's is only those settings."""
    try:
        model, end = json.JSONDecoder().raw_decode(llm_string)
    except ValueError:
        model, end = None, 0
    if isinstance(model, dict) and llm_string.startswith("---", end):
        settings = model.get("kwargs") or {}
        kept = {k: v for k, v in settings.items() if k not in TRANSPORT_SETTINGS}
        name = str(kept.get("model") or kept.get("model_name") or "")
        return {"model": {**model, "kwargs": kept}, "call": llm_string[end + 3 :]}, name
    found = _MODEL_SETTING.search(llm_string)
    return {"call": llm_string}, found.group(1) if found else ""


def request_key(prompt: str, llm_string: str) -> str:
    """The fingerprint of one LangChain call: its messages and the settings that shape the answer.

    LangChain has already cleared the messages' ids; cache markers are dropped like in
    `spend.fingerprint`, and so are the transport settings and the usage of earlier answers
    (`MESSAGE_METADATA`)."""
    try:
        messages = json.loads(prompt)
    except ValueError:
        messages = prompt
    if isinstance(messages, list):
        messages = [without_metadata(message) for message in messages]
    settings, _ = describe(llm_string)
    return spend.fingerprint({"messages": messages, **settings})


def without_metadata(message: Any) -> Any:
    """A serialized message without `MESSAGE_METADATA`."""
    kwargs = message.get("kwargs") if isinstance(message, dict) else None
    if not isinstance(kwargs, dict):
        return message
    kept = {k: v for k, v in kwargs.items() if k not in MESSAGE_METADATA}
    return {**message, "kwargs": kept}


def answer_usage(generations: Sequence[Any]) -> spend.Usage:
    """The tokens of a LangChain answer: the provider's own usage when the message carries it,
    else LangChain's `usage_metadata`."""
    total = spend.Usage()
    for generation in generations:
        message = getattr(generation, "message", None)
        raw = (getattr(message, "response_metadata", None) or {}).get("usage")
        if isinstance(raw, Mapping) and "input_tokens" in raw:
            total = total + spend.Usage.from_api(raw)
        elif getattr(message, "usage_metadata", None):
            total = total + spend.Usage.from_langchain(message.usage_metadata)
    return total


def answer_model(generations: Sequence[Any], requested: str) -> str:
    """The model that answered, as the provider named it, else the one asked for."""
    for generation in generations:
        message = getattr(generation, "message", None)
        metadata = getattr(message, "response_metadata", None) or {}
        name = metadata.get("model_name") or metadata.get("model")
        if name:
            return str(name)
    return requested


class SpendCache(BaseCache):
    """A LangChain cache that answers from recordings and sends every other call through the
    spend guard. Give it to a chat model with `guard_model`."""

    def __init__(
        self,
        guard: spend.Guard | None,
        recorder: spend.Recorder | None = None,
        *,
        label: str = "",
        normalize: Callable[[str], str] | None = None,
    ):
        """Guard live calls with `guard`, and answer from `recorder` when it has the call.

        `normalize` rewrites a prompt before it is keyed, to blank what changes on every run
        without changing the question, such as a random marker around untrusted text. The
        prompt sent is never changed."""
        self.guard = guard
        self.recorder = recorder
        self.label = label
        self.normalize = normalize
        # The slot each live call was given, waiting for its answer (`update`).
        self._waiting: dict[tuple[str, int], deque[str]] = {}
        self._lock = threading.Lock()

    def _key(self, prompt: str, llm_string: str) -> str:
        """The key of one call, after `normalize`."""
        return request_key(self.normalize(prompt) if self.normalize else prompt, llm_string)

    def _place(self, key: str) -> tuple[str, int]:
        """Where a call waits for its answer: its key, in the meter block it runs in."""
        return key, id(spend.current())

    def lookup(self, prompt: str, llm_string: str) -> list[Any] | None:
        """A recorded answer, or None once the guard allows a live call; raises otherwise."""
        key = self._key(prompt, llm_string)
        _, model = describe(llm_string)
        slot = key
        recorder = self.recorder
        if recorder is not None and recorder.mode != "off":
            slot = recorder.claim(key)
            stored = recorder.get(slot)
            if stored is not None:
                spend.replayed(stored.get("model") or model, stored, self.guard, self.label)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", LangChainBetaWarning)
                    return loads(json.dumps(stored["response"]), allowed_objects="core")
            if recorder.mode == "replay":
                raise spend.ReplayMiss(
                    f"no recording for this call ({model}, slot {slot[:12]}...{slot[64:]})"
                )
        if self.guard is None:
            raise spend.SpendRefused("a paid model call needs a budget guard, and none was given")
        name = model or "a model with no name"
        self.guard.require(f"a call to {name}" + (f" ({self.label})" if self.label else ""), model)
        with self._lock:
            self._waiting.setdefault(self._place(key), deque()).append(slot)
        return None

    def update(self, prompt: str, llm_string: str, return_val: Sequence[Any]) -> None:
        """Add a live answer to the ledger, and record it when recording."""
        key = self._key(prompt, llm_string)
        _, requested = describe(llm_string)
        with self._lock:
            waiting = self._waiting.get(self._place(key))
            slot = waiting.popleft() if waiting else key
            if waiting is not None and not waiting:
                del self._waiting[self._place(key)]
        model = answer_model(return_val, requested)
        usage = answer_usage(return_val)
        if self.guard is not None:
            self.guard.record(model, usage, route="api", key=slot, label=self.label)
        if self.recorder is not None:
            self.recorder.put(slot, model, json.loads(dumps(list(return_val))), usage, self.label)

    def clear(self, **kwargs: Any) -> None:
        """Forget the calls waiting for an answer. Recordings are kept: deleting them is a
        person's call."""
        with self._lock:
            self._waiting.clear()

    async def alookup(self, prompt: str, llm_string: str) -> list[Any] | None:
        """`lookup`, in the caller's context so its meter block counts the call."""
        return self.lookup(prompt, llm_string)

    async def aupdate(self, prompt: str, llm_string: str, return_val: Sequence[Any]) -> None:
        """`update`, in the caller's context."""
        self.update(prompt, llm_string, return_val)

    async def aclear(self, **kwargs: Any) -> None:
        """`clear`."""
        self.clear(**kwargs)


def guard_model(
    model: Any,
    guard: spend.Guard | None,
    recorder: spend.Recorder | None = None,
    *,
    label: str = "",
    normalize: Callable[[str], str] | None = None,
) -> Any:
    """A copy of a LangChain chat model whose every call goes through a `SpendCache`, with
    streaming off so that no call can skip it."""
    cache = SpendCache(guard, recorder, label=label, normalize=normalize)
    return model.model_copy(update={"cache": cache, "disable_streaming": True})
