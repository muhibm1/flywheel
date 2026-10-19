"""A LangChain chat model that answers through headless Claude Code on a Claude subscription.

The agents under test expect an API-backed chat model. This one gives them the same interface
(`invoke`, `bind_tools`, `with_structured_output`) without an API key: every model call becomes
one `claude -p` call, signed in to the subscription, with the API key variables removed from the
child's environment.

Each call is stateless. The conversation is rendered as a transcript, and the reply is JSON that
must match a schema: a list of tool calls when tools are bound, or one object for structured
output. The agent's own graph, prompts and tools are untouched; only the model transport differs.
That difference is disclosed in the results.

Token usage of every call is appended to `USAGE_LOG`, so a paid run can be estimated from it.
"""

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel

KEY_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "AGENTOPS_TEST_ANTHROPIC_API_KEY")
TIMEOUT = 600
ATTEMPTS = 3
MAX_PARALLEL = int(os.environ.get("SUBCHAT_PARALLEL", "4"))
USAGE_LOG = Path(os.environ.get("SUBCHAT_USAGE_LOG", "usage.jsonl"))
_slots = threading.BoundedSemaphore(MAX_PARALLEL)
_log_lock = threading.Lock()


class SubscriptionError(RuntimeError):
    """A headless call failed after every attempt."""


def _run(args: list[str], prompt: str) -> dict:
    """One headless Claude Code call in an empty folder; its parsed JSON result."""
    exe = shutil.which("claude")
    if not exe:
        raise SubscriptionError("the claude command is not installed")
    env = {k: v for k, v in os.environ.items() if k not in KEY_VARIABLES}
    with _slots, tempfile.TemporaryDirectory(prefix="fw-cc-") as cwd:
        done = subprocess.run(
            [exe, "-p", *args],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=cwd,
            env=env,
            check=False,
        )
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError as error:
        detail = (done.stderr or done.stdout)[-300:]
        raise SubscriptionError(f"claude exited {done.returncode}: {detail}") from error


def _args(model: str, system: str, schema: dict | None) -> list[str]:
    """Flags for a lean call: no tools, settings, MCP servers or saved session."""
    args = [
        "--output-format", "json",
        "--model", model,
        "--tools", "",
        "--strict-mcp-config",
        "--setting-sources", "",
        "--no-session-persistence",
        "--system-prompt", system or " ",
    ]
    if schema is not None:
        args += ["--json-schema", json.dumps(schema)]
    return args


def _log(model: str, result: dict, chars: int) -> dict:
    """Record one call's tokens and prompt size, and return the tokens in LangChain's shape.

    The subscription's own token counts include Claude Code's fixed overhead, so `chars` (the
    system prompt, schema and transcript this agent actually sent) is what a paid estimate uses.
    """
    u = result.get("usage") or {}
    plain = u.get("input_tokens") or 0
    read = u.get("cache_read_input_tokens") or 0
    write = u.get("cache_creation_input_tokens") or 0
    out = u.get("output_tokens") or 0
    row = {"t": time.time(), "model": model, "input": plain, "cache_read": read,
           "cache_write": write, "output": out, "chars": chars}
    with _log_lock, USAGE_LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")
    total_in = plain + read + write
    return {"input_tokens": total_in, "output_tokens": out, "total_tokens": total_in + out}


LIMIT_WAIT = 600  # seconds between checks while the subscription's usage window is spent


def _limited(result: dict) -> bool:
    """Whether a reply says the subscription's usage window is spent."""
    return "hit your session limit" in str(result.get("result") or "").lower()


def _call(model: str, system: str, schema: dict | None, prompt: str) -> tuple[dict, dict]:
    """A retried call that must return structured output (or text when `schema` is None).

    A spent usage window is not a failure of the agent: the call waits for the window to reset
    and tries again, so a long experiment pauses instead of recording errors."""
    last = ""
    attempt = 0
    while attempt < ATTEMPTS:
        try:
            result = _run(_args(model, system, schema), prompt)
        except (SubscriptionError, subprocess.TimeoutExpired) as error:
            last = str(error)[:300]
            attempt += 1
            continue
        if _limited(result):
            time.sleep(LIMIT_WAIT)
            continue
        attempt += 1
        if schema is not None:
            ok = isinstance(result.get("structured_output"), dict)
        else:
            ok = bool(str(result.get("result") or "").strip())
        if not result.get("is_error") and ok:
            chars = len(system) + len(prompt) + len(json.dumps(schema) if schema else "")
            return result, _log(model, result, chars)
        last = str(result.get("result") or result.get("subtype") or "empty reply")[:300]
    raise SubscriptionError(f"headless call failed {ATTEMPTS} times: {last}")


