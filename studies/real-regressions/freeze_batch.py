"""Hash the frozen inputs for a batch of held-out gates: python freeze_batch.py <label> <gate> [...]

Writes freeze-<label>.json next to this file (sha256 of every case and adapter file of each gate and
its project's suite, plus the briefs and the study's own code) and prints a digest of that file.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKIP = ("smoke", "scratch", "__pycache__", ".pyc", "fault-smoke", "pgdata")


def digest(p: Path) -> str:
    """sha256 of a file."""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def files(root: Path) -> list[Path]:
    """Every file under root, skipping scratch and run output."""
    return sorted(p for p in root.rglob("*") if p.is_file() and not any(s in str(p) for s in SKIP))


label, gates = sys.argv[1], sys.argv[2:]
out: dict[str, str] = {}
for gid in gates:
    project = gid.rsplit("-g", 1)[0]
    for p in files(Path(f"/tmp/rr/blind/{project}/{gid}")) + files(Path(f"/tmp/rr/blind/{project}/suite")):
        out[str(p)] = digest(p)
for name in ("WRITER_BRIEF_v2.md", "ROUND2_NOTE.md", "VETO_BRIEF.md", "FAULT_NOTE.md", "SWEEP_NOTE.md"):
    out[f"/tmp/rr/blind/{name}"] = digest(Path(f"/tmp/rr/blind/{name}"))
for name in ("proxy.py", "transport.py", "run_gate.py", "run_heldout.py", "score.py", "proxy_check.py", "confirm.py", "PLAN.md"):
    out[str(HERE / name)] = digest(HERE / name)
path = HERE / f"freeze-{label}.json"
path.write_text(json.dumps(out, indent=1, sort_keys=True))
print(label, len(out), "files", digest(path))
