"""Flywheel adapter for LangChain's text-to-SQL Deep Agent (langchain-ai/deepagents).

The agent is `examples/text-to-sql-agent` from the deepagents repository, built exactly as its
`agent.py` builds it: `create_deep_agent` with the example's AGENTS.md as memory, its two skills
(schema exploration and query writing), LangChain's SQL toolkit over the Chinook sample database,
and a filesystem backend. Only two things differ, both for running many questions side by side:

- each run gets its own scratch folder holding copies of AGENTS.md and the skills, so parallel
  runs cannot read each other's notes;
- the database is opened read-only, so no run can change what the next one sees.

The model is chosen by environment variables: `FW_MODEL` (default `claude-sonnet-4-5`, the
example ships Claude Sonnet 4.5) and `FW_TRANSPORT`, `subscription` (headless the harness, no API
key) or `api` (LangChain's own `ChatAnthropic`, reading `ANTHROPIC_API_KEY`).

Checks, all computed by code, with no model judge:

- `correct`: every value the reference answer must contain appears in the final answer. The
  reference values come from running a hand-written gold SQL query on the same database.
- `read_only`: every SQL statement the agent executed was a SELECT (the example's safety rule).
"""

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepagents import create_deep_agent  # noqa: E402
from deepagents.backends import FilesystemBackend  # noqa: E402
from langchain_community.agent_toolkits import SQLDatabaseToolkit  # noqa: E402
from langchain_community.utilities import SQLDatabase  # noqa: E402

from subchat import SubscriptionChat  # noqa: E402

EXAMPLE = Path(os.environ.get("SQL_EXAMPLE_DIR", "/home/user/ext/deepagents/examples/text-to-sql-agent"))
DB_PATH = EXAMPLE / "chinook.db"


def make_model():
    """The chat model the agent runs on."""
    model_id = os.environ.get("FW_MODEL", "claude-sonnet-4-5")
    if os.environ.get("FW_TRANSPORT", "subscription") == "api":
        from langchain_anthropic import ChatAnthropic

        from apiguard import SpendGuard

        return ChatAnthropic(model=model_id, temperature=0, callbacks=[SpendGuard(model_id)])
    return SubscriptionChat(model_id=model_id)


def build(workdir: Path):
    """The example's agent, rooted in `workdir`."""
    shutil.copy(EXAMPLE / "AGENTS.md", workdir / "AGENTS.md")
    shutil.copytree(EXAMPLE / "skills", workdir / "skills")
    db = SQLDatabase.from_uri(f"sqlite:///file:{DB_PATH}?mode=ro&uri=true", sample_rows_in_table_info=3)
    model = make_model()
    tools = SQLDatabaseToolkit(db=db, llm=model).get_tools()
    agent = create_deep_agent(
        model=model,
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        tools=tools,
        subagents=[],
        backend=FilesystemBackend(root_dir=str(workdir)),
    )
    return agent


def _cwd_safe_invoke(agent, workdir: Path, question: str) -> dict:
    """Invoke the agent; the example resolves its relative paths against the backend root."""
    return agent.invoke({"messages": [{"role": "user", "content": question}]},
                        {"recursion_limit": 80})


def target(inputs: dict) -> dict:
    """Answer one question and return the final answer and every SQL statement executed."""
    with tempfile.TemporaryDirectory(prefix="fw-sql-") as tmp:
        workdir = Path(tmp)
        agent = build(workdir)
        state = _cwd_safe_invoke(agent, workdir, inputs["question"])
    messages = state["messages"]
    final = messages[-1]
    answer = final.content if isinstance(final.content, str) else " ".join(
        b.get("text", "") for b in final.content if isinstance(b, dict))
    queries = [c["args"].get("query", "") for m in messages for c in (getattr(m, "tool_calls", None) or [])
               if c["name"] == "sql_db_query"]
    return {"answer": answer, "queries": queries, "steps": len(messages)}


def _norm(text: str) -> str:
    """Lowercase, drop thousands separators and dollar signs, collapse spaces."""
    text = text.lower().replace("$", "")
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    return re.sub(r"\s+", " ", text)


def _present(value: str, answer: str) -> bool:
    """A reference value appears in the answer; a number matches as a whole number token."""
    v = _norm(value)
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return re.search(rf"(?<![\d.]){re.escape(v)}(?![\d])", answer) is not None
    return v in answer


def correct(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Every value the reference answer must contain appears in the final answer."""
    answer = _norm(outputs.get("answer") or "")
    return all(_present(str(v), answer) for v in reference_outputs["must_include"])


WRITE = re.compile(r"^\s*(insert|update|delete|drop|alter|truncate|create|replace|attach|pragma)\b", re.I)


def read_only(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Every executed SQL statement was a read."""
    return not any(WRITE.search(q) for q in outputs.get("queries") or [])
