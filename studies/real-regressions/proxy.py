"""An OpenAI-compatible chat endpoint answered by headless the harness on a Claude subscription.

Every agent framework in this study can talk to an OpenAI-style `/v1/chat/completions` URL. This
server gives them one, so each project's own agent code runs unchanged at both commits while the
model calls go to the subscription instead of an API key. The transport is the same for the base
and the head of every change, so it cannot explain a difference between them.

Each request becomes one stateless `claude -p` call: the conversation is rendered as a transcript,
and the reply is JSON that must match a schema (tool calls when tools are offered, the caller's
schema when it asks for structured output). API-key variables are removed from the child's
environment. Every call's tokens are appended to `PROXY_USAGE_LOG`.

Run: python proxy.py --port 8765 --model claude-haiku-4-5
"""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

KEY_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "AGENTOPS_TEST_ANTHROPIC_API_KEY")
TIMEOUT = 600
ATTEMPTS = 3
LIMIT_WAIT = 600
MAX_PARALLEL = int(os.environ.get("PROXY_PARALLEL", "4"))
USAGE_LOG = Path(os.environ.get("PROXY_USAGE_LOG", "proxy-usage.jsonl"))
_slots = threading.BoundedSemaphore(MAX_PARALLEL)
_log_lock = threading.Lock()


class CallFailed(RuntimeError):
    """A headless call failed after every attempt."""


def _run(args: list[str], prompt: str) -> dict:
    """One headless call in an empty folder; its parsed JSON result."""
    exe = shutil.which("claude")
    if not exe:
        raise CallFailed("the claude command is not installed")
    env = {k: v for k, v in os.environ.items() if k not in KEY_VARIABLES}
    with _slots, tempfile.TemporaryDirectory(prefix="rr-cc-") as cwd:
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
        raise CallFailed(f"claude exited {done.returncode}: {(done.stderr or done.stdout)[-300:]}") from error


def _args(model: str, system: str, schema: dict | None) -> list[str]:
    """Flags for a lean call: no tools, settings, MCP servers or saved session."""
    args = ["--output-format", "json", "--model", model, "--tools", "", "--strict-mcp-config",
            "--setting-sources", "", "--no-session-persistence", "--system-prompt", system or " "]
    if schema is not None:
        args += ["--json-schema", json.dumps(schema)]
    return args


def _call(model: str, system: str, schema: dict | None, prompt: str, tag: str) -> dict:
    """A retried call; waits out a spent usage window instead of failing."""
    last, attempt = "", 0
    while attempt < ATTEMPTS:
        try:
            result = _run(_args(model, system, schema), prompt)
        except (CallFailed, subprocess.TimeoutExpired) as error:
            last, attempt = str(error)[:300], attempt + 1
            continue
        text = str(result.get("result") or "")
        if "hit your session limit" in text.lower() or "usage limit" in text.lower():
            time.sleep(LIMIT_WAIT)
            continue
        attempt += 1
        ok = isinstance(result.get("structured_output"), dict) if schema is not None else bool(text.strip())
        if not result.get("is_error") and ok:
            u = result.get("usage") or {}
            with _log_lock, USAGE_LOG.open("a") as f:
                f.write(json.dumps({"t": time.time(), "tag": tag, "model": model,
                                    "input": u.get("input_tokens"), "cache_read": u.get("cache_read_input_tokens"),
                                    "cache_write": u.get("cache_creation_input_tokens"),
                                    "output": u.get("output_tokens"), "chars": len(system) + len(prompt)}) + "\n")
            return result
        last = (text or str(result.get("subtype") or "empty reply"))[:300]
    raise CallFailed(f"headless call failed {ATTEMPTS} times: {last}")


def _text(content: Any) -> str:
    """A message's content as plain text (images are noted, not sent)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            if block.get("type") in ("text", "input_text"):
                parts.append(block.get("text", ""))
            elif block.get("type") in ("image_url", "image"):
                parts.append("[image omitted]")
    return "\n".join(parts)


def render(messages: list[dict]) -> tuple[str, str]:
    """Split OpenAI-style messages into a system prompt and a transcript."""
    system = "\n\n".join(_text(m.get("content")) for m in messages if m.get("role") in ("system", "developer"))
    lines = []
    for m in messages:
        role = m.get("role")
        if role == "user":
            lines.append(f"USER:\n{_text(m.get('content'))}")
        elif role == "assistant":
            said = _text(m.get("content")).strip()
            if said:
                lines.append(f"YOU SAID:\n{said}")
            for c in m.get("tool_calls") or []:
                fn = c.get("function") or {}
                lines.append(f"YOU CALLED {fn.get('name')}({fn.get('arguments') or '{}'}) [id {c.get('id')}]")
        elif role in ("tool", "function"):
            lines.append(f"RESULT of {m.get('name') or m.get('tool_call_id') or 'tool'}:\n{_text(m.get('content'))}")
    return system, "\n\n".join(lines)


def _clean(node: Any, defs: dict) -> Any:
    """A JSON schema with `$ref`s inlined and keys the structured-output checker rejects dropped."""
    if isinstance(node, dict):
        if "$ref" in node:
            return _clean(defs.get(node["$ref"].split("/")[-1], {}), defs)
        return {k: _clean(v, defs) for k, v in node.items()
                if k not in ("title", "default", "$defs", "definitions", "examples")}
    if isinstance(node, list):
        return [_clean(v, defs) for v in node]
    return node


def inline(schema: dict | None) -> dict:
    """Inline a schema's definitions."""
    schema = json.loads(json.dumps(schema or {"type": "object", "properties": {}}))
    defs = {**schema.get("$defs", {}), **schema.get("definitions", {})}
    out = _clean(schema, defs)
    if out.get("type") is None and "properties" in out:
        out["type"] = "object"
    return out


