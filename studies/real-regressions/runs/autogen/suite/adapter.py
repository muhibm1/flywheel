"""Flywheel adapter for AutoGen AgentChat (autogen-agentchat + autogen-ext[openai]).

`target(inputs)` builds an AgentChat agent or team the way the README and tutorials do, runs one
task against the local OpenAI-compatible endpoint, and returns what the checks need. Every run
gets its own temp folder; all tools are local and offline.

inputs:
  scenario: which setup to build (see SCENARIOS)
  task:     the task text given to the agent/team
outputs:
  final_text:  last substantive text message (TERMINATE stripped)
  texts:       every text-like message content, in order
  sources:     every message's source, in order
  tool_calls:  [{"name", "arguments"}] for every tool call requested
  files:       {name: content} of files left in the run's work folder
  stop_reason: the TaskResult stop reason
  parsed_json: the final text parsed as JSON, when it parses
"""

import asyncio
import contextvars
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import (
    HandoffTermination,
    MaxMessageTermination,
    TextMentionTermination,
)
from autogen_agentchat.teams import RoundRobinGroupChat, Swarm
from autogen_core.models import ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient

BASE_URL = os.environ.get("AUTOGEN_SUITE_BASE_URL", "http://127.0.0.1:8765/v1")
MODEL = os.environ.get("AUTOGEN_SUITE_MODEL", "claude-haiku-4-5")
RUN_TIMEOUT_S = 300
MAX_MESSAGES = 20

# Every local tool records its own calls here, so the checks see tool use even when it happened
# inside an inner team whose messages are not part of the returned TaskResult.
_TOOL_LOG: contextvars.ContextVar[list] = contextvars.ContextVar("tool_log")


def _log(name: str) -> None:
    """Record that a local tool ran."""
    try:
        _TOOL_LOG.get().append(name)
    except LookupError:
        pass


def make_client() -> OpenAIChatCompletionClient:
    """An OpenAI-compatible chat-completions client pointed at the local endpoint."""
    return OpenAIChatCompletionClient(
        model=MODEL,
        base_url=BASE_URL,
        api_key="sk-local",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "structured_output": True,
            "family": ModelFamily.UNKNOWN,
        },
    )


# ---------------------------------------------------------------- scenarios


async def sc_hello(client, work: Path, task: str):
    """The README hello world: a bare AssistantAgent."""
    agent = AssistantAgent("assistant", client)
    return await agent.run(task=task)


async def sc_weather(client, work: Path, task: str):
    """One tool, reflect_on_tool_use=True (tutorial pattern)."""
    data = {"paris": "17 degrees Celsius and cloudy", "tokyo": "24 degrees Celsius and sunny"}

    async def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        _log("get_weather")
        return data.get(city.strip().lower(), "no data for that city")

    agent = AssistantAgent(
        "weather_agent",
        client,
        tools=[get_weather],
        reflect_on_tool_use=True,
        system_message="You are a helpful assistant. Use the get_weather tool to answer weather questions.",
    )
    return await agent.run(task=task)


async def sc_math_team(client, work: Path, task: str):
    """Multi-step tool use: a single agent looping in a RoundRobinGroupChat until TERMINATE."""

    async def add(a: float, b: float) -> float:
        """Add two numbers."""
        _log("add")
        return a + b

    async def multiply(a: float, b: float) -> float:
        """Multiply two numbers."""
        _log("multiply")
        return a * b

    agent = AssistantAgent(
        "calculator",
        client,
        tools=[add, multiply],
        system_message=(
            "You are a careful calculator. Use the add and multiply tools for every arithmetic step, "
            "one tool call at a time. When you have the final result, state it and then write TERMINATE."
        ),
    )
    team = RoundRobinGroupChat(
        [agent],
        termination_condition=TextMentionTermination("TERMINATE") | MaxMessageTermination(MAX_MESSAGES),
    )
    return await team.run(task=task)


async def sc_files(client, work: Path, task: str):
    """File-writing tools confined to the run's work folder."""
    root = work / "files"
    root.mkdir()

    async def write_file(filename: str, content: str) -> str:
        """Write text content to a file in the workspace (overwrites)."""
        _log("write_file")
        path = (root / filename).resolve()
        if root.resolve() not in path.parents:
            return "error: path outside workspace"
        path.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} characters to {filename}"

    async def list_files() -> str:
        """List the files in the workspace."""
        _log("list_files")
        return ", ".join(sorted(p.name for p in root.iterdir())) or "(empty)"

    agent = AssistantAgent(
        "file_agent",
        client,
        tools=[write_file, list_files],
        reflect_on_tool_use=True,
        system_message="You manage files in a workspace using your tools.",
    )
    return await agent.run(task=task)


