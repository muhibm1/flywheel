"""Spend tools for paid model calls: prices, a budget guard, record and replay, and a meter.

A paid API call should be the last thing an agent's harness reaches for. These pieces make it
so, in the order a call goes through them:

1. **Replay.** Each call is keyed by a fingerprint of its exact request. A call that was
   recorded before is answered from the recording and costs nothing. Identical requests are
   separate samples, never one answer copied: the n-th use of a request gets the n-th recorded
   answer, so repeated runs keep their spread. In replay mode a miss raises `ReplayMiss`
   instead of going live, so a frozen run can never start spending.
2. **The guard.** A live call needs a dollar cap (`FLYWHEEL_API_CAP` by default). Before each
   call the guard reads the running total from its ledger and refuses once the cap is spent;
   with no cap set, paid calls are off. Calls already in flight can overshoot it, nothing more.
3. **The ledger.** Every call is appended to a JSONL file: model, uncached input, cache writes,
   cache reads, output, the list price, and what was actually billed (nothing for a replay).
   `flywheel spend` totals it.
4. **The meter.** Whatever runs inside `meter()` is counted for that block, so `flywheel run`
   can keep each run's tokens, cache reads and dollars, and the gate can compare them.

Only the standard library is used, like the rest of the core.
"""

import hashlib
import json
import os
import re
import tempfile
import threading
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:  # POSIX: lock the ledger so parallel processes append whole lines.
    import fcntl
except ImportError:  # pragma: no cover - Windows appends without the lock
    fcntl = None

CAP_VARIABLE = "FLYWHEEL_API_CAP"
LEDGER_VARIABLE = "FLYWHEEL_API_LEDGER"
DEFAULT_LEDGER = ".flywheel/api-ledger.jsonl"
ROUTES = ("api", "replay", "subscription")
MODES = ("off", "record", "replay")
FINGERPRINT_VERSION = "v1"
# A request's cache markers change its bytes but not its answer, and streaming is transport.
IGNORED_KEYS = frozenset({"cache_control"})
IGNORED_TOP_LEVEL = frozenset({"stream"})


@dataclass(frozen=True)
class Price:
    """List prices in dollars per million tokens."""

    input: float
    write_5m: float
    write_1h: float
    read: float
    output: float


# Anthropic's list prices (platform.claude.com/docs/en/about-claude/pricing, 2026-10-24).
PRICES: dict[str, Price] = {
    "claude-fable-5-1": Price(10.00, 12.50, 20.00, 0.25, 50.00),
    "claude-fable-5": Price(10.00, 12.50, 20.00, 1.00, 50.00),
    "claude-opus-5-5": Price(4.00, 5.00, 8.00, 0.20, 20.00),
    "claude-opus-5": Price(5.00, 6.25, 10.00, 0.50, 25.00),
    "claude-opus-4-8": Price(5.00, 6.25, 10.00, 0.50, 25.00),
    "claude-opus-4-7": Price(5.00, 6.25, 10.00, 0.50, 25.00),
    "claude-opus-4-6": Price(5.00, 6.25, 10.00, 0.50, 25.00),
    "claude-opus-4-5": Price(5.00, 6.25, 10.00, 0.50, 25.00),
    "claude-sonnet-5-5": Price(2.00, 2.50, 4.00, 0.10, 10.00),
    "claude-sonnet-5": Price(2.00, 2.50, 4.00, 0.20, 10.00),
    "claude-sonnet-4-6": Price(3.00, 3.75, 6.00, 0.30, 15.00),
    "claude-sonnet-4-5": Price(3.00, 3.75, 6.00, 0.30, 15.00),
    "claude-haiku-5-5": Price(0.10, 0.125, 0.20, 0.01, 0.50),
    "claude-haiku-4-5": Price(1.00, 1.25, 2.00, 0.10, 5.00),
}
# Haiku 5.5 is priced by prompt length: a prompt over this many tokens, cache reads and writes
# included, pays these prices for the whole call.
LONG_PROMPT = 100_000
LONG_PROMPT_PRICES: dict[str, Price] = {
    "claude-haiku-5-5": Price(0.50, 0.625, 1.00, 0.05, 2.50),
}
WEB_SEARCH = 0.01  # dollars per web search request


class SpendRefused(RuntimeError):
    """A paid call was refused: paid calls are off, or the cap is spent."""


