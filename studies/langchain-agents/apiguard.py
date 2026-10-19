"""A hard spending cap for the paid runs on the Anthropic API.

Every API model call passes through this callback. After each call it prices the tokens the
API reported (list prices per million tokens, cache reads and writes included) and appends them
to a ledger file shared by every process of the run. Before each call it reads the ledger and
refuses to start the call once the total has reached the cap, so a run can overshoot the cap by
at most the price of the calls already in flight.

Environment: `FW_API_CAP` (dollars, required for a paid run) and `FW_API_LEDGER` (a JSONL path).
"""

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

# Dollars per million tokens: input, output, cache read, cache write (5-minute).
PRICES = {
    "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25),
    "claude-sonnet-4-5": (3.00, 15.00, 0.30, 3.75),
}


class CapReached(RuntimeError):
    """The run has spent its cap; no further paid call starts."""


def ledger() -> Path:
    """The shared ledger file."""
    return Path(os.environ.get("FW_API_LEDGER", "api-ledger.jsonl"))


def spent() -> float:
    """Dollars recorded in the ledger so far."""
    path = ledger()
    if not path.exists():
        return 0.0
    return sum(json.loads(line)["usd"] for line in path.read_text().splitlines() if line.strip())


def price(model: str, usage: dict) -> float:
    """The list price of one call's usage."""
    p_in, p_out, p_read, p_write = PRICES[model]
    details = usage.get("input_token_details") or {}
    read = details.get("cache_read") or 0
    write = details.get("cache_creation") or 0
    plain = (usage.get("input_tokens") or 0) - read - write
    out = usage.get("output_tokens") or 0
    return (plain * p_in + out * p_out + read * p_read + write * p_write) / 1e6


class SpendGuard(BaseCallbackHandler):
    """Prices every call and stops new calls once the cap is reached."""

    raise_error = True

    def __init__(self, model: str):
        """Guard calls to `model` under the cap in `FW_API_CAP`."""
        if model not in PRICES:
            raise ValueError(f"no price for {model}")
        self.model = model
        self.cap = float(os.environ["FW_API_CAP"])

    def on_chat_model_start(self, serialized: Any, messages: Any, **kwargs: Any) -> None:
        """Refuse to start a call once the cap is reached."""
        if spent() >= self.cap:
            raise CapReached(f"API spend cap ${self.cap:.2f} reached")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Record the call's price in the ledger."""
        for gens in response.generations:
            for gen in gens:
                usage = getattr(getattr(gen, "message", None), "usage_metadata", None) or {}
                row = {
                    "t": time.time(),
                    "model": self.model,
                    "usd": round(price(self.model, usage), 6),
                    "input": usage.get("input_tokens"),
                    "output": usage.get("output_tokens"),
                    "cache": usage.get("input_token_details"),
                }
                with ledger().open("a") as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    f.write(json.dumps(row) + "\n")
