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
import re
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
# Host-session context that must not reach the model under test (memory, extra CLAUDE.md files).
CONTEXT_VARIABLES = ("CLAUDE_MEMORY_STORES", "CLAUDE_COWORK_MEMORY_PATH_OVERRIDE", "CLAUDE_ADDITIONAL_DIRECTORIES",
                     "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD", "CLAUDE_CODE_PROJECTS_SESSION",
                     "CLAUDE_CODE_SKILL_PROPOSALS", "CLAUDE_CODE_COORDINATOR_EXTRA_TOOLS", "CLAUDE_CODE_CHILD_NOTES_DIR",
                     "CLAUDE_CODE_SILENT_TURN_REMINDER", "CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION",
                     "CLAUDE_CODE_USER_EMAIL")
TIMEOUT = 600
ATTEMPTS = 3
LIMIT_WAIT = 600
MAX_PARALLEL = int(os.environ.get("PROXY_PARALLEL", "4"))
USAGE_LOG = Path(os.environ.get("PROXY_USAGE_LOG", "proxy-usage.jsonl"))
LOOSE = os.environ.get("PROXY_LOOSE", "1") == "1"  # version 2 default; 0 restores version 1
REFUSAL_RETRIES = int(os.environ.get("PROXY_REFUSAL_RETRIES", "2"))
REFUSAL = re.compile(r"(not|n't|no longer|un)\s*(currently\s*)?(available|accessible|access to)|no such tool"
                     r"|(don't|do not|cannot|can't) (have|use|call|access)\b[^.]{0,40}\btool", re.I)
_slots = threading.BoundedSemaphore(MAX_PARALLEL)
_log_lock = threading.Lock()


class CallFailed(RuntimeError):
    """A headless call failed after every attempt."""


def _run(args: list[str], prompt: str) -> dict:
    """One headless call in an empty folder; its parsed JSON result."""
    exe = shutil.which("claude")
    if not exe:
        raise CallFailed("the claude command is not installed")
    env = {k: v for k, v in os.environ.items() if k not in KEY_VARIABLES and k not in CONTEXT_VARIABLES}
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"  # v2.3: the model under test sees no host memory
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
            "--setting-sources", "", "--no-session-persistence", "--system-prompt", system if (system or "").strip() else "You are Claude, an AI assistant."]
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
    shapes, names, specs = [], [], []
    for t in tools:
        fn = t.get("function") or t
        name = fn["name"]
        if only and name != only:
            continue
        names.append(name)
        specs.append({"name": name, "description": fn.get("description", ""),
                      "parameters": inline(fn.get("parameters"))})
        shapes.append({"type": "object",
                       "properties": {"tool": {"const": name}, "args": inline(fn.get("parameters"))},
                       "required": ["tool", "args"]})
    if LOOSE:
        # Closer to a real API: each tool keeps its name and argument names, but required
        # arguments and argument types are not enforced, so a model can call a tool wrongly.
        loose = []
        for sh in shapes:
            args = json.loads(json.dumps(sh["properties"]["args"]))
            args.pop("required", None)
            args.pop("additionalProperties", None)
            for v in (args.get("properties") or {}).values():
                if isinstance(v, dict):
                    for k in ("type", "enum", "format", "minimum", "maximum", "pattern"):
                        v.pop(k, None)
            loose.append({**sh, "properties": {**sh["properties"], "args": args}})
        calls: dict = {"type": "array", "items": {"anyOf": loose}}
    else:
        calls = {"type": "array", "items": {"anyOf": shapes}}
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
    if LOOSE:
        guide += ("\n\nTool reference (arguments and their meaning):\n" + json.dumps(specs, indent=1)
                  + "\nDo not try to call these tools any other way: list them in `calls`.")
    return schema, guide


def _limit(body: dict) -> int | None:
    """The request's output-token limit, if any."""
    for k in ("max_completion_tokens", "max_tokens"):
        if isinstance(body.get(k), int) and body[k] > 0:
            return body[k]
    return None


