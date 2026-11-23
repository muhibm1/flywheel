"""Smoke-check the running endpoint before trusting it: python proxy_check.py [base_url]."""

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
TOOL = {"type": "function", "function": {"name": "get_weather", "description": "Weather for a city.",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}


def post(body: dict, path: str = "/v1/chat/completions") -> tuple[int, bytes]:
    """POST a body; status and raw bytes."""
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def msg(raw: bytes) -> tuple[dict, str]:
    """Message and finish reason of a non-streamed reply."""
    c = json.loads(raw)["choices"][0]
    return c["message"], c["finish_reason"]


CHECKS = []


def check(name):
    """Register a check."""
    def wrap(f):
        CHECKS.append((name, f))
        return f
    return wrap


@check("no system message, plain text")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "Reply with the word ok."}]})
    return s == 200 and "ok" in (msg(raw)[0]["content"] or "").lower()


@check("system message, plain text")
def _():
    s, raw = post({"messages": [{"role": "system", "content": "Answer in one word."}, {"role": "user", "content": "Colour of the sky?"}]})
    return s == 200 and bool(msg(raw)[0]["content"])


@check("tools, no system message, tool called")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "What is the weather in Paris? Use the tool."}], "tools": [TOOL]})
    m, f = msg(raw)
    return s == 200 and f == "tool_calls" and m["tool_calls"][0]["function"]["name"] == "get_weather"


@check("tool result turn answers")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "What is the weather in Paris?"},
                                {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "get_weather", "arguments": "{\"city\": \"Paris\"}"}}]},
                                {"role": "tool", "tool_call_id": "c1", "content": "17C and sunny"}], "tools": [TOOL]})
    m, f = msg(raw)
    return s == 200 and "17" in (m.get("content") or "")


@check("tool_choice required")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "Hello"}], "tools": [TOOL], "tool_choice": "required"})
    return s == 200 and bool(msg(raw)[0].get("tool_calls"))


@check("json_schema response format")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "Give the number 7."}], "response_format": {"type": "json_schema", "json_schema": {"name": "n", "schema": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}}}})
    return s == 200 and json.loads(msg(raw)[0]["content"]).get("n") == 7


@check("max_tokens truncates with length")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "Write 300 words about rivers."}], "max_tokens": 20})
    return s == 200 and msg(raw)[1] == "length"


@check("stop sequence applied")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "Count from 1 to 10 separated by spaces."}], "stop": ["5"]})
    return s == 200 and "6" not in (msg(raw)[0]["content"] or "")


@check("stream ends with [DONE]")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "Say hi."}], "stream": True})
    return s == 200 and raw.strip().endswith(b"data: [DONE]")


@check("fault unknown_tool fires once")
def _():
    s, raw = post({"messages": [{"role": "user", "content": "Weather in Paris?"}], "tools": [TOOL]}, "/fault/unknown_tool/v1/chat/completions")
    return s == 200 and msg(raw)[0]["tool_calls"][0]["function"]["name"] == "no_such_tool_xyz"


ok = True
for name, f in CHECKS:
    try:
        r = f()
    except Exception as e:  # report and continue
        r = False
        name += f" ({type(e).__name__}: {str(e)[:120]})"
    ok &= bool(r)
    print("PASS" if r else "FAIL", name, flush=True)
sys.exit(0 if ok else 1)