def make_shop_db(path: Path) -> None:
    """A small sqlite database of orders."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, amount INTEGER, status TEXT)")
    con.executemany(
        "INSERT INTO orders (customer, amount, status) VALUES (?, ?, ?)",
        [
            ("alice", 40, "shipped"),
            ("alice", 55, "shipped"),
            ("alice", 25, "shipped"),
            ("alice", 300, "cancelled"),
            ("bob", 70, "shipped"),
            ("bob", 15, "pending"),
            ("carol", 99, "shipped"),
        ],
    )
    con.commit()
    con.close()


async def sc_sql(client, work: Path, task: str):
    """A read-only SQL tool over a local sqlite db, inside a tool loop."""
    db = work / "shop.db"
    make_shop_db(db)

    async def run_sql(query: str) -> str:
        """Run a read-only SQL query against the shop database (table: orders(id, customer, amount, status))."""
        _log("run_sql")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = con.execute(query).fetchall()
            return json.dumps(rows)
        except sqlite3.Error as error:
            return f"sql error: {error}"
        finally:
            con.close()

    agent = AssistantAgent(
        "analyst",
        client,
        tools=[run_sql],
        system_message=(
            "You are a data analyst. Answer questions by querying the database with run_sql. "
            "When you have the answer, state it and then write TERMINATE."
        ),
    )
    team = RoundRobinGroupChat(
        [agent],
        termination_condition=TextMentionTermination("TERMINATE") | MaxMessageTermination(MAX_MESSAGES),
    )
    return await team.run(task=task)


async def sc_json(client, work: Path, task: str):
    """Structured output by instruction: the agent replies with one JSON object."""
    agent = AssistantAgent(
        "extractor",
        client,
        system_message=(
            "You extract structured data. Reply with a single JSON object only, no prose and no code fences."
        ),
    )
    return await agent.run(task=task)


async def sc_memory(client, work: Path, task: str):
    """ListMemory injected into the agent's context."""
    from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType

    memory = ListMemory()
    await memory.add(MemoryContent(content="The user's favourite colour is teal.", mime_type=MemoryMimeType.TEXT))
    await memory.add(MemoryContent(content="The user lives in Oslo.", mime_type=MemoryMimeType.TEXT))
    agent = AssistantAgent("assistant", client, memory=[memory])
    return await agent.run(task=task)


async def sc_swarm(client, work: Path, task: str):
    """Swarm with handoffs: triage hands off to billing, which uses a tool."""
    invoices = {"INV-7731": "amount due 318.40 USD, due date 2026-12-01"}

    async def lookup_invoice(invoice_id: str) -> str:
        """Look up an invoice by its id."""
        _log("lookup_invoice")
        return invoices.get(invoice_id.strip().upper(), "invoice not found")

    triage = AssistantAgent(
        "triage",
        client,
        handoffs=["billing"],
        system_message=(
            "You are a triage agent. You cannot look anything up yourself. "
            "Hand off any invoice or payment question to the billing agent."
        ),
    )
    billing = AssistantAgent(
        "billing",
        client,
        tools=[lookup_invoice],
        reflect_on_tool_use=True,
        system_message=(
            "You are a billing agent. Use lookup_invoice to answer invoice questions. "
            "After answering, write TERMINATE."
        ),
    )
    team = Swarm(
        [triage, billing],
        termination_condition=TextMentionTermination("TERMINATE")
        | HandoffTermination(target="user")
        | MaxMessageTermination(MAX_MESSAGES),
    )
    return await team.run(task=task)


WEATHER = {"paris": "17 degrees Celsius and cloudy", "tokyo": "24 degrees Celsius and sunny"}
INVOICES = {"INV-7731": "amount due 318.40 USD, due date 2026-12-01"}


async def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    _log("get_weather")
    return WEATHER.get(city.strip().lower(), "no data for that city")


async def lookup_invoice(invoice_id: str) -> str:
    """Look up an invoice by its id."""
    _log("lookup_invoice")
    return INVOICES.get(invoice_id.strip().upper(), "invoice not found")


async def create_ticket(summary: str) -> str:
    """Create a support ticket with a one-line summary and return its ticket number."""
    _log("create_ticket")
    return "ticket T-5512 created"


# --- AssistantAgent variations: reflection, streaming, summary format, handoff with tools


