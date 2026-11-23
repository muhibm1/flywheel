"""Decide block or pass for one gate from the verifier's structured answers.

Usage: python verdict.py <gate_dir> [<gate_dir> ...]

A finding blocks only when every one of these holds:
  - the runner shows it passes every run on base and fails every run on head (results.json);
  - the verifier reproduced it and found it fails for the stated reason;
  - it goes through a public entry point and existed at base;
  - the effect is a loss and the base behaviour was not a defect;
  - ordinary use meets it, or an unusual but valid use loses something that succeeded at base
    (a change in how a failure is reported blocks only when ordinary use meets it).
The model fills in the fields; this file makes the decision.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def decide(gate: Path) -> dict:
    results = json.loads((gate / "results.json").read_text()) if (gate / "results.json").exists() else {}
    vfile = gate / "verdicts.json"
    ffile = gate / "findings_final.json"
    if not vfile.exists() and ffile.exists():
        # Nothing was claimed as a loss, so there is nothing for a verifier to check.
        if not [f for f in json.loads(ffile.read_text()) if f.get("effect") == "loss"]:
            out = {"gate": gate.name, "verdict": "pass", "blocking": [], "dropped": [],
                   "reason": "no loss findings"}
            (gate / "verdict.json").write_text(json.dumps(out, indent=1))
            return out
    if not vfile.exists():
        return {"gate": gate.name, "verdict": "incomplete", "blocking": [], "reason": "no verdicts.json"}
    blocking, dropped = [], []
    for v in json.loads(vfile.read_text()):
        runner_ok = results.get(v.get("probe"), {}).get("status") == "confirmed_difference"
        checks = {
            "runner_confirmed": runner_ok,
            "reproduced": v.get("reproduced") is True,
            "fails_for_stated_reason": v.get("fails_for_stated_reason") is True,
            "public_entry_point": v.get("public_entry_point") is True,
            "existed_at_base": v.get("existed_at_base") is True,
            "effect_is_loss": v.get("effect") == "loss",
            # A lost success blocks at any legitimate reach. A change in how a failure is
            # reported blocks only when ordinary use meets it.
            "reach_sufficient": v.get("reach") == "mainstream"
            or (v.get("reach") == "legitimate_edge" and v.get("base_outcome") == "success"),
            "base_not_defect": v.get("base_was_defect") is False,
        }
        failed = [k for k, ok in checks.items() if not ok]
        row = {"probe": v.get("probe"), "summary": v.get("summary"), "declared": v.get("declared"),
               "reach": v.get("reach")}
        if failed:
            dropped.append(dict(row, failed_checks=failed))
        else:
            blocking.append(row)
    out = {"gate": gate.name, "verdict": "block" if blocking else "pass",
           "blocking": blocking, "dropped": dropped}
    (gate / "verdict.json").write_text(json.dumps(out, indent=1))
    return out


def main() -> int:
    for g in sys.argv[1:]:
        r = decide(Path(g).resolve())
        print(f"{r['gate']}: {r['verdict']} ({len(r['blocking'])} blocking)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
