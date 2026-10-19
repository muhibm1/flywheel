"""Send the traffic emails through the agent once each, like a day of real mail.

Each run is scored by the same evaluators the dataset uses, and written as an exported trace
(`flywheel mine --from-file` input): inputs, outputs, the scores as feedback, and the graph node
where it went wrong. LangSmith would normally hold these traces; its monthly trace allowance for
this account was used up when this ran, so the export stands in for it, with the same fields.

Usage: python traffic.py OUT.json
"""

import json
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import adapter
from traffic_emails import EMAILS


def one(email: dict) -> dict:
    """Run one email and return it as an exported trace."""
    inputs = {"email_input": email["email_input"]}
    ref = {k: email[k] for k in ("classification", "expected_calls", "criteria")}
    try:
        out = adapter.target(inputs)
    except Exception as error:
        return {
            "id": str(uuid.uuid4()),
            "name": "email_assistant",
            "inputs": inputs,
            "error": f"{type(error).__name__}: {error}"[:300],
            "nodes": [],
            "reference": ref,
        }
    feedback = {"triage": float(adapter.triage(inputs, out, ref))}
    for ev in (adapter.tool_calls, adapter.criteria):
        score = ev(inputs, out, ref)["score"]
        if score is not None:
            feedback[ev.__name__] = float(score)
    nodes = [{"name": "triage_router", "error": None if feedback["triage"] else "wrong category"}]
    if out["classification"] == "respond":
        bad = feedback.get("tool_calls", 1) < 1 or feedback.get("criteria", 1) < 1
        nodes.append(
            {"name": "response_agent", "error": "reply misses the criteria" if bad else None}
        )
    return {
        "id": str(uuid.uuid4()),
        "name": "email_assistant",
        "inputs": inputs,
        "outputs": out,
        "feedback": feedback,
        "nodes": nodes,
        "reference": ref,
    }


if __name__ == "__main__":
    with ThreadPoolExecutor(6) as pool:
        runs = list(pool.map(one, EMAILS))
    with open(sys.argv[1], "w") as f:
        json.dump(runs, f, indent=1)
    bad = [r for r in runs if r.get("error") or min(r.get("feedback", {"x": 0}).values()) < 1]
    print(f"{len(runs)} runs, {len(bad)} failed at least one check")