async def sc_weather_styled(client, work: Path, task: str):
    """Tool + reflection, with a system message that sets the answer format."""
    agent = AssistantAgent(
        "weather_agent",
        client,
        tools=[get_weather],
        reflect_on_tool_use=True,
        system_message=(
            "You are a weather assistant. Use the get_weather tool. "
            "Every answer you give must begin with the exact prefix 'FORECAST:'."
        ),
    )
    return await agent.run(task=task)


async def sc_weather_stream(client, work: Path, task: str):
    """Tool + reflection with model_client_stream=True."""
    agent = AssistantAgent(
        "weather_agent",
        client,
        tools=[get_weather],
        reflect_on_tool_use=True,
        model_client_stream=True,
        system_message="You are a helpful assistant. Use the get_weather tool to answer weather questions.",
    )
    return await agent.run(task=task)


async def sc_two_turn(client, work: Path, task: str):
    """The same agent across two run() calls: the first turn's content must stay in its context.
    `task` is two turns separated by a line with only '---'."""
    first, second = [part.strip() for part in task.split("\n---\n", 1)]

    async def save_note(text: str) -> str:
        """Save a short note for later."""
        _log("save_note")
        return "note saved"

    agent = AssistantAgent(
        "assistant",
        client,
        tools=[save_note],
        reflect_on_tool_use=True,
        system_message="You are a helpful assistant with a save_note tool.",
    )
    await agent.run(task=first)
    return await agent.run(task=second)


async def sc_weather_summary(client, work: Path, task: str):
    """Tool use without reflection: the reply is the tool-call summary in a custom format."""
    agent = AssistantAgent(
        "weather_agent",
        client,
        tools=[get_weather],
        reflect_on_tool_use=False,
        tool_call_summary_format="{tool_name} -> {result}",
        system_message="You are a helpful assistant. Use the get_weather tool to answer weather questions.",
    )
    return await agent.run(task=task)


async def sc_swarm_tool_handoff(client, work: Path, task: str):
    """Swarm where the first agent must use its own tool before handing off."""
    triage = AssistantAgent(
        "triage",
        client,
        tools=[create_ticket],
        handoffs=["billing"],
        system_message=(
            "You are a triage agent. For every customer request, first create a support ticket with "
            "create_ticket, then hand off invoice or payment questions to the billing agent. "
            "You cannot look up invoices yourself."
        ),
    )
    billing = AssistantAgent(
        "billing",
        client,
        tools=[lookup_invoice],
        reflect_on_tool_use=True,
        system_message=(
            "You are a billing agent. Use lookup_invoice to answer invoice questions. "
            "After answering, write TERMINATE."
        ),
    )
    team = Swarm(
        [triage, billing],
        termination_condition=TextMentionTermination("TERMINATE")
        | HandoffTermination(target="user")
        | MaxMessageTermination(MAX_MESSAGES),
    )
    return await team.run(task=task)


async def sc_memory_stream(client, work: Path, task: str):
    """ListMemory with a streaming model client."""
    from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType

    memory = ListMemory()
    await memory.add(MemoryContent(content="The user's favourite colour is teal.", mime_type=MemoryMimeType.TEXT))
    await memory.add(MemoryContent(content="The user lives in Oslo.", mime_type=MemoryMimeType.TEXT))
    agent = AssistantAgent("assistant", client, memory=[memory], model_client_stream=True)
    return await agent.run(task=task)


# --- SocietyOfMindAgent


def writer_editor_team(client) -> RoundRobinGroupChat:
    """The docstring's inner team: a writer and an editor who approves."""
    writer = AssistantAgent("writer", client, system_message="You are a writer, write well.")
    editor = AssistantAgent(
        "editor",
        client,
        system_message=(
            "You are an editor, provide critical feedback. "
            "Respond with 'APPROVE' if the text addresses all feedbacks."
        ),
    )
    return RoundRobinGroupChat(
        [writer, editor],
        termination_condition=TextMentionTermination("APPROVE") | MaxMessageTermination(8),
    )


async def sc_soma_basic(client, work: Path, task: str):
    """A SocietyOfMindAgent wrapping a writer/editor team, run directly."""
    from autogen_agentchat.agents import SocietyOfMindAgent

    soma = SocietyOfMindAgent("society_of_mind", team=writer_editor_team(client), model_client=client)
    return await soma.run(task=task)