def _text(content: Any) -> str:
    """A message's content as plain text."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block["text"])
    return "\n".join(parts)


def render(messages: list[BaseMessage]) -> tuple[str, str]:
    """Split messages into a system prompt and a transcript."""
    system = "\n\n".join(_text(m.content) for m in messages if isinstance(m, SystemMessage))
    lines = []
    for m in messages:
        if isinstance(m, HumanMessage):
            lines.append(f"USER:\n{_text(m.content)}")
        elif isinstance(m, AIMessage):
            said = _text(m.content).strip()
            if said:
                lines.append(f"YOU SAID:\n{said}")
            for c in m.tool_calls or []:
                args = json.dumps(c["args"], ensure_ascii=False, default=str)
                lines.append(f"YOU CALLED {c['name']}({args})")
        elif isinstance(m, ToolMessage):
            lines.append(f"RESULT of {m.name or 'tool'}:\n{_text(m.content)}")
    return system, "\n\n".join(lines)


def inline(schema: dict) -> dict:
    """A JSON schema with `$defs` inlined and titles dropped, for --json-schema."""
    schema = json.loads(json.dumps(schema))
    defs = schema.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            return {k: walk(v) for k, v in node.items() if k not in ("title", "default")}
        return [walk(v) for v in node] if isinstance(node, list) else node

    return walk(schema)


def tool_schema(tools: list, at_least_one: bool) -> tuple[dict, str]:
    """The reply shape for a tool-using turn, and the guide appended to the system prompt."""
    shapes, names = [], []
    for t in tools:
        spec = convert_to_openai_tool(t)["function"]
        names.append(spec["name"])
        params = inline(spec.get("parameters") or {"type": "object", "properties": {}})
        params["additionalProperties"] = False
        shapes.append({
            "type": "object",
            "properties": {"tool": {"const": spec["name"]}, "args": params},
            "required": ["tool", "args"],
            "additionalProperties": False,
        })
    calls: dict = {"type": "array", "items": {"anyOf": shapes}}
    if at_least_one:
        calls["minItems"] = 1
    schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}, "calls": calls},
        "required": ["text", "calls"],
        "additionalProperties": False,
    }
    # The headless session has no native tools except the one that returns this JSON, and the
    # agent's prompts say "use the sql_db_query tool". Without this framing a model sometimes
    # told the user the tools were unavailable instead of requesting them.
    guide = (
        "\n\nHOW ACTIONS WORK HERE: you have no native tools in this setup. Every tool named "
        f"above or below ({', '.join(names)}) is requested by listing it in the `calls` field "
        "of your JSON reply; the system runs it and returns its result in the next turn's "
        "transcript. So all of these tools ARE available: never tell the user they are not. "
        'Reply as {"text": words to the user, "calls": [{"tool": name, "args": {...}}]}.'
        + (" You must request at least one tool." if at_least_one
           else " When you are finished, reply with an empty list of calls and your final answer "
                "to the user in text; text must not be empty then.")
    )
    return schema, guide


class SubscriptionChat(BaseChatModel):
    """A chat model answered by headless Claude Code on the subscription."""

    model_id: str = "claude-haiku-4-5"
    turns: int = 0

    @property
    def _llm_type(self) -> str:
        """LangChain's name for this kind of model."""
        return "subscription-claude-code"

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        """Answer with text, or with tool calls when tools are bound."""
        tools = kwargs.get("tools")
        system, transcript = render(messages)
        if tools:
            forced = kwargs.get("tool_choice") in ("any", "required")
            schema, guide = tool_schema(tools, forced)
            prompt = (transcript or "Begin.") + "\n\nChoose your next tool calls."
            result, usage = _call(self.model_id, system + guide, schema, prompt)
            self.turns += 1
            out = result["structured_output"]
            calls = [
                {"name": c["tool"], "args": c.get("args") or {},
                 "id": f"sc{self.turns}-{i}", "type": "tool_call"}
                for i, c in enumerate(out.get("calls", []))
            ]
            message = AIMessage(content=out.get("text") or "", tool_calls=calls, usage_metadata=usage)
        else:
            result, usage = _call(self.model_id, system, None, transcript or "Answer now.")
            message = AIMessage(content=str(result["result"]), usage_metadata=usage)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def bind_tools(self, tools: list, tool_choice: Any = None, **kwargs: Any):
        """A runnable whose replies are calls to `tools`."""
        return self.bind(tools=list(tools), tool_choice=tool_choice)

    def with_structured_output(self, schema: Any, **kwargs: Any):
        """A runnable that answers in one Pydantic schema."""

        def run(messages: Any) -> BaseModel:
            msgs = self._convert_input(messages).to_messages()
            system, transcript = render(msgs)
            result, _ = _call(self.model_id, system, inline(schema.model_json_schema()),
                              transcript or "Answer now.")
            return schema.model_validate(result["structured_output"])

        return RunnableLambda(run)
