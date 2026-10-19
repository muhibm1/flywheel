"""Flywheel adapter for LangChain's email assistant (langchain-ai/agents-from-scratch).

The agent is the repository's `email_assistant` graph, unchanged: a triage router that sorts an
email into ignore, notify or respond, then a tool-calling response agent that drafts replies and
schedules meetings. It ships on OpenAI's gpt-4.1; here its two model objects are swapped for a
Claude model, chosen by environment variables:

- `FW_MODEL`: the Claude model id (default `claude-sonnet-4-5`).
- `FW_TRANSPORT`: `subscription` (headless the harness, no API key) or `api` (LangChain's own
  `ChatAnthropic`, native tool calling, reading `ANTHROPIC_API_KEY`).

The evaluators are LangChain's own checks from the repository's tests, in LangSmith's
`(inputs, outputs, reference_outputs)` signature:

- `triage`: the classification matches the labelled one (`eval/evaluate_triage.py`).
- `tool_calls`: every expected tool was called (`tests/test_response.py`); respond cases only.
- `criteria`: a model judge, given LangChain's judge prompt, says the reply meets the case's
  written criteria (`tests/test_response.py`); respond cases only. The judge is a fixed model on
  the subscription, the same for every run, so it never moves with the change under test.
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "unused")  # the module builds gpt-4.1 at import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from email_assistant import email_assistant as ea  # noqa: E402
from email_assistant.eval.prompts import RESPONSE_CRITERIA_SYSTEM_PROMPT  # noqa: E402
from email_assistant.schemas import RouterSchema  # noqa: E402
from email_assistant.utils import extract_tool_calls, format_messages_string  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from subchat import SubscriptionChat  # noqa: E402

JUDGE_MODEL = "claude-sonnet-4-6"


def make_model(model_id: str, transport: str):
    """The chat model the agent runs on."""
    if transport == "api":
        from langchain_anthropic import ChatAnthropic

        from apiguard import SpendGuard

        return ChatAnthropic(model=model_id, temperature=0, max_tokens=4096,
                             callbacks=[SpendGuard(model_id)])
    return SubscriptionChat(model_id=model_id)


def _install() -> None:
    """Swap the agent's model objects for the configured Claude model."""
    model = make_model(os.environ.get("FW_MODEL", "claude-sonnet-4-5"),
                       os.environ.get("FW_TRANSPORT", "subscription"))
    ea.llm_router = model.with_structured_output(RouterSchema)
    ea.llm_with_tools = model.bind_tools(ea.tools, tool_choice="any")


_install()


def target(inputs: dict) -> dict:
    """Run the email assistant on one email and return what the checks need."""
    state = ea.email_assistant.invoke({"email_input": inputs["email_input"]},
                                      {"recursion_limit": 30})
    messages = state.get("messages", [])
    out = {
        "classification": state.get("classification_decision"),
        "tool_calls": extract_tool_calls(messages),
        "transcript": format_messages_string(messages) if messages else "",
    }
    if os.environ.get("FW_OUTPUTS_LOG"):  # kept for auditing; Flywheel itself stores scores only
        with open(os.environ["FW_OUTPUTS_LOG"], "a") as f:
            f.write(json.dumps({"inputs": inputs, "outputs": out}) + "\n")
    return out


def triage(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """The email was sorted into the labelled category."""
    return outputs.get("classification") == reference_outputs["classification"]


def tool_calls(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Every expected tool was called; scored only for emails that need a reply."""
    if reference_outputs["classification"] != "respond":
        return {"key": "tool_calls", "score": None}
    called = set(outputs.get("tool_calls") or [])
    return {"key": "tool_calls", "score": all(c.lower() in called for c in reference_outputs["expected_calls"])}


class CriteriaGrade(BaseModel):
    """Score the response against specific criteria."""

    grade: bool = Field(description="Does the response meet the provided criteria?")
    justification: str = Field(description="The justification for the grade and score, including specific examples from the response.")


_judge = SubscriptionChat(model_id=JUDGE_MODEL).with_structured_output(CriteriaGrade)


def criteria(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """LangChain's model judge: the reply meets the case's criteria; respond cases only."""
    if reference_outputs["classification"] != "respond":
        return {"key": "criteria", "score": None}
    if outputs.get("classification") != "respond":
        return {"key": "criteria", "score": False}
    grade = _judge.invoke([
        {"role": "system", "content": RESPONSE_CRITERIA_SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"\n\n Response criteria: {reference_outputs['criteria']} \n\n Assistant's response: "
            f"\n\n {outputs['transcript']} \n\n Evaluate whether the assistant's response meets "
            "the criteria and provide justification for your evaluation.")},
    ])
    return {"key": "criteria", "score": bool(grade.grade)}


def traffic_reference(inputs: dict) -> dict | None:
    """The label written for a traffic email before it ran: the reviewer's answer for mining."""
    from traffic_emails import EMAILS

    for email in EMAILS:
        if email["email_input"] == inputs.get("email_input"):
            return {k: email[k] for k in ("classification", "expected_calls", "criteria")}
    return None