async def sc_soma_outer(client, work: Path, task: str):
    """The docstring example: SocietyOfMindAgent then a translator in an outer round-robin team."""
    from autogen_agentchat.agents import SocietyOfMindAgent

    soma = SocietyOfMindAgent("society_of_mind", team=writer_editor_team(client), model_client=client)
    translator = AssistantAgent("translator", client, system_message="Translate the text to Spanish.")
    team = RoundRobinGroupChat([soma, translator], max_turns=2)
    return await team.run(task=task)


async def sc_soma_tool(client, work: Path, task: str):
    """A SocietyOfMindAgent whose inner team uses a tool to find the answer."""
    from autogen_agentchat.agents import SocietyOfMindAgent

    researcher = AssistantAgent(
        "researcher",
        client,
        tools=[lookup_invoice],
        reflect_on_tool_use=True,
        system_message=(
            "You answer billing questions using lookup_invoice. State the answer, then write TERMINATE."
        ),
    )
    inner = RoundRobinGroupChat(
        [researcher], termination_condition=TextMentionTermination("TERMINATE") | MaxMessageTermination(8)
    )
    soma = SocietyOfMindAgent("society_of_mind", team=inner, model_client=client)
    return await soma.run(task=task)


async def sc_soma_chain(client, work: Path, task: str):
    """An outer team where the SocietyOfMindAgent speaks twice, answering a critic in between."""
    from autogen_agentchat.agents import SocietyOfMindAgent

    soma = SocietyOfMindAgent("society_of_mind", team=writer_editor_team(client), model_client=client)
    critic = AssistantAgent(
        "critic",
        client,
        system_message="You are a reader. Give one short, concrete suggestion to improve the text you just read.",
    )
    team = RoundRobinGroupChat([soma, critic], max_turns=3)
    return await team.run(task=task)


async def sc_soma_prompt(client, work: Path, task: str):
    """A SocietyOfMindAgent with a custom response_prompt."""
    from autogen_agentchat.agents import SocietyOfMindAgent

    soma = SocietyOfMindAgent(
        "society_of_mind",
        team=writer_editor_team(client),
        model_client=client,
        response_prompt=(
            "Output a standalone response to the original request, without mentioning any of the "
            "intermediate discussion. End your response with a final line that reads exactly: END OF DRAFT"
        ),
    )
    return await soma.run(task=task)


async def sc_soma_continue(client, work: Path, task: str):
    """Run a SocietyOfMindAgent on a task, then call run() again with no new task to continue."""
    from autogen_agentchat.agents import SocietyOfMindAgent

    counter_a = AssistantAgent(
        "counter_a", client, system_message="You count with your partner. Reply with only the next number."
    )
    counter_b = AssistantAgent(
        "counter_b", client, system_message="You count with your partner. Reply with only the next number."
    )
    inner = RoundRobinGroupChat([counter_a, counter_b], termination_condition=MaxMessageTermination(4))
    soma = SocietyOfMindAgent("society_of_mind", team=inner, model_client=client)
    await soma.run(task=task)
    return await soma.run()


SCENARIOS = {
    "hello": sc_hello,
    "weather": sc_weather,
    "math_team": sc_math_team,
    "files": sc_files,
    "sql": sc_sql,
    "json": sc_json,
    "memory": sc_memory,
    "swarm": sc_swarm,
    "weather_styled": sc_weather_styled,
    "weather_stream": sc_weather_stream,
    "weather_summary": sc_weather_summary,
    "two_turn": sc_two_turn,
    "swarm_tool_handoff": sc_swarm_tool_handoff,
    "memory_stream": sc_memory_stream,
    "soma_basic": sc_soma_basic,
    "soma_outer": sc_soma_outer,
    "soma_tool": sc_soma_tool,
    "soma_continue": sc_soma_continue,
    "soma_chain": sc_soma_chain,
    "soma_prompt": sc_soma_prompt,
}


# ---------------------------------------------------------------- running


def message_text(message: Any) -> str | None:
    """A message's text, when it is text-like."""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    to_text = getattr(message, "to_text", None)
    if type(message).__name__ in ("StructuredMessage",) and callable(to_text):
        return to_text()
    return None