class ReplayMiss(RuntimeError):
    """Replay asked for a call the recording does not hold."""


# What stops a whole run, not one call: every later call would be refused or missed the same way.
STOPS = (SpendRefused, ReplayMiss)


class UnknownModel(KeyError):
    """No price is listed for the model."""


@dataclass(frozen=True)
class Usage:
    """The tokens of one call, or of several added together."""

    input: int = 0  # input read at the full price
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    cache_read: int = 0
    output: int = 0
    web_searches: int = 0

    @property
    def cache_write(self) -> int:
        """Tokens written to the cache, either lifetime."""
        return self.cache_write_5m + self.cache_write_1h

    @property
    def prompt(self) -> int:
        """The whole prompt: uncached input, cache writes and cache reads."""
        return self.input + self.cache_write + self.cache_read

    @property
    def tokens(self) -> int:
        """Every token the call moved, prompt and output."""
        return self.prompt + self.output

    def __add__(self, other: "Usage") -> "Usage":
        """Both calls' tokens together."""
        return Usage(
            input=self.input + other.input,
            cache_write_5m=self.cache_write_5m + other.cache_write_5m,
            cache_write_1h=self.cache_write_1h + other.cache_write_1h,
            cache_read=self.cache_read + other.cache_read,
            output=self.output + other.output,
            web_searches=self.web_searches + other.web_searches,
        )

    @classmethod
    def from_api(cls, usage: Mapping[str, Any]) -> "Usage":
        """From the Messages API's `usage`, where `input_tokens` is only the uncached part."""
        written = int(usage.get("cache_creation_input_tokens") or 0)
        split = usage.get("cache_creation") or {}
        one_hour = int(split.get("ephemeral_1h_input_tokens") or 0)
        five = int(split.get("ephemeral_5m_input_tokens") or 0)
        if not (five or one_hour):
            five = written
        tools = usage.get("server_tool_use") or {}
        return cls(
            input=int(usage.get("input_tokens") or 0),
            cache_write_5m=five,
            cache_write_1h=one_hour,
            cache_read=int(usage.get("cache_read_input_tokens") or 0),
            output=int(usage.get("output_tokens") or 0),
            web_searches=int(tools.get("web_search_requests") or 0),
        )

    @classmethod
    def from_langchain(cls, usage: Mapping[str, Any]) -> "Usage":
        """From LangChain's `usage_metadata`, where `input_tokens` includes the cache tokens."""
        details = usage.get("input_token_details") or {}
        read = int(details.get("cache_read") or 0)
        one_hour = int(details.get("ephemeral_1h_input_tokens") or 0)
        five = int(details.get("ephemeral_5m_input_tokens") or 0)
        if not (five or one_hour):
            five = int(details.get("cache_creation") or 0)
        total = int(usage.get("input_tokens") or 0)
        return cls(
            input=max(total - read - five - one_hour, 0),
            cache_write_5m=five,
            cache_write_1h=one_hour,
            cache_read=read,
            output=int(usage.get("output_tokens") or 0),
        )


def model_key(model: str) -> str:
    """The price-list name of a model id: no provider prefix, date suffix or context tag."""
    name = model.rsplit(":", 1)[-1].strip().lower()
    name = re.sub(r"\[[^\]]*\]$", "", name)
    return re.sub(r"-\d{8}$", "", name)


def price(model: str, usage: Usage) -> float:
    """The list price of `usage` on `model`, in dollars."""
    key = model_key(model)
    rates = LONG_PROMPT_PRICES.get(key) if usage.prompt > LONG_PROMPT else None
    rates = rates or PRICES.get(key)
    if rates is None:
        raise UnknownModel(f"no price for {model!r}; add it to flywheel.spend.PRICES")
    tokens = (
        usage.input * rates.input
        + usage.cache_write_5m * rates.write_5m
        + usage.cache_write_1h * rates.write_1h
        + usage.cache_read * rates.read
        + usage.output * rates.output
    )
    return tokens / 1e6 + usage.web_searches * WEB_SEARCH


def cache_share(usage: Usage) -> float | None:
    """The share of the prompt read from the cache; None when there was no prompt."""
    return usage.cache_read / usage.prompt if usage.prompt else None


# --- the meter ---------------------------------------------------------------------------------