def _truncate(msg: dict, limit: int, used: int) -> bool:
    """Cut an over-long answer to about `limit` tokens, as a real API does; True when cut."""
    if used <= limit:
        return False
    keep = max(1, limit * 4)  # about four characters per token
    if msg.get("tool_calls"):
        budget = keep - len(msg.get("content") or "")
        for c in msg["tool_calls"]:
            args = c["function"]["arguments"]
            c["function"]["arguments"] = args[: max(0, budget)]
            budget -= len(args)
    if msg.get("content"):
        msg["content"] = msg["content"][:keep]
    return True


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
        # The headless model sometimes answers "that tool is not available" because its own
        # session has no tools; a real API never does this, so ask again (version 2.1).
        for _ in range(REFUSAL_RETRIES):
            if out.get("calls") or not REFUSAL.search(str(out.get("text") or "")):
                break
            with _log_lock, USAGE_LOG.open("a") as f:
                f.write(json.dumps({"t": time.time(), "tag": tag, "refusal_retry": True}) + "\n")
            result = _call(model, system + guide, schema,
                           (transcript or "Begin.") + "\n\nChoose your next tool calls.", tag)
            out = result["structured_output"]
        if not out.get("calls"):
            with _log_lock, Path(os.environ.get("PROXY_NOCALL_LOG", "/tmp/rr-nocall.jsonl")).open("a") as f:
                f.write(json.dumps({"t": time.time(), "choice": str(choice), "text": str(out.get("text"))[:400]}) + "\n")
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
    stops = body.get("stop")
    stops = [stops] if isinstance(stops, str) else [s for s in stops or [] if s]
    if LOOSE and stops and isinstance(msg.get("content"), str):
        # A real API stops generating at the first stop sequence and leaves it out.
        cut = min((msg["content"].find(s) for s in stops if s in msg["content"]), default=-1)
        if cut >= 0:
            msg["content"] = msg["content"][:cut]
    limit = _limit(body)
    if LOOSE and limit:
        # Thinking tokens are not part of the visible answer; estimate the answer's own size.
        visible = len(json.dumps(msg.get("tool_calls") or "")) + len(msg.get("content") or "")
        if _truncate(msg, limit, visible // 4):
            finish = "length"
    prompt_tokens = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return {"id": f"chatcmpl-{uuid.uuid4().hex}", "object": "chat.completion", "created": int(time.time()),
            "model": body.get("model") or model,
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": u.get("output_tokens") or 0,
                      "total_tokens": prompt_tokens + (u.get("output_tokens") or 0)}}


FAULTS = ("bad_json_args", "unknown_tool", "missing_arg", "truncated", "empty", "call_as_text")


def fault_reply(name: str, body: dict, model: str) -> dict | None:
    """Arm 5: one scripted bad reply on a run's first tool turn, or None to answer normally.

    Reached through base_url http://127.0.0.1:8765/fault/<name>/v1. The fault fires only while
    the conversation has no assistant or tool message yet, so it happens exactly once per run
    and identically on base and head; every later turn is answered by the model as usual.
    """
    msgs = body.get("messages") or []
    if name not in FAULTS or any(m.get("role") in ("assistant", "tool", "function") for m in msgs):
        return None
    tools = body.get("tools") or [{"type": "function", "function": f} for f in body.get("functions") or []]
    if not tools:
        return None
    fn = tools[0].get("function") or tools[0]
    props = list(((fn.get("parameters") or {}).get("properties") or {}).keys())
    call = {"id": f"call_{uuid.uuid4().hex[:20]}", "type": "function",
            "function": {"name": fn["name"], "arguments": json.dumps({p: "x" for p in props})}}
    msg: dict = {"role": "assistant", "content": ""}
    finish = "tool_calls"
    if name == "bad_json_args":
        call["function"]["arguments"] = '{"' + (props[0] if props else "arg") + '": "x",'
        msg["tool_calls"] = [call]
    elif name == "unknown_tool":
        call["function"]["name"] = "no_such_tool_xyz"
        msg["tool_calls"] = [call]
    elif name == "missing_arg":
        call["function"]["arguments"] = "{}"
        msg["tool_calls"] = [call]
    elif name == "truncated":
        msg["content"], finish = "I will start by calling the", "length"
    elif name == "empty":
        msg["content"], finish = "", "stop"
    elif name == "call_as_text":
        msg["content"], finish = json.dumps({"name": fn["name"], "arguments": json.loads(call["function"]["arguments"])}), "stop"
    with _log_lock, USAGE_LOG.open("a") as f:
        f.write(json.dumps({"t": time.time(), "fault": name}) + "\n")
    return {"id": f"chatcmpl-{uuid.uuid4().hex}", "object": "chat.completion", "created": int(time.time()),
            "model": body.get("model") or model, "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


def stream_chunks(resp: dict) -> list[dict]:
    """The same answer as a short stream of chat.completion.chunk objects."""
    msg = resp["choices"][0]["message"]
    base = {"id": resp["id"], "object": "chat.completion.chunk", "created": resp["created"], "model": resp["model"]}
    chunks = [{**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": msg.get("content") or ""},
                                    "finish_reason": None}]}]
    # Text first, then each tool call in its own chunk, the order a real API streams them in.
    for i, c in enumerate(msg.get("tool_calls") or []):
        chunks.append({**base, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": i, **c}]},
                                            "finish_reason": None}]})
    return chunks + [
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
        parts = self.path.strip("/").split("/")
        fault = parts[1] if len(parts) > 2 and parts[0] == "fault" else None
        try:
            resp = (fault and fault_reply(fault, body, self.model)) or complete(body, self.model)
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
