"""A tiny stand-in agent so the quickstart runs with nothing installed.

It routes a customer message to a team. Two "simplified" rule sets stand in for edits that
read fine in review:

- `QUICKSTART_REGRESSION=1` drops the refund rule, so every refund request is misrouted. The
  hand-written seed cases catch this one.
- `QUICKSTART_REGRESSION=money` drops the "money back" rule, added after production traffic
  showed customers asking for their money back without saying "refund". No seed case covers
  it; only the cases mined from `traces.json` do.
"""

import os

RULES = [
    ("refund", "billing"),
    ("money back", "billing"),
    ("charged twice", "billing"),
    ("invoice", "billing"),
    ("password", "account"),
    ("log in", "account"),
    ("crash", "engineering"),
    ("error", "engineering"),
]


def target(inputs: dict) -> dict:
    """Route one message: the first rule whose phrase appears wins; otherwise `general`."""
    regression = os.environ.get("QUICKSTART_REGRESSION")
    dropped = {"1": "refund", "money": "money back"}.get(regression or "")
    rules = [rule for rule in RULES if rule[0] != dropped]
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
