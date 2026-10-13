"""A tiny stand-in agent so the quickstart runs with nothing installed.

It routes a customer message to a team. `QUICKSTART_REGRESSION=1` swaps in a "simplified"
rule set that drops the refund rule, the kind of tidy-up that reads fine in review and
silently misroutes every refund request.
"""

import os

RULES = [
    ("refund", "billing"),
    ("charged twice", "billing"),
    ("invoice", "billing"),
    ("password", "account"),
    ("log in", "account"),
    ("crash", "engineering"),
    ("error", "engineering"),
]


def target(inputs: dict) -> dict:
    """Route one message: the first rule whose phrase appears wins; otherwise `general`."""
    rules = RULES[1:] if os.environ.get("QUICKSTART_REGRESSION") == "1" else RULES
    message = inputs["message"].lower()
    for phrase, team in rules:
        if phrase in message:
            return {"team": team}
    return {"team": "general"}


def correct_team(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """The message went to the team the reference names."""
    return outputs.get("team") == reference_outputs.get("team")


def not_general_when_specific(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """A message with a known owner never falls through to the general queue."""
    return reference_outputs.get("team") == "general" or outputs.get("team") != "general"
