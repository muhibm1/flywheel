"""Keep model-service failures out of the verdict.

A run whose error came from the local model endpoint (a failed headless call, a dropped
connection) says nothing about the agent, so it is removed from the experiment and run again,
on whichever side it happened. Rules fixed before the held-out round:
- an error counts as transport only when its text contains one of MARKERS;
- each side is topped up until every case has its configured repetitions, at most 3 rounds;
- what was removed is logged in transport.json next to the gate.
"""

import json
from pathlib import Path

MARKERS = ("proxy_error", "headless call failed", "claude exited", "APIConnectionError",
           "Connection refused", "RemoteDisconnected", "Connection reset", "ServiceUnavailable")


def is_transport(error: str | None) -> bool:
    """Whether a run's error came from the model endpoint, not the agent."""
    return bool(error) and any(m.lower() in error.lower() for m in MARKERS)


def clean(paths: list[Path], out: Path) -> dict[str, int]:
    """Pool `paths` into `out` without transport-errored runs; return runs still owed per case."""
    exps = [json.loads(p.read_text()) for p in paths]
    merged = exps[0]
    merged["runs"] = [r for e in exps for r in e["runs"] if not is_transport(r.get("error"))]
    removed = [r for e in exps for r in e["runs"] if is_transport(r.get("error"))]
    out.write_text(json.dumps(merged))
    want = merged.get("repetitions") or 3
    have: dict[str, int] = {}
    for r in merged["runs"]:
        have[r["example_id"]] = have.get(r["example_id"], 0) + 1
    owed = {}
    for r in removed:
        cid = r["example_id"]
        if have.get(cid, 0) < want:
            owed[cid] = want - have.get(cid, 0)
    return owed
