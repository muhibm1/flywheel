"""Write LangChain's 16 labelled emails (eval/email_dataset.py) as a Flywheel dataset."""

import json
import sys

from email_assistant.eval.email_dataset import (
    email_inputs, email_names, expected_tool_calls, response_criteria_list, triage_outputs_list,
)
from flywheel.dataset import inputs_id

rows = []
for name, email, label, calls, crit in zip(
    email_names, email_inputs, triage_outputs_list, expected_tool_calls, response_criteria_list
):
    inputs = {"email_input": email}
    rows.append({
        "id": inputs_id(inputs),
        "inputs": inputs,
        "reference_outputs": {"classification": label, "expected_calls": calls, "criteria": crit.strip()},
        "metadata": {"source": "langchain", "name": name},
    })
out = sys.argv[1] if len(sys.argv) > 1 else "dataset.jsonl"
with open(out, "w") as f:
    for r in rows:
        f.write(json.dumps(r, sort_keys=True) + "\n")
print(len(rows), "cases;", {l: triage_outputs_list.count(l) for l in set(triage_outputs_list)})