@dataclass
class Meter:
    """The calls made inside one `meter()` block."""

    calls: int = 0
    replayed: int = 0
    subscription: int = 0
    unpriced: int = 0
    usage: Usage = field(default_factory=Usage)
    usd: float = 0.0  # list price of the priced calls, paid or replayed
    billed: float = 0.0  # what was actually spent
    # The run's repetition, when the block is one run of a repeated case: it names the run's
    # recorded answers, so each repetition keeps its own (`Recorder.claim`).
    sample: int | None = None
    _claims: dict[str, int] = field(default_factory=dict, repr=False, compare=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def claim(self, key: str) -> int:
        """How many times this block used `key` before now."""
        with self._lock:
            used = self._claims.get(key, 0)
            self._claims[key] = used + 1
        return used

    def add(self, usage: Usage, route: str, usd: float | None) -> None:
        """Count one call."""
        with self._lock:
            self.calls += 1
            self.usage = self.usage + usage
            self.replayed += route == "replay"
            self.subscription += route == "subscription"
            if usd is None:
                self.unpriced += route != "subscription"
                return
            self.usd += usd
            if route == "api":
                self.billed += usd

    def summary(self) -> dict[str, Any] | None:
        """What a run keeps of its calls; None when it made none.

        Dollars appear only when every call was priced: a run that answered through a
        subscription has tokens, not a price."""
        if not self.calls:
            return None
        out: dict[str, Any] = {
            "calls": self.calls,
            "replayed": self.replayed,
            "subscription": self.subscription,
            "input": self.usage.input,
            "cache_write": self.usage.cache_write,
            "cache_read": self.usage.cache_read,
            "output": self.usage.output,
            "billed": round(self.billed, 9),
        }
        if not (self.subscription or self.unpriced):
            out["usd"] = round(self.usd, 9)
        return out


_current: ContextVar[Meter | None] = ContextVar("flywheel_spend_meter", default=None)


@contextmanager
def meter(sample: int | None = None) -> Iterator[Meter]:
    """Count every call noted inside the block, in this thread and in tasks it copies to.

    `sample` is the block's repetition when it is one run of a repeated case; recordings made
    inside it are kept per repetition."""
    current = Meter(sample=sample)
    token = _current.set(current)
    try:
        yield current
    finally:
        _current.reset(token)


def current() -> Meter | None:
    """The meter of the block this code runs in, if any."""
    return _current.get()


def note(model: str, usage: Usage, route: str = "api") -> float | None:
    """Count one call in the current meter, if any; its list price, or None when unpriced.

    `route` is `api` for a paid call, `replay` for one answered from a recording and
    `subscription` for one answered through a subscription, which is never priced."""
    if route not in ROUTES:
        raise ValueError(f"route must be one of {ROUTES}, not {route!r}")
    usd = None
    if route != "subscription":
        try:
            usd = price(model, usage)
        except UnknownModel:
            usd = None
    current = _current.get()
    if current is not None:
        current.add(usage, route, usd)
    return usd


# --- the guard and its ledger ------------------------------------------------------------------


class Guard:
    """A dollar cap on paid calls, kept against a ledger file shared by every process."""

    def __init__(
        self,
        cap: float | None,
        ledger: Path | str = DEFAULT_LEDGER,
        *,
        project: str = "",
        cap_variable: str = CAP_VARIABLE,
    ):
        """Allow paid calls up to `cap` dollars in total; None or 0 turns them off."""
        self.cap = cap or 0.0
        self.ledger = Path(ledger)
        self.project = project
        self.cap_variable = cap_variable
        self._lock = threading.Lock()

    @classmethod
    def from_env(
        cls,
        *,
        project: str = "",
        cap_variable: str = CAP_VARIABLE,
        ledger_variable: str = LEDGER_VARIABLE,
        default_ledger: str = DEFAULT_LEDGER,
    ) -> "Guard":
        """A guard whose cap and ledger come from the environment; no cap means no paid calls."""
        try:
            cap = max(0.0, float(os.environ.get(cap_variable, "0") or 0))
        except ValueError:
            cap = 0.0
        ledger = os.environ.get(ledger_variable) or default_ledger
        return cls(cap, ledger, project=project, cap_variable=cap_variable)

    def spent(self) -> float:
        """Dollars billed so far, by the ledger."""
        return sum(row.get("billed", 0.0) for row in read_ledger([self.ledger]))

    def require(self, purpose: str = "a paid model call", model: str | None = None) -> None:
        """Refuse a paid call unless a cap is set and not yet spent, and its model has a price."""
        if self.cap <= 0:
            raise SpendRefused(
                f"{purpose} needs API credit, and paid calls are off. Replay a recording, use "
                f"the subscription, or set {self.cap_variable} to a dollar cap."
            )
        if model is not None and model_key(model) not in PRICES:
            raise SpendRefused(f"{purpose} refused: {model!r} has no price, so no cap can hold it")
        used = self.spent()
        if used >= self.cap:
            raise SpendRefused(
                f"{purpose} refused: ${used:.2f} of the ${self.cap:.2f} cap is already spent"
            )

    def record(
        self,
        model: str,
        usage: Usage,
        *,
        route: str = "api",
        key: str | None = None,
        label: str = "",
    ) -> float | None:
        """Count one call in the current meter and append it to the ledger; its list price."""
        usd = note(model, usage, route)
        row = {
            "t": datetime.now(UTC).isoformat(timespec="seconds"),
            "project": self.project,
            "label": label,
            "model": model_key(model),
            "route": route,
            "input": usage.input,
            "cache_write_5m": usage.cache_write_5m,
            "cache_write_1h": usage.cache_write_1h,
            "cache_read": usage.cache_read,
            "output": usage.output,
            "web_searches": usage.web_searches,
            "usd": None if usd is None else round(usd, 9),
            "billed": round(usd or 0.0, 9) if route == "api" else 0.0,
            "key": key,
        }
        line = json.dumps(row, sort_keys=True) + "\n"
        with self._lock:
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger.open("a", encoding="utf-8") as handle:
                if fcntl is not None:
                    fcntl.flock(handle, fcntl.LOCK_EX)
                handle.write(line)
        return usd


def read_ledger(paths: Iterable[Path | str]) -> list[dict[str, Any]]:
    """Every row of the ledgers; a missing file reads as empty, a torn last line is skipped."""
    rows = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def row_usage(row: Mapping[str, Any]) -> Usage:
    """The tokens of one ledger row."""
    return Usage(
        input=int(row.get("input") or 0),
        cache_write_5m=int(row.get("cache_write_5m") or 0),
        cache_write_1h=int(row.get("cache_write_1h") or 0),
        cache_read=int(row.get("cache_read") or 0),
        output=int(row.get("output") or 0),
        web_searches=int(row.get("web_searches") or 0),
    )


@dataclass
class Tally:
    """Ledger rows added up."""

    calls: int = 0
    replayed: int = 0
    usage: Usage = field(default_factory=Usage)
    billed: float = 0.0
    saved: float = 0.0  # list price of the calls a recording answered

    def add(self, row: Mapping[str, Any]) -> None:
        """Count one row."""
        self.calls += 1
        self.usage = self.usage + row_usage(row)
        self.billed += float(row.get("billed") or 0.0)
        if row.get("route") == "replay":
            self.replayed += 1
            self.saved += float(row.get("usd") or 0.0)


def tally(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Totals overall and by day, model and project."""
    total = Tally()
    groups: dict[str, dict[str, Tally]] = {"day": {}, "model": {}, "project": {}}
    for row in rows:
        total.add(row)
        keys = {
            "day": str(row.get("t") or "")[:10] or "?",
            "model": str(row.get("model") or "?"),
            "project": str(row.get("project") or "-"),
        }
        for group, key in keys.items():
            groups[group].setdefault(key, Tally()).add(row)
    return {"total": total, **groups}


# --- record and replay -------------------------------------------------------------------------


def _strip(value: Any) -> Any:
    """`value` without cache markers, at any depth."""
    if isinstance(value, Mapping):
        return {k: _strip(v) for k, v in value.items() if k not in IGNORED_KEYS}
    if isinstance(value, list | tuple):
        return [_strip(v) for v in value]
    return value


def fingerprint(request: Mapping[str, Any]) -> str:
    """The key of one call: a hash of everything in the request that shapes the answer.

    Cache markers and the streaming flag are left out, so turning caching on keeps every
    recording valid. Key order does not matter; any other change is a different call."""
    body = {k: v for k, v in _strip(request).items() if k not in IGNORED_TOP_LEVEL}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(f"{FINGERPRINT_VERSION}:{text}".encode()).hexdigest()


class Recorder:
    """Answers stored one file per call under `root`, named by the call's fingerprint.

    `record` serves a stored answer when there is one and stores every new one; `replay` serves
    stored answers only and raises `ReplayMiss` for anything else; `off` stores nothing. Keep one
    recorder for a whole run: it counts the uses of each request (`claim`)."""

    def __init__(self, root: Path | str, mode: str = "record"):
        """Use the recordings under `root` in `mode`."""
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
        self.root = Path(root)
        self.mode = mode
        self.hits = 0
        self.misses = 0
        self._claims: dict[str, int] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls, variable: str = "FLYWHEEL_REPLAY", default_root: str = ".flywheel/replay"):
        """A recorder set by `<variable>=record|replay|off` and `<variable>_DIR`; off if unset."""
        mode = os.environ.get(variable, "off") or "off"
        return cls(os.environ.get(f"{variable}_DIR") or default_root, mode)

    def claim(self, key: str) -> str:
        """The slot of this use of `key`: where its answer is recorded, or replayed from.

        An agent run three times sends the same first request three times, and needs three
        answers, not one answer three times, or every repeat would agree and the spread the
        repeats exist to measure would vanish. So the n-th use of a key in a run gets its own
        slot, and a later run of the same work replays the same answers in turn. Inside
        `meter(sample=r)`, as each repetition of `flywheel run` is, uses are counted per run and
        the slot names the repetition: repetition r replays repetition r's answers in any later
        run, so a request a change left alone replays on the pull request's side too, while
        runs of further repetitions record new answers."""
        current = _current.get()
        if current is not None and current.sample is not None:
            used, slot = current.claim(key), f"{key}.r{current.sample}"
        else:
            with self._lock:
                used = self._claims.get(key, 0)
                self._claims[key] = used + 1
            slot = key
        return slot if used == 0 else f"{slot}.{used}"

    def path(self, key: str) -> Path:
        """Where the answer to `key`, a fingerprint or a slot that starts with one, is stored."""
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        """The stored call for `key`, or None."""
        if self.mode == "off":
            return None
        path = self.path(key)
        found = None
        if path.exists():
            found = json.loads(path.read_text(encoding="utf-8"))
        with self._lock:
            if found is None:
                self.misses += 1
            else:
                self.hits += 1
        return found

    def put(self, key: str, model: str, response: Any, usage: Usage, label: str = "") -> None:
        """Store one answer; written whole or not at all."""
        if self.mode != "record":
            return
        stored = {
            "key": key,
            "model": model_key(model),
            "label": label,
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "usage": asdict(usage),
            "response": response,
        }
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(stored, out, indent=1, sort_keys=True, ensure_ascii=False)
        os.replace(temporary, path)


def api_usage(response: Any) -> Usage:
    """The usage of a Messages API response, as a dict."""
    return Usage.from_api((response or {}).get("usage") or {})


def call(
    request: Mapping[str, Any],
    send: Callable[[Mapping[str, Any]], Any],
    *,
    guard: Guard | None,
    recorder: Recorder | None = None,
    usage_of: Callable[[Any], Usage] = api_usage,
    label: str = "",
) -> Any:
    """One model call through the ladder: a recorded answer if there is one, else a paid call
    under the guard, recorded for next time.

    `request` must name its `model`; `send` makes the live call and returns a JSON-safe
    response, from which `usage_of` reads the tokens (a Messages API body by default)."""
    model = str(request.get("model") or "")
    key = fingerprint(request)
    if recorder is not None and recorder.mode != "off":
        key = recorder.claim(key)
        stored = recorder.get(key)
        if stored is not None:
            replayed(model, stored, guard, label)
            return stored["response"]
        if recorder.mode == "replay":
            raise ReplayMiss(f"no recording for this call ({model}, slot {key[:12]}...{key[64:]})")
    if guard is None:
        raise SpendRefused("a paid model call needs a budget guard, and none was given")
    guard.require(f"a call to {model}" + (f" ({label})" if label else ""), model=model)
    response = send(request)
    usage = usage_of(response)
    guard.record(model, usage, route="api", key=key, label=label)
    if recorder is not None:
        recorder.put(key, model, response, usage, label)
    return response


def replayed(model: str, stored: Mapping[str, Any], guard: Guard | None, label: str = "") -> None:
    """Count a call answered from a recording: in the guard's ledger at no cost, or the meter."""
    usage = Usage(**stored["usage"])
    if guard is not None:
        guard.record(model, usage, route="replay", key=stored.get("key"), label=label)
    else:
        note(model, usage, "replay")