def tool_schema(tools: list[dict], required: bool, only: str | None) -> tuple[dict, str]:
    """The reply shape for a turn with tools offered, and the guide appended to the system prompt."""
    shapes, names = [], []
    for t in tools:
        fn = t.get("function") or t
        name = fn["name"]
        if only and name != only:
            continue
        names.append(name)
        shapes.append({"type": "object",
                       "properties": {"tool": {"const": name}, "args": inline(fn.get("parameters"))},
                       "required": ["tool", "args"]})
    calls: dict = {"type": "array", "items": {"anyOf": shapes}}
    if required or only:
        calls["minItems"] = 1
    schema = {"type": "object", "properties": {"text": {"type": "string"}, "calls": calls},
              "required": ["text", "calls"]}
    guide = (
        "\n\nHOW ACTIONS WORK HERE: you have no native tools in this setup. Every tool named "
        f"above or below ({', '.join(names)}) is requested by listing it in the `calls` field "
        "of your JSON reply; the system runs it and returns its result in the next turn's "
        "transcript. So all of these tools ARE available: never say they are not. "
        'Reply as {"text": words to the user, "calls": [{"tool": name, "args": {...}}]}.'
        + (" You must request at least one tool." if (required or only) else
           " When you are finished, reply with an empty list of calls and your final answer in text.")
    )
    return schema, guide


def complete(body: dict, default_model: str) -> dict:
    """Answer one chat-completions request body."""
    model = os.environ.get("PROXY_FORCE_MODEL") or default_model
    tag = os.environ.get("PROXY_TAG", "")
    system, transcript = render(body.get("messages") or [])
    tools = body.get("tools") or [{"type": "function", "function": f} for f in body.get("functions") or []]
    choice = body.get("tool_choice")
    rf = body.get("response_format") or {}
    msg: dict = {"role": "assistant", "content": None}
    finish = "stop"
    if tools and choice != "none":
        only = choice.get("function", {}).get("name") if isinstance(choice, dict) else None
        schema, guide = tool_schema(tools, choice in ("required", "any"), only)
        result = _call(model, system + guide, schema, (transcript or "Begin.") + "\n\nChoose your next tool calls.", tag)
        out = result["structured_output"]
        calls = [{"id": f"call_{uuid.uuid4().hex[:20]}", "type": "function",
                  "function": {"name": c["tool"], "arguments": json.dumps(c.get("args") or {})}}
                 for c in out.get("calls") or []]
        msg["content"] = out.get("text") or ("" if calls else " ")
        if calls:
            msg["tool_calls"] = calls
            finish = "tool_calls"
    elif rf.get("type") == "json_schema":
        schema = inline((rf.get("json_schema") or {}).get("schema"))
        result = _call(model, system, schema, transcript or "Answer now.", tag)
        msg["content"] = json.dumps(result["structured_output"])
    elif rf.get("type") == "json_object":
        result = _call(model, system + "\n\nReply with one JSON object only.", {"type": "object"}, transcript or "Answer now.", tag)
        msg["content"] = json.dumps(result["structured_output"])
    else:
        result = _call(model, system, None, transcript or "Answer now.", tag)
        msg["content"] = str(result["result"])
    u = result.get("usage") or {}
    prompt_tokens = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return {"id": f"chatcmpl-{uuid.uuid4().hex}", "object": "chat.completion", "created": int(time.time()),
            "model": body.get("model") or model,
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": u.get("output_tokens") or 0,
                      "total_tokens": prompt_tokens + (u.get("output_tokens") or 0)}}


def stream_chunks(resp: dict) -> list[dict]:
    """The same answer as a short stream of chat.completion.chunk objects."""
    msg = resp["choices"][0]["message"]
    base = {"id": resp["id"], "object": "chat.completion.chunk", "created": resp["created"], "model": resp["model"]}
    delta: dict = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("tool_calls"):
        delta["tool_calls"] = [{"index": i, **c} for i, c in enumerate(msg["tool_calls"])]
    return [{**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": resp["choices"][0]["finish_reason"]}],
             "usage": resp["usage"]}]


class Handler(BaseHTTPRequestHandler):
    """Serves POST /v1/chat/completions and GET /v1/models."""

    model = "claude-haiku-4-5"

    def log_message(self, *args: Any) -> None:
        """Quiet."""

    def _send(self, code: int, obj: dict) -> None:
        """Send one JSON response."""
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        """List the one model."""
        self._send(200, {"object": "list", "data": [{"id": self.model, "object": "model"}]})

    def do_POST(self) -> None:
        """Answer a chat completion, streamed if asked."""
        if not self.path.rstrip("/").endswith("chat/completions"):
            self._send(404, {"error": {"message": f"unsupported path {self.path}"}})
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        try:
            resp = complete(body, self.model)
        except Exception as error:  # surfaced to the agent as an API error, as a real outage would be
            self._send(500, {"error": {"message": str(error)[:500], "type": "proxy_error"}})
            return
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for chunk in stream_chunks(resp):
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            self._send(200, resp)


def main() -> None:
    """Start the server."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--model", default="claude-haiku-4-5")
    a = ap.parse_args()
    Handler.model = a.model
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
