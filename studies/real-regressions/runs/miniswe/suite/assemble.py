"""Build each gate's dataset.jsonl (standing + change), adapter.py copy and flywheel.toml."""

import shutil
from pathlib import Path

SUITE = Path(__file__).resolve().parent
PROJECT = SUITE.parent
TOML = """[flywheel]
target = "adapter:target"
evaluators = ["adapter:check_exit_status", "adapter:check_verify", "adapter:check_files", "adapter:check_trajectory", "adapter:check_limits"]
dataset = "dataset.jsonl"
repetitions = 3

[gate]
max_broken = 0
close_call_repetitions = 3
"""

standing = (SUITE / "standing.jsonl").read_text(encoding="utf-8").strip()
for gate in sorted(PROJECT.glob("miniswe-g*")):
    change_file = gate / "change.jsonl"
    change = change_file.read_text(encoding="utf-8").strip() if change_file.exists() else ""
    (gate / "dataset.jsonl").write_text(standing + "\n" + (change + "\n" if change else ""), encoding="utf-8")
    shutil.copy(SUITE / "adapter.py", gate / "adapter.py")
    (gate / "flywheel.toml").write_text(TOML, encoding="utf-8")
    print(gate.name, "ok")