def collect(result: Any, work: Path) -> dict:
    """Turn a TaskResult into plain outputs."""
    texts: list[str] = []
    agent_texts: list[str] = []
    sources: list[str] = []
    types: list[str] = []
    tool_calls: list[dict] = []
    for message in result.messages:
        sources.append(str(getattr(message, "source", "")))
        types.append(type(message).__name__)
        if type(message).__name__ == "ToolCallRequestEvent":
            for call in message.content:
                tool_calls.append({"name": call.name, "arguments": call.arguments})
            continue
        text = message_text(message)
        if text is not None and type(message).__name__ not in ("ToolCallExecutionEvent",):
            texts.append(text)
            if getattr(message, "source", "") != "user":
                agent_texts.append(text)
    final_text = ""
    for text in reversed(agent_texts):
        stripped = text.replace("TERMINATE", "").strip()
        if stripped:
            final_text = stripped
            break
    parsed = None
    candidate = re.sub(r"^```(?:json)?|```$", "", final_text.strip(), flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(candidate)
    except (ValueError, TypeError):
        match = re.search(r"\{.*\}", final_text, flags=re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except ValueError:
                parsed = None
    files = {}
    for path in work.rglob("*"):
        if path.is_file() and path.suffix in (".txt", ".md", ".csv", ".json", ".py"):
            try:
                files[str(path.relative_to(work))] = path.read_text(encoding="utf-8")[:4000]
            except (OSError, UnicodeDecodeError):
                pass
    return {
        "final_text": final_text,
        "texts": texts,
        "sources": sources,
        "types": types,
        "tool_calls": tool_calls,
        "files": files,
        "stop_reason": str(result.stop_reason),
        "parsed_json": parsed,
    }


async def run_async(inputs: dict) -> dict:
    """Build the scenario, run it with a timeout, collect the outputs."""
    scenario = SCENARIOS[inputs["scenario"]]
    client = make_client()
    tool_log: list = []
    _TOOL_LOG.set(tool_log)
    with tempfile.TemporaryDirectory(prefix="autogen-flywheel-") as tmp:
        work = Path(tmp)
        try:
            result = await asyncio.wait_for(scenario(client, work, inputs["task"]), RUN_TIMEOUT_S)
            outputs = collect(result, work)
            outputs["tool_log"] = list(tool_log)
            return outputs
        finally:
            close = getattr(client, "close", None)
            if close is not None:
                await close()


def target(inputs: dict) -> dict:
    """Flywheel target: one task, one fresh event loop."""
    return asyncio.run(run_async(inputs))


# ---------------------------------------------------------------- checks
# Every check returns True when its reference key is absent, so one evaluator list fits every case.


def _norm(text: Any) -> str:
    """Lowercase, collapse whitespace, drop thousands separators."""
    return re.sub(r"\s+", " ", str(text)).lower().replace(",", "")


def check_answer(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Every `answer_contains` string appears in the final answer; no `answer_excludes` string does."""
    text = _norm(outputs.get("final_text", ""))
    wanted = reference_outputs.get("answer_contains", [])
    unwanted = reference_outputs.get("answer_excludes", [])
    return all(_norm(w) in text for w in wanted) and not any(_norm(u) in text for u in unwanted)


def check_tools(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Every tool in `tools_called` was called; no tool in `tools_not_called` was."""
    called = {call["name"] for call in outputs.get("tool_calls", [])} | set(outputs.get("tool_log", []))
    wanted = set(reference_outputs.get("tools_called", []))
    unwanted = set(reference_outputs.get("tools_not_called", []))
    return wanted <= called and not (unwanted & called)


def check_files(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Each file in `files` exists and contains every listed substring."""
    files = {Path(name).name: content for name, content in outputs.get("files", {}).items()}
    for name, needles in reference_outputs.get("files", {}).items():
        if name not in files:
            return False
        content = _norm(files[name])
        if not all(_norm(n) in content for n in needles):
            return False
    return True


def check_json(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """The parsed JSON answer has every field in `json`, compared case-insensitively."""
    expected = reference_outputs.get("json")
    if expected is None:
        return True
    parsed = outputs.get("parsed_json")
    if not isinstance(parsed, dict):
        return False
    for key, value in expected.items():
        if key not in parsed:
            return False
        got = parsed[key]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                if float(got) != float(value):
                    return False
            except (TypeError, ValueError):
                return False
        elif _norm(got).strip() != _norm(value).strip():
            return False
    return True


def check_flow(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Every agent in `speakers` spoke, every message type in `message_types` appeared,
    and `stop_reason_contains` (if set) is in the stop reason."""
    sources = set(outputs.get("sources", []))
    types = set(outputs.get("types", []))
    if not set(reference_outputs.get("speakers", [])) <= sources:
        return False
    if not set(reference_outputs.get("message_types", [])) <= types:
        return False
    needle = reference_outputs.get("stop_reason_contains")
    return needle is None or needle.lower() in outputs.get("stop_reason", "").lower()
